import os
import sys
import json
import uuid
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.sql import (
    SessionLocal, Case, CaseMember, EvidenceFile, CallRecord, Transaction,
    Entity, EntityLink, ExtractedEntity, MatchSuggestion, ProfileMember,
    Alert, AuditLog, CaseSetting, User, Report
)
from backend.app.services.graph.builder import invalidate_case_graph, build_detail_graph, CASE_GRAPH_CACHE
from backend.app.services.graph.projection import build_entity_projection
from backend.app.services.matching.service import generate_case_matches
from backend.app.services.analytics.lead_advisor import compute_lead_advisor
from backend.app.services.money.patterns import detect_money_patterns
from backend.app.audit.service import record_audit_log
from backend.app.services.reports.router import _gather_case_dossier_data
from backend.app.services.reports.pdf_generator import generate_case_dossier_pdf

SAMPLE_CASES_DIR = ROOT_DIR / "docs" / "sample_cases"
SAMPLE_CASES_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_EVIDENCE_DIR = SAMPLE_CASES_DIR / "evidence"
SAMPLE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

def ensure_user(db):
    user = db.query(User).filter(User.username == "investigator1").first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            username="investigator1",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4h2i4L1f.e", # OfficerPass1234!
            full_name="Inspector Meera Sundaram",
            role="investigator",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()
    return user

def stage_cyber_shield_case(db, user):
    """Stages Case 2: Operation Cyber Shield (FIR 882/2026)"""
    title = "Operation Cyber Shield: Inter-State Cyber Extortion Syndicate (FIR 882/2026)"
    existing = db.query(Case).filter(Case.title == title).first()
    if existing:
        print(f"[OK] Cyber Shield case already exists (ID: {existing.id})")
        case_id = existing.id
    else:
        case_id = str(uuid.uuid4())
        new_case = Case(
            id=case_id,
            title=title,
            description="Inter-state cyber extortion, burner SIM rotation & mule bank accounts syndicate active across Delhi NCR and Haryana. Involves organized digital extortion and rapid pass-through money laundering.",
            priority="high",
            status="active",
            created_by=user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_case)
        db.add(CaseMember(case_id=case_id, user_id=user.id, role="lead", added_at=datetime.now(timezone.utc)))
        
        defaults = {
            "money_threshold_inr": 200000,
            "pass_through_hours": 24,
            "round_amount_mod": 50000,
            "sim_swap_days": 7,
            "call_spike_mad_multiplier": 3.0,
            "weights": {"cdr": 0.4, "financial": 0.4, "fir": 0.2}
        }
        db.add(CaseSetting(case_id=case_id, settings_json=json.dumps(defaults), updated_at=datetime.now(timezone.utc)))
        db.commit()
        print(f"[OK] Created Case: {title} (ID: {case_id})")

    # Ingest synthetic clean files
    clean_dir = ROOT_DIR / "data" / "synthetic" / "samples" / "clean"
    
    # 1. FIR
    fir_file = clean_dir / "FIR-2026-101.txt"
    if fir_file.exists():
        content = fir_file.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        dest = UPLOADS_DIR / f"{case_id}_{fir_file.name}"
        dest.write_bytes(content)
        
        ev = db.query(EvidenceFile).filter_by(case_id=case_id, original_name="FIR-2026-101.txt").first()
        if not ev:
            ev = EvidenceFile(
                id=str(uuid.uuid4()),
                case_id=case_id,
                original_name="FIR-2026-101.txt",
                stored_path=str(dest),
                sha256=sha,
                file_size=len(content),
                detected_type="fir",
                status="ingested",
                uploader_id=user.id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(ev)
            db.commit()

    # 2. CDR
    cdr_file = clean_dir / "cdr.csv"
    if cdr_file.exists():
        content = cdr_file.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        dest = UPLOADS_DIR / f"{case_id}_{cdr_file.name}"
        dest.write_bytes(content)
        
        ev_cdr = db.query(EvidenceFile).filter_by(case_id=case_id, original_name="cdr.csv").first()
        if not ev_cdr:
            ev_cdr = EvidenceFile(
                id=str(uuid.uuid4()),
                case_id=case_id,
                original_name="cdr.csv",
                stored_path=str(dest),
                sha256=sha,
                file_size=len(content),
                detected_type="cdr",
                status="ingested",
                uploader_id=user.id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(ev_cdr)
            db.commit()

            import csv
            with open(cdr_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    caller = row.get("caller") or row.get("calling_number", "")
                    receiver = row.get("receiver") or row.get("called_number", "")
                    c_date = row.get("date") or "2026-10-10"
                    c_time = row.get("time") or "12:00:00"
                    fp = hashlib.sha256(f"{caller}_{receiver}_{c_date}_{c_time}_{i}".encode()).hexdigest()
                    cr = CallRecord(
                        case_id=case_id,
                        source_file="cdr.csv",
                        source_ref=f"row_{i+1}",
                        caller=caller,
                        receiver=receiver,
                        call_date=c_date,
                        call_time=c_time,
                        datetime_iso=f"{c_date}T{c_time}Z",
                        duration_seconds=int(row.get("duration", 60)),
                        call_type=row.get("call_type", "voice"),
                        imei=row.get("imei", ""),
                        imsi=row.get("imsi", ""),
                        cell_id=row.get("cell_id", ""),
                        fingerprint=fp
                    )
                    db.add(cr)
            db.commit()

    # 3. Bank Transactions
    bank_file = clean_dir / "bank_transactions.csv"
    if bank_file.exists():
        content = bank_file.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        dest = UPLOADS_DIR / f"{case_id}_{bank_file.name}"
        dest.write_bytes(content)
        
        ev_bank = db.query(EvidenceFile).filter_by(case_id=case_id, original_name="bank_transactions.csv").first()
        if not ev_bank:
            ev_bank = EvidenceFile(
                id=str(uuid.uuid4()),
                case_id=case_id,
                original_name="bank_transactions.csv",
                stored_path=str(dest),
                sha256=sha,
                file_size=len(content),
                detected_type="bank_transactions",
                status="ingested",
                uploader_id=user.id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(ev_bank)
            db.commit()

            import csv
            with open(bank_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    amt_str = row.get("amount", "0")
                    amt_paise = int(float(amt_str) * 100)
                    from_acc = row.get("remitter_account") or row.get("sender_account", "")
                    to_acc = row.get("beneficiary_account") or row.get("receiver_account", "")
                    t_date = row.get("date") or "2026-10-10"
                    t_time = row.get("time") or "12:00:00"
                    fp = hashlib.sha256(f"{from_acc}_{to_acc}_{amt_paise}_{t_date}_{i}".encode()).hexdigest()
                    tx = Transaction(
                        case_id=case_id,
                        source_file="bank_transactions.csv",
                        source_ref=f"row_{i+1}",
                        txn_id=row.get("txn_id") or f"TXN-{i+1}",
                        from_account=from_acc,
                        to_account=to_acc,
                        from_name=row.get("remitter_name") or row.get("sender_name", ""),
                        to_name=row.get("beneficiary_name") or row.get("receiver_name", ""),
                        amount_paise=amt_paise,
                        date_iso=f"{t_date}T{t_time}Z",
                        reference=row.get("reference", ""),
                        direction="out",
                        fingerprint=fp
                    )
                    db.add(tx)
            db.commit()

    # 4. Identity entities from account master
    master_file = clean_dir / "account_master.csv"
    if master_file.exists():
        import csv
        with open(master_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                name = row.get("holder_name") or row.get("name", "")
                acc = row.get("account_number") or row.get("account", "")
                phone = row.get("phone", "")
                if name and not db.query(Entity).filter_by(case_id=case_id, canonical_id=name).first():
                    db.add(Entity(
                        case_id=case_id,
                        label="Person",
                        canonical_id=name,
                        display_name=name,
                        properties_json=json.dumps({"role": "Account Holder", "phone": phone}),
                        source_file="account_master.csv",
                        source_ref=f"row_{i+1}",
                        method="structured",
                        confidence=1.0
                    ))
                if acc and not db.query(Entity).filter_by(case_id=case_id, canonical_id=acc).first():
                    db.add(Entity(
                        case_id=case_id,
                        label="BankAccount",
                        canonical_id=acc,
                        display_name=f"A/c {acc}",
                        properties_json=json.dumps({"holder": name}),
                        source_file="account_master.csv",
                        source_ref=f"row_{i+1}",
                        method="structured",
                        confidence=1.0
                    ))
                if phone and not db.query(Entity).filter_by(case_id=case_id, canonical_id=phone).first():
                    db.add(Entity(
                        case_id=case_id,
                        label="Phone",
                        canonical_id=phone,
                        display_name=phone,
                        properties_json=json.dumps({"owner": name}),
                        source_file="account_master.csv",
                        source_ref=f"row_{i+1}",
                        method="structured",
                        confidence=1.0
                    ))
        db.commit()

    # Rebuild graph & matches
    invalidate_case_graph(case_id)
    dg = build_detail_graph(db, case_id)
    eg = build_entity_projection(dg)
    CASE_GRAPH_CACHE[case_id] = (dg, eg)
    
    txns = db.query(Transaction).filter_by(case_id=case_id).all()
    c_setting = db.query(CaseSetting).filter_by(case_id=case_id).first()
    settings_dict = json.loads(c_setting.settings_json) if c_setting else {}
    anomalies = detect_money_patterns(txns, settings_dict)
    for a in anomalies:
        al = Alert(
            case_id=case_id,
            entity_id=a["account"],
            pattern_type=a["pattern"],
            severity=a["severity"],
            alert_date="2026-10-12",
            explanation=a["explanation"],
            evidence_ids_json=json.dumps(a.get("evidence_txn_keys", [])),
            created_at=datetime.now(timezone.utc)
        )
        db.add(al)
    db.commit()

    return case_id

def export_dossiers(db, user):
    """Generates Section 63 BSA 2023 PDFs for both sample cases."""
    cases_to_export = [
        ("Operation RedSand: Inter-State Hawala & Angadia Syndicate (FIR 409/2026)",
         "Operation_RedSand_Hawala_Syndicate_Dossier.pdf"),
        ("Operation Cyber Shield: Inter-State Cyber Extortion Syndicate (FIR 882/2026)",
         "Operation_Cyber_Shield_Syndicate_Dossier.pdf")
    ]

    for title, out_filename in cases_to_export:
        case = db.query(Case).filter(Case.title == title).first()
        if not case:
            print(f"[WARN] Case not found: {title}")
            continue

        print(f"\nGenerating Court Dossier PDF for: {case.title}...")
        case_dict = {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "priority": case.priority,
            "created_at": str(case.created_at)
        }
        officer_info = {
            "name": "Inspector Meera Sundaram",
            "rank": "Inspector of Police (Lead Forensic Investigator)",
            "station": "Special Cell, Lodhi Colony, New Delhi",
            "unit": "Cyber Crime & Organised Syndicate Investigation Unit",
            "remarks": "Investigation conducted under Section 63 Bharatiya Sakshya Adhiniyam, 2023. Forensic chain of custody cryptographically sealed with SHA-256."
        }
        sections_enabled = {
            "overview": True,
            "entities": True,
            "cdr": True,
            "financial": True,
            "documents": True,
            "audit": True
        }

        data_bundle = _gather_case_dossier_data(db, case)
        out_pdf_path = str(SAMPLE_CASES_DIR / out_filename)

        sha256_hash = generate_case_dossier_pdf(
            output_path=out_pdf_path,
            case_data=case_dict,
            officer_info=officer_info,
            sections_enabled=sections_enabled,
            evidence_list=data_bundle["evidence_list"],
            entities_list=data_bundle["entities_list"],
            cdr_summary=data_bundle["cdr_summary"],
            financial_summary=data_bundle["financial_summary"],
            extracted_summary=data_bundle["extracted_summary"],
            audit_summary=data_bundle["audit_summary"]
        )
        file_size_kb = os.path.getsize(out_pdf_path) / 1024
        print(f"[SUCCESS] Exported: {out_filename} ({file_size_kb:.1f} KB, SHA-256: {sha256_hash[:16]}...)")

def copy_sample_evidence_files():
    """Copies sample evidence files to docs/sample_cases/evidence/ for easy user access."""
    # 1. Hawala case files
    hawala_src = ROOT_DIR / "data" / "synthetic" / "samples" / "hawala_case"
    if hawala_src.exists():
        for f in hawala_src.glob("*"):
            if f.is_file():
                dest = SAMPLE_EVIDENCE_DIR / f.name
                shutil.copy2(f, dest)
                print(f"[COPIED] {f.name} -> docs/sample_cases/evidence/{dest.name}")

    # 2. Cyber Shield case files
    clean_src = ROOT_DIR / "data" / "synthetic" / "samples" / "clean"
    if clean_src.exists():
        shutil.copy2(clean_src / "FIR-2026-101.txt", SAMPLE_EVIDENCE_DIR / "FIR-2026-101-CYBER-SHIELD.txt")
        shutil.copy2(clean_src / "bank_transactions.csv", SAMPLE_EVIDENCE_DIR / "cyber_shield_bank_transactions.csv")
        shutil.copy2(clean_src / "cdr.csv", SAMPLE_EVIDENCE_DIR / "cyber_shield_cdr.csv")
        shutil.copy2(clean_src / "ip_logs.csv", SAMPLE_EVIDENCE_DIR / "cyber_shield_ip_logs.csv")
        shutil.copy2(clean_src / "sdr.csv", SAMPLE_EVIDENCE_DIR / "cyber_shield_sdr.csv")
        print("[COPIED] Clean case files -> docs/sample_cases/evidence/")

def main():
    print("==================================================")
    print("  STAGING SAMPLE CASES & GENERATING COURT DOSSIERS")
    print("==================================================")
    db = SessionLocal()
    try:
        user = ensure_user(db)
        stage_cyber_shield_case(db, user)
        export_dossiers(db, user)
        copy_sample_evidence_files()
        print("\n[ALL DONE] Sample cases and PDFs ready in docs/sample_cases/")
    finally:
        db.close()

if __name__ == "__main__":
    main()
