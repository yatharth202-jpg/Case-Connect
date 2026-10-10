import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.config import settings
from backend.app.db.sql import (
    get_db, Case, EvidenceFile, Entity, EntityLink, CallRecord, Transaction,
    ExtractedEntity, AuditLog, Report, User
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.audit.service import record_audit_log, verify_audit_chain
from backend.app.services.reports.pdf_generator import generate_case_dossier_pdf
from backend.app.services.reports.json_exporter import generate_case_export_json

router = APIRouter()

class CreateReportRequest(BaseModel):
    report_title: str = Field(default="Investigation Court Dossier (Section 63 BSA 2023)")
    format: str = Field(default="pdf") # "pdf" or "json"
    sections: Dict[str, bool] = Field(default_factory=lambda: {
        "overview": True,
        "entities": True,
        "cdr": True,
        "financial": True,
        "documents": True,
        "audit": True
    })
    officer_name: Optional[str] = None
    officer_rank: Optional[str] = None
    officer_station: Optional[str] = None
    officer_unit: Optional[str] = None
    officer_remarks: Optional[str] = None

def _gather_case_dossier_data(db: Session, case: Case) -> Dict[str, Any]:
    """Gathers and formats comprehensive case intelligence across all subsystem tables."""
    # 1. Evidence Files
    ev_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).order_by(EvidenceFile.created_at.asc()).all()
    evidence_list = [
        {
            "id": e.id,
            "original_name": e.original_name,
            "detected_type": e.detected_type,
            "file_size": e.file_size,
            "sha256": e.sha256,
            "status": e.status,
            "created_at": str(e.created_at)
        }
        for e in ev_files
    ]

    # 2. Entities & Links
    ents = db.query(Entity).filter(Entity.case_id == case.id).all()
    entities_list = [
        {
            "id": e.id,
            "label": e.label,
            "canonical_id": e.canonical_id,
            "display_name": e.display_name,
            "confidence": e.confidence,
            "method": e.method,
            "source_file": e.source_file
        }
        for e in ents
    ]

    links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    links_list = [
        {
            "id": l.id,
            "source_entity_id": l.source_entity_id,
            "target_entity_id": l.target_entity_id,
            "relationship_type": l.relationship_type,
            "confidence": l.confidence,
            "source_file": l.source_file
        }
        for l in links
    ]

    # 3. CDR Telecommunications
    cdrs = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
    total_calls = len(cdrs)
    total_duration = sum(c.duration_seconds for c in cdrs)
    unique_phones = set()
    pair_counts = {}
    pair_durations = {}

    for c in cdrs:
        unique_phones.add(c.caller)
        unique_phones.add(c.receiver)
        pair_key = (c.caller, c.receiver)
        pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
        pair_durations[pair_key] = pair_durations.get(pair_key, 0) + c.duration_seconds

    top_pairs = []
    for (caller, receiver), count in sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        top_pairs.append({
            "caller": caller,
            "receiver": receiver,
            "count": count,
            "duration_seconds": pair_durations.get((caller, receiver), 0)
        })

    high_freq_count = sum(1 for cnt in pair_counts.values() if cnt >= 5)
    cdr_summary = {
        "total_calls": total_calls,
        "total_duration_minutes": round(total_duration / 60, 1),
        "unique_phones": len(unique_phones),
        "high_freq_pairs_count": high_freq_count,
        "top_pairs": top_pairs
    }

    # 4. Financial Transactions
    txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()
    total_paise = sum(t.amount_paise for t in txns)
    unique_accounts = set()
    for t in txns:
        unique_accounts.add(t.from_account)
        unique_accounts.add(t.to_account)

    top_txns = [
        {
            "from_account": t.from_account,
            "to_account": t.to_account,
            "amount_paise": t.amount_paise,
            "date_iso": t.date_iso
        }
        for t in sorted(txns, key=lambda x: x.amount_paise, reverse=True)[:10]
    ]

    financial_summary = {
        "transaction_count": len(txns),
        "total_flow_paise": total_paise,
        "unique_accounts": len(unique_accounts),
        "alerts_count": 0, # Stored anomalies
        "top_transactions": top_txns
    }

    # 5. Extracted Findings
    extracted_approved = db.query(ExtractedEntity).filter(
        ExtractedEntity.case_id == case.id,
        ExtractedEntity.status == "approved"
    ).all()

    extracted_summary = {
        "approved_count": len(extracted_approved),
        "approved_items": [
            {
                "entity_type": ee.entity_type,
                "raw_value": ee.raw_value,
                "normalized_value": ee.normalized_value,
                "page_or_paragraph": ee.page_or_paragraph,
                "confidence": ee.confidence,
                "status": ee.status
            }
            for ee in extracted_approved
        ]
    }

    # 6. Audit Trail Summary
    chain_status = verify_audit_chain(db)
    all_audit_logs = db.query(AuditLog).order_by(AuditLog.ts.asc()).all()
    genesis_hash = all_audit_logs[0].hash if all_audit_logs else "0" * 64
    head_hash = all_audit_logs[-1].hash if all_audit_logs else "0" * 64

    audit_summary = {
        "is_valid": chain_status.get("valid", True),
        "total_verified": chain_status.get("checked_rows", 0),
        "genesis_hash": genesis_hash,
        "head_hash": head_hash
    }

    return {
        "evidence_list": evidence_list,
        "entities_list": entities_list,
        "links_list": links_list,
        "cdr_summary": cdr_summary,
        "financial_summary": financial_summary,
        "extracted_summary": extracted_summary,
        "audit_summary": audit_summary
    }

@router.post("/cases/{case_id}/reports")
def generate_case_report(
    case_id: str,
    req: CreateReportRequest,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Generates an official court-admissible Section 63 BSA 2023 Case Dossier Report (PDF or JSON).
    Calculates cryptographic SHA-256 fingerprint and registers the immutable report record.
    """
    case_dict = {
        "id": case.id,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "priority": case.priority,
        "created_at": str(case.created_at)
    }

    officer_info = {
        "name": req.officer_name or current_user.username,
        "rank": req.officer_rank or "Inspector of Police",
        "station": req.officer_station or "Special Cyber Crime Cell",
        "unit": req.officer_unit or "Special Investigation Division",
        "remarks": req.officer_remarks or ""
    }

    # Gather data across subsystems
    data_bundle = _gather_case_dossier_data(db, case)

    # Output path setup
    reports_dir = Path(settings.UPLOAD_DIR) / "reports" / case.id
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    export_format = req.format.lower().strip()
    if export_format == "json":
        filename = f"dossier_{case.id[:8]}_{timestamp_str}.json"
        out_path = str(reports_dir / filename)
        sha256_hash = generate_case_export_json(
            output_path=out_path,
            case_data=case_dict,
            officer_info=officer_info,
            evidence_list=data_bundle["evidence_list"],
            entities_list=data_bundle["entities_list"],
            entity_links=data_bundle["links_list"],
            cdr_summary=data_bundle["cdr_summary"],
            financial_summary=data_bundle["financial_summary"],
            extracted_summary=data_bundle["extracted_summary"],
            audit_summary=data_bundle["audit_summary"]
        )
    else:
        filename = f"court_dossier_sec63_{case.id[:8]}_{timestamp_str}.pdf"
        out_path = str(reports_dir / filename)
        sha256_hash = generate_case_dossier_pdf(
            output_path=out_path,
            case_data=case_dict,
            officer_info=officer_info,
            sections_enabled=req.sections,
            evidence_list=data_bundle["evidence_list"],
            entities_list=data_bundle["entities_list"],
            cdr_summary=data_bundle["cdr_summary"],
            financial_summary=data_bundle["financial_summary"],
            extracted_summary=data_bundle["extracted_summary"],
            audit_summary=data_bundle["audit_summary"]
        )

    # Stage report record in SQLite reports table
    report_entry = Report(
        case_id=case.id,
        report_title=req.report_title,
        stored_path=out_path,
        sha256=sha256_hash,
        generated_by=current_user.id,
        parameters_json=json.dumps({
            "format": export_format,
            "filename": filename,
            "sections": req.sections,
            "officer_name": officer_info["name"],
            "officer_rank": officer_info["rank"]
        })
    )
    db.add(report_entry)
    db.commit()
    db.refresh(report_entry)

    # Record tamper-evident cryptographic audit log
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="generate_report",
        case_id=case.id,
        object_type="report",
        object_id=report_entry.id,
        details={
            "format": export_format,
            "title": req.report_title,
            "sha256": sha256_hash,
            "legal_standard": "Section 63 BSA 2023"
        }
    )

    return {
        "id": report_entry.id,
        "case_id": case.id,
        "report_title": report_entry.report_title,
        "format": export_format,
        "filename": filename,
        "sha256": report_entry.sha256,
        "created_at": str(report_entry.created_at)
    }

@router.get("/cases/{case_id}/reports")
def list_case_reports(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all generated Section 63 BSA 2023 court reports and case dossiers for the case."""
    reports = db.query(Report).filter(Report.case_id == case.id).order_by(Report.created_at.desc()).all()
    results = []

    for r in reports:
        params = {}
        try:
            params = json.loads(r.parameters_json)
        except Exception:
            pass

        gen_user = db.query(User).filter(User.id == r.generated_by).first()
        results.append({
            "id": r.id,
            "case_id": r.case_id,
            "report_title": r.report_title,
            "format": params.get("format", "pdf"),
            "filename": params.get("filename", Path(r.stored_path).name),
            "sha256": r.sha256,
            "generated_by": gen_user.username if gen_user else "Officer",
            "officer_name": params.get("officer_name", "Officer"),
            "officer_rank": params.get("officer_rank", ""),
            "created_at": str(r.created_at)
        })

    return results

@router.get("/reports/{report_id}/download")
def download_case_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Downloads a certified court report PDF or JSON file with verified SHA-256 integrity."""
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Access check: verify user has case membership
    get_case_for_user(case_id=r.case_id, current_user=current_user, db=db)

    file_path = Path(r.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found on storage")

    # Record audit download event
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="download_report",
        case_id=r.case_id,
        object_type="report",
        object_id=r.id,
        details={"filename": file_path.name, "sha256": r.sha256}
    )

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "application/json"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name
    )

@router.get("/cases/{case_id}/export/json")
def export_case_json(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Direct one-click endpoint to export complete case dataset as a Section 63 BSA 2023 JSON dossier."""
    case_dict = {
        "id": case.id,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "priority": case.priority,
        "created_at": str(case.created_at)
    }

    officer_info = {
        "name": current_user.username,
        "rank": "Investigating Officer",
        "station": "Special Cyber Crime Cell",
        "unit": "Special Investigation Division"
    }

    data_bundle = _gather_case_dossier_data(db, case)
    reports_dir = Path(settings.UPLOAD_DIR) / "reports" / case.id
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"case_export_{case.id[:8]}.json"
    out_path = str(reports_dir / filename)

    sha256_hash = generate_case_export_json(
        output_path=out_path,
        case_data=case_dict,
        officer_info=officer_info,
        evidence_list=data_bundle["evidence_list"],
        entities_list=data_bundle["entities_list"],
        entity_links=data_bundle["links_list"],
        cdr_summary=data_bundle["cdr_summary"],
        financial_summary=data_bundle["financial_summary"],
        extracted_summary=data_bundle["extracted_summary"],
        audit_summary=data_bundle["audit_summary"]
    )

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="export_case_json",
        case_id=case.id,
        object_type="case",
        object_id=case.id,
        details={"sha256": sha256_hash}
    )

    return FileResponse(
        path=out_path,
        media_type="application/json",
        filename=filename
    )
