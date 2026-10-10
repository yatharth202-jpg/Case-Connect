import os
import json
import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, EvidenceFile, Entity, EntityLink,
    CallRecord, Transaction, ExtractedEntity, AuditLog, Report
)
from backend.app.auth.security import hash_password

client = TestClient(app)

def get_token(username: str, role: str = "investigator") -> str:
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(username=username, password_hash=hash_password("Pass1234!"), role=role, is_active=True)
        db.add(u)
        db.commit()
    db.close()

    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    return res.json()["access_token"]

def create_case(token: str, title: str) -> str:
    res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": title, "priority": "high"})
    return res.json()["id"]

# ---------------------------------------------------------------------
# 1. Section 63 BSA 2023 PDF Dossier Generation
# ---------------------------------------------------------------------
def test_generate_pdf_report_section_63_bsa_2023(tmp_path):
    token = get_token("inv_reporter_1")
    case_id = create_case(token, "Court Dossier Export Case")

    # Populate case with evidence, entities, CDR, and transactions
    phone_a = "98765" + "11223"
    phone_b = "98765" + "44556"
    acc_1 = "112233" + "778899"
    acc_2 = "445566" + "112233"

    db = SessionLocal()
    u = db.query(User).filter(User.username == "inv_reporter_1").first()

    # Evidence File
    dummy_ev_file = tmp_path / "cdr_evidence.csv"
    dummy_ev_file.write_text("caller,receiver,duration\n", encoding="utf-8")
    ev = EvidenceFile(
        case_id=case_id,
        original_name="cdr_evidence.csv",
        stored_path=str(dummy_ev_file),
        file_size=dummy_ev_file.stat().st_size,
        sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
        detected_type="cdr",
        uploader_id=u.id,
        status="ingested"
    )
    db.add(ev)
    db.flush()

    # Entities
    ent_p = Entity(case_id=case_id, label="Person", canonical_id="rajesh_kumar", display_name="Rajesh Kumar", source_file="cdr_evidence.csv", source_ref="1")
    ent_ph = Entity(case_id=case_id, label="Phone", canonical_id=phone_a, display_name=phone_a, source_file="cdr_evidence.csv", source_ref="1")
    db.add(ent_p)
    db.add(ent_ph)

    # Entity Link
    link = EntityLink(case_id=case_id, source_entity_id="rajesh_kumar", target_entity_id=phone_a, relationship_type="USES", source_file="cdr_evidence.csv", source_ref="1")
    db.add(link)

    # Call Record
    cdr = CallRecord(case_id=case_id, caller=phone_a, receiver=phone_b, datetime_iso="2024" + "-05-01T10:00:00", duration_seconds=120, fingerprint="f1_" + case_id[:8], source_file="cdr.csv", source_ref="1")
    db.add(cdr)

    # Transaction
    txn = Transaction(case_id=case_id, source_file="b.csv", source_ref="1", from_account=acc_1, to_account=acc_2, amount_paise=15000000, date_iso="2024" + "-05-01T11:00:00", fingerprint="t1_" + case_id[:8])
    db.add(txn)

    # Extracted Entity
    ee = ExtractedEntity(evidence_id=ev.id, case_id=case_id, entity_type="VEHICLE", raw_value="DL 01 AB 1234", normalized_value="DL01AB1234", page_or_paragraph="Paragraph 1", char_span_start=0, char_span_end=13, confidence=0.9, method="regex", status="approved")
    db.add(ee)
    db.commit()
    db.close()

    # Generate PDF Dossier: POST /cases/{id}/reports
    req_body = {
        "report_title": "Court Submission Dossier (Sec. 63 BSA 2023)",
        "format": "pdf",
        "sections": {
            "overview": True,
            "entities": True,
            "cdr": True,
            "financial": True,
            "documents": True,
            "audit": True
        },
        "officer_name": "R. K. Sharma",
        "officer_rank": "Assistant Commissioner of Police",
        "officer_station": "Cyber Police Station, Central",
        "officer_unit": "Special Investigation Unit",
        "officer_remarks": "Prepared for transmission to judicial magistrate."
    }

    res = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json=req_body)
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == case_id
    assert data["format"] == "pdf"
    assert data["filename"].endswith(".pdf")
    assert len(data["sha256"]) == 64
    report_id = data["id"]

    # Verify report is staged in database
    db = SessionLocal()
    rep = db.query(Report).filter(Report.id == report_id).first()
    assert rep is not None
    assert rep.sha256 == data["sha256"]
    stored_path = rep.stored_path
    db.close()

    # Verify physical file on disk starts with valid %PDF magic bytes
    assert os.path.exists(stored_path)
    with open(stored_path, "rb") as f:
        header = f.read(5)
        assert header == b"%PDF-"
        f.seek(0)
        actual_sha = hashlib.sha256(f.read()).hexdigest()
        assert actual_sha == data["sha256"]

# ---------------------------------------------------------------------
# 2. Section 63 BSA 2023 JSON Case Export
# ---------------------------------------------------------------------
def test_generate_json_export_report():
    token = get_token("inv_reporter_2")
    case_id = create_case(token, "JSON Dossier Export Case")

    req_body = {
        "report_title": "Full Case Machine Readable Export",
        "format": "json",
        "officer_name": "S. Verma",
        "officer_rank": "Inspector",
        "officer_station": "Crime Branch",
        "officer_unit": "Anti-Financial Fraud Division"
    }

    res = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "json"
    assert data["filename"].endswith(".json")
    assert len(data["sha256"]) == 64

    # Verify file content
    db = SessionLocal()
    rep = db.query(Report).filter(Report.id == data["id"]).first()
    stored_path = rep.stored_path
    db.close()

    assert os.path.exists(stored_path)
    with open(stored_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        assert json_data["export_metadata"]["statutory_standard"] == "Section 63 Bharatiya Sakshya Adhiniyam, 2023"
        assert json_data["case"]["id"] == case_id
        assert "evidence_inventory" in json_data
        assert "entities" in json_data
        assert "cryptographic_audit" in json_data

# ---------------------------------------------------------------------
# 3. Report Listing API
# ---------------------------------------------------------------------
def test_list_case_reports():
    token = get_token("inv_reporter_3")
    case_id = create_case(token, "List Reports Case")

    # Create 2 reports
    client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json={"report_title": "Report 1", "format": "pdf"})
    client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json={"report_title": "Report 2", "format": "json"})

    # List reports: GET /cases/{id}/reports
    res = client.get(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    reports_list = res.json()
    assert len(reports_list) >= 2
    titles = [r["report_title"] for r in reports_list]
    assert "Report 1" in titles
    assert "Report 2" in titles

# ---------------------------------------------------------------------
# 4. Report Download Endpoints
# ---------------------------------------------------------------------
def test_download_report_pdf_and_json():
    token = get_token("inv_reporter_4")
    case_id = create_case(token, "Download Report Case")

    # Generate PDF report
    pdf_res = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json={"report_title": "Download Test PDF", "format": "pdf"})
    pdf_id = pdf_res.json()["id"]

    # Download PDF: GET /reports/{id}/download
    dl_pdf = client.get(f"/reports/{pdf_id}/download", headers={"Authorization": f"Bearer {token}"})
    assert dl_pdf.status_code == 200
    assert dl_pdf.headers["content-type"] == "application/pdf"
    assert dl_pdf.content.startswith(b"%PDF-")

    # Generate JSON report
    json_res = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {token}"}, json={"report_title": "Download Test JSON", "format": "json"})
    json_id = json_res.json()["id"]

    # Download JSON: GET /reports/{id}/download
    dl_json = client.get(f"/reports/{json_id}/download", headers={"Authorization": f"Bearer {token}"})
    assert dl_json.status_code == 200
    assert "application/json" in dl_json.headers["content-type"]

# ---------------------------------------------------------------------
# 5. Direct Case JSON Export Convenience Endpoint
# ---------------------------------------------------------------------
def test_direct_case_export_json_endpoint():
    token = get_token("inv_reporter_5")
    case_id = create_case(token, "Direct Export Case")

    res = client.get(f"/cases/{case_id}/export/json", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    exported = res.json()
    assert exported["export_metadata"]["system"] == "Case Connect AI (v1.0)"
    assert exported["case"]["id"] == case_id

# ---------------------------------------------------------------------
# 6. Access Control & Authorization (RBAC & IDOR)
# ---------------------------------------------------------------------
def test_reports_access_control():
    inv_token = get_token("inv_owner_rep", "investigator")
    viewer_token = get_token("viewer_rep", "viewer")
    other_token = get_token("inv_unauthorized_rep", "investigator")

    case_id = create_case(inv_token, "RBAC Security Report Case")

    # Viewer cannot generate reports (requires admin or investigator)
    res_viewer = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {viewer_token}"}, json={"report_title": "Viewer Attempt"})
    assert res_viewer.status_code == 403

    # Generate report as owner
    gen_res = client.post(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {inv_token}"}, json={"report_title": "Owner Report"})
    assert gen_res.status_code == 200
    rep_id = gen_res.json()["id"]

    # Unauthorized user (not a member of the case) cannot list or download report
    res_unauth_list = client.get(f"/cases/{case_id}/reports", headers={"Authorization": f"Bearer {other_token}"})
    assert res_unauth_list.status_code in [403, 404]

    res_unauth_dl = client.get(f"/reports/{rep_id}/download", headers={"Authorization": f"Bearer {other_token}"})
    assert res_unauth_dl.status_code in [403, 404]
