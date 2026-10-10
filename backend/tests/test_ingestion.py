import json
from pathlib import Path
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, User, Case, EvidenceFile, CallRecord, Transaction
from backend.app.auth.security import hash_password
from backend.app.services.ingestion.normalize import (
    normalize_phone, normalize_amount, normalize_datetime,
    normalize_account, normalize_duration, normalize_ip
)
from backend.app.services.ingestion.detect import detect_file_type
from backend.app.services.ingestion.mapping import suggest_column_mappings, compute_header_signature
from backend.app.services.ingestion.stage import stage_evidence_file

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

# ---------------------------------------------------------------------
# 1. Normalizer Unit Tests
# ---------------------------------------------------------------------

def test_normalize_phone_tricky_formats():
    # 1. Standard Indian 10-digit
    p1 = normalize_phone("9876543210")
    assert p1["valid_mobile"] is True
    assert p1["number"] == "9876543210"

    # 2. +91 prefix
    p2 = normalize_phone("+91 98765 43210")
    assert p2["valid_mobile"] is True
    assert p2["number"] == "9876543210"

    # 3. Leading trunk 0
    p3 = normalize_phone("09876543210")
    assert p3["valid_mobile"] is True
    assert p3["number"] == "9876543210"

    # 4. Alphanumeric SMS sender ID
    p4 = normalize_phone("AD-HDFCBK")
    assert p4["kind"] == "sms_header"
    assert p4["valid_mobile"] is False

    # 5. Landline / Short code
    p5 = normalize_phone("01123456789")
    assert p5["valid_mobile"] is False

    # 6. Invalid / Empty
    assert normalize_phone("") is None
    assert normalize_phone(None) is None

def test_normalize_amount_precision_never_float():
    # 1. Indian comma notation: 5,00,000.00 Rs -> 50,000,000 paise
    a1 = normalize_amount("5,00,000.00")
    assert a1 == 50000000

    # 2. Decimal representation: 1,250.50 -> 125050 paise
    a2 = normalize_amount("Rs 1,250.50")
    assert a2 == 125050

    # 3. Accounting brackets for negative / debit: (1,200) -> -120000 paise
    a3 = normalize_amount("(1,200)")
    assert a3 == -120000

    # 4. Dr indicator
    a4 = normalize_amount("450.75 Dr")
    assert a4 == -45075

    # 5. Invalid string returns None
    assert normalize_amount("invalid_amount") is None

def test_normalize_datetime_formats():
    # 1. ISO format
    d1, t1, iso1 = normalize_datetime("2026-08-15 14:30:00")
    assert d1 == "2026-08-15"
    assert t1 == "14:30:00"

    # 2. Indian dd/mm/yyyy
    d2, t2, iso2 = normalize_datetime("15/08/2026", "10:15:00")
    assert d2 == "2026-08-15"
    assert t2 == "10:15:00"

# ---------------------------------------------------------------------
# 2. Type Detection & Ingestion Integration Tests
# ---------------------------------------------------------------------

def test_detect_file_types_accurately():
    # CDR detection
    cdr_headers = ["A-Party", "B-Party", "Call Date", "Call Time", "Dur(sec)", "Call Type"]
    cdr_records = [{"A-Party": "9876543210", "B-Party": "9876543211", "Call Date": "15/08/2026"}]
    det_cdr = detect_file_type(cdr_headers, cdr_records, "cdr_test.xlsx")
    assert det_cdr["detected_type"] == "cdr"

    # Bank transactions detection
    bank_headers = ["Txn Date", "Remitter A/c", "Beneficiary A/c", "Amount (INR)", "Reference"]
    bank_records = [{"Remitter A/c": "100234567890", "Beneficiary A/c": "200987654321", "Amount (INR)": "5000"}]
    det_bank = detect_file_type(bank_headers, bank_records, "bank_messy.csv")
    assert det_bank["detected_type"] == "bank_transactions"

def test_staging_and_deduplication():
    token = get_token("stage_investigator", "investigator")

    # Create Case
    case_res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": "Ingestion Staging Case"})
    case_id = case_res.json()["id"]

    # Upload clean CDR sample
    clean_cdr_path = Path("data/synthetic/samples/clean/cdr.csv")
    if not clean_cdr_path.exists():
        pytest.skip("Sample clean CDR missing")

    with open(clean_cdr_path, "rb") as f:
        up_res = client.post(
            f"/cases/{case_id}/evidence",
            headers={"Authorization": f"Bearer {token}"},
            files={"files": ("cdr.csv", f, "text/csv")}
        )
    ev_id = up_res.json()[0]["id"]

    # 1. Preview
    prev_res = client.get(f"/evidence/{ev_id}/preview", headers={"Authorization": f"Bearer {token}"})
    assert prev_res.status_code == 200
    assert prev_res.json()["detected_type"] == "cdr"

    # 2. Confirm Mapping
    mapping = {h: prev_res.json()["suggested_mapping"][h]["canonical"] for h in prev_res.json()["headers"]}
    map_res = client.post(
        f"/evidence/{ev_id}/mapping",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_type": "cdr", "mapping": mapping}
    )
    assert map_res.status_code == 200

    # 3. Stage
    db = SessionLocal()
    u = db.query(User).filter(User.username == "stage_investigator").first()
    user_id = u.id

    result1 = stage_evidence_file(db, ev_id, user_id, "cdr", mapping)
    assert result1["rows_ingested"] > 0
    assert result1["duplicates_skipped"] == 0
    ingested_count = result1["rows_ingested"]

    # 4. Ingest again (Idempotence Test) - must NOT double rows
    result2 = stage_evidence_file(db, ev_id, user_id, "cdr", mapping)
    assert result2["rows_ingested"] == 0
    assert result2["duplicates_skipped"] == ingested_count
    db.close()

def test_mapping_template_reuse():
    token = get_token("tpl_investigator", "investigator")
    case_res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": "Template Reuse Case"})
    case_id = case_res.json()["id"]

    # Upload messy bank sample 1
    sample_path = Path("data/synthetic/samples/messy/bank_messy.csv")
    if not sample_path.exists():
        pytest.skip("Messy bank sample missing")

    with open(sample_path, "rb") as f:
        up_res1 = client.post(f"/cases/{case_id}/evidence", headers={"Authorization": f"Bearer {token}"}, files={"files": ("bank_1.csv", f, "text/csv")})
    ev1_id = up_res1.json()[0]["id"]

    # Preview and confirm mapping
    prev1 = client.get(f"/evidence/{ev1_id}/preview", headers={"Authorization": f"Bearer {token}"}).json()
    mapping = {h: prev1["suggested_mapping"][h]["canonical"] for h in prev1["headers"]}
    client.post(f"/evidence/{ev1_id}/mapping", headers={"Authorization": f"Bearer {token}"}, json={"file_type": "bank_transactions", "mapping": mapping})

    # Upload second file with same headers
    with open(sample_path, "rb") as f:
        up_res2 = client.post(f"/cases/{case_id}/evidence", headers={"Authorization": f"Bearer {token}"}, files={"files": ("bank_2.csv", f, "text/csv")})
    ev2_id = up_res2.json()[0]["id"]

    # Preview second file - should auto-apply template with 1.0 confidence
    prev2 = client.get(f"/evidence/{ev2_id}/preview", headers={"Authorization": f"Bearer {token}"}).json()
    assert prev2["header_signature"] == prev1["header_signature"]
    for h in prev2["headers"]:
        assert prev2["suggested_mapping"][h]["confidence"] == 1.0
