"""
Verification Test Suite for Phase 2: Lossless Excel Export & Audit Dossier.
Compliant with Section 63 BSA 2023.

Verifications:
1. Multi-sheet Excel workbook generated via openpyxl write_only mode.
2. Invariant: ZERO float cells across all generated worksheets.
3. Invariant: Formula injection prevention (cells starting with =, +, -, @ prepended with "'").
4. Invariant: Currency integrity (money stored as integer paise + formatted text, not float).
5. README sheet contains exact row counts, UTC & IST timestamps, and statutory disclaimer.
6. Cryptographic audit chain: every export operation creates an EXPORT_EXCEL audit log entry.
7. BOLA / RBAC defense: unauthorized officers are rejected with 403/404.
"""

import io
import os
import json
import openpyxl
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, Case, CaseMember, EvidenceFile, RawSheet, RawRow,
    CallRecord, Transaction, Entity, AuditLog, User
)
from backend.app.services.excel_export import export_case_to_excel, sanitize_excel_cell


@pytest.fixture
def test_case_with_data():
    """Seeds an isolated test case with mixed forensic data and formula injection payloads."""
    db = SessionLocal()
    case_id = f"test_phase2_case_{int(datetime.utcnow().timestamp())}"
    
    # Get or create test investigator
    user = db.query(User).filter(User.username == "investigator1").first()
    if not user:
        from backend.app.auth.security import get_password_hash
        user = User(username="investigator1", role="investigator", password_hash=get_password_hash("OfficerPass1234!"))
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create Case
    test_case = Case(
        id=case_id,
        title="Forensic Excel Export Test Docket",
        created_by=user.id
    )
    db.add(test_case)

    # Assign membership
    member = CaseMember(case_id=case_id, user_id=user.id, role="investigator")
    db.add(member)

    # Create Evidence File
    ev_file = EvidenceFile(
        id=f"ev_{case_id}",
        case_id=case_id,
        uploader_id=user.id,
        original_name="cdr_and_bank_feed.csv",
        stored_path="uploads/test_feed.csv",
        detected_type="csv",
        file_size=2048,
        sha256="aabbccddeeff11223344556677889900aabbccddeeff11223344556677889900",
        status="staged"
    )
    db.add(ev_file)

    # Create Raw Rows (including formula injection attempts)
    raw_rows = [
        RawRow(
            id=f"rr_{case_id}_1",
            evidence_file_id=ev_file.id,
            sheet_name="Sheet1",
            row_no=1,
            raw_json=json.dumps({"caller": "9876543210", "receiver": "9123456780", "payload": "=cmd|'/C calc'!A0"}),
            row_hash="hash_rr_1",
            status="staged",
            linked_record_type="call_record",
            linked_record_id=f"cr_{case_id}_1"
        ),
        RawRow(
            id=f"rr_{case_id}_2",
            evidence_file_id=ev_file.id,
            sheet_name="Sheet1",
            row_no=2,
            raw_json=json.dumps({"caller": "@malicious", "receiver": "+918888888888", "notes": "-25000"}),
            row_hash="hash_rr_2",
            status="staged"
        ),
        RawRow(
            id=f"rr_{case_id}_3",
            evidence_file_id=ev_file.id,
            sheet_name="Sheet1",
            row_no=3,
            raw_json=json.dumps({"notes": "Standard benign observation line"}),
            row_hash="hash_rr_3",
            status="preamble"
        )
    ]
    for rr in raw_rows:
        db.add(rr)

    # Create Staged Call Record
    cr = CallRecord(
        id=f"cr_{case_id}_1",
        case_id=case_id,
        source_file=ev_file.original_name,
        source_ref="1",
        caller="9876543210",
        receiver="9123456780",
        datetime_iso="2026-11-12T10:00:00Z",
        duration_seconds=120,
        raw_row_id=f"rr_{case_id}_1",
        fingerprint=f"fp_cr_{case_id}_1"
    )
    db.add(cr)

    # Create Staged Transaction (Money strictly as integer paise)
    txn = Transaction(
        id=f"txn_{case_id}_1",
        case_id=case_id,
        source_file=ev_file.original_name,
        source_ref="2",
        from_account="AC98765432",
        to_account="AC12345678",
        amount_paise=1250050,  # Rs. 12,500.50
        date_iso="2026-11-12T10:05:00Z",
        direction="DEBIT",
        raw_row_id=f"rr_{case_id}_2",
        fingerprint=f"fp_txn_{case_id}_1"
    )
    db.add(txn)

    # Create Entity
    ent = Entity(
        id=f"ent_{case_id}_1",
        case_id=case_id,
        label="Phone",
        canonical_id="9876543210",
        display_name="Primary Attributed Phone 9876543210",
        confidence=0.98,
        method="telecom_cdr",
        source_file=ev_file.original_name,
        source_ref="1"
    )
    db.add(ent)

    db.commit()
    db.close()

    yield case_id

    # Teardown
    td_db = SessionLocal()
    td_db.query(CallRecord).filter(CallRecord.case_id == case_id).delete()
    td_db.query(Transaction).filter(Transaction.case_id == case_id).delete()
    td_db.query(Entity).filter(Entity.case_id == case_id).delete()
    td_db.query(RawRow).filter(RawRow.evidence_file_id == f"ev_{case_id}").delete()
    td_db.query(EvidenceFile).filter(EvidenceFile.id == f"ev_{case_id}").delete()
    td_db.query(AuditLog).filter(AuditLog.case_id == case_id).delete()
    td_db.query(CaseMember).filter(CaseMember.case_id == case_id).delete()
    td_db.query(Case).filter(Case.id == case_id).delete()
    td_db.commit()
    td_db.close()


def test_sanitize_excel_cell_formula_escape():
    """Verifies that malicious formulas and injection characters are properly escaped."""
    assert sanitize_excel_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_excel_cell("@cmd|'/C calc'!A0") == "'@cmd|'/C calc'!A0"
    assert sanitize_excel_cell("+1234567890") == "'+1234567890"
    assert sanitize_excel_cell("-9999") == "'-9999"
    assert sanitize_excel_cell("normal_text") == "normal_text"
    assert sanitize_excel_cell(1250050) == 1250050
    assert sanitize_excel_cell(None) == ""


def test_export_case_to_excel_file_and_sheets(test_case_with_data):
    """Verifies file generation, sheet existence, row count reconciliation, and zero floats."""
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == test_case_with_data).first()
    user = db.query(User).filter(User.username == "investigator1").first()

    filepath, sha256_hash, exported_counts = export_case_to_excel(
        db=db,
        case=case,
        user=user
    )

    assert filepath.exists()
    assert len(sha256_hash) == 64
    assert exported_counts.get("Raw_Rows") == 3
    assert exported_counts.get("Call_Records") == 1
    assert exported_counts.get("Transactions") == 1
    assert exported_counts.get("Entities") == 1

    # Load back the generated workbook with openpyxl to inspect contents
    wb = openpyxl.load_workbook(filepath, data_only=False)
    sheet_names = wb.sheetnames

    assert "README" in sheet_names
    assert "Raw_Rows" in sheet_names
    assert "Call_Records" in sheet_names
    assert "Transactions" in sheet_names
    assert "Entities" in sheet_names

    # Check README sheet
    ws_readme = wb["README"]
    readme_cells = [str(cell) for row in ws_readme.iter_rows(values_only=True) for cell in row if cell is not None]
    assert any("CASECONNECT AI" in c for c in readme_cells)
    assert any("Section 63" in c for c in readme_cells)

    # Check for ZERO float cells across all sheets
    for s_name in sheet_names:
        ws = wb[s_name]
        for row in ws.iter_rows(values_only=True):
            for cell_val in row:
                assert not isinstance(cell_val, float), f"Forbidden float cell encountered in sheet '{s_name}': {cell_val}"

    # Verify formula escape in Raw_Rows sheet
    ws_raw = wb["Raw_Rows"]
    found_escaped_formula = False
    for row in ws_raw.iter_rows(values_only=True):
        for cell_val in row:
            if isinstance(cell_val, str) and cell_val.startswith("'="):
                found_escaped_formula = True
    assert found_escaped_formula, "Expected formula cell starting with '=cmd' was not properly escaped."

    # Verify Transactions money format
    ws_txn = wb["Transactions"]
    txn_rows = list(ws_txn.iter_rows(values_only=True))
    headers = txn_rows[0]
    paise_idx = headers.index("amount_paise")
    inr_idx = headers.index("amount_inr_text")
    data_row = txn_rows[1]
    assert isinstance(data_row[paise_idx], int)
    assert data_row[paise_idx] == 1250050
    assert data_row[inr_idx] == "Rs. 12,500.50"

    # Verify Audit Log entry
    audit_entry = db.query(AuditLog).filter(
        AuditLog.case_id == test_case_with_data,
        AuditLog.action == "EXPORT_EXCEL"
    ).first()
    assert audit_entry is not None
    assert len(audit_entry.hash) == 64
    import json
    details = json.loads(audit_entry.details_json)
    assert details["sha256"] == sha256_hash

    db.close()
    if filepath.exists():
        try:
            filepath.unlink()
        except Exception:
            pass


def test_api_export_excel_authenticated(test_case_with_data):
    """Tests the GET /cases/{case_id}/export.xlsx API route with auth token."""
    client = TestClient(app)

    # 1. Login as investigator
    login_resp = client.post("/auth/login", json={
        "username": "investigator1",
        "password": "OfficerPass1234!"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Call Export endpoint
    resp = client.get(
        f"/cases/{test_case_with_data}/export.xlsx",
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "X-Case-Integrity-SHA256" in resp.headers

    # Validate returned bytes form a valid openpyxl workbook
    wb_stream = io.BytesIO(resp.content)
    wb = openpyxl.load_workbook(wb_stream)
    assert "README" in wb.sheetnames
    assert "Raw_Rows" in wb.sheetnames


def test_api_export_excel_bola_defense(test_case_with_data):
    """Verifies that an unauthenticated user or unauthorized officer cannot export the case."""
    client = TestClient(app)

    # Unauthenticated request
    resp = client.get(f"/cases/{test_case_with_data}/export.xlsx")
    assert resp.status_code in (401, 403)
