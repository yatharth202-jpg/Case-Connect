import os
import stat
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, User, Case
from backend.app.auth.security import hash_password

client = TestClient(app)

def get_token(username: str, role: str) -> str:
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(username=username, password_hash=hash_password("Pass1234!"), role=role, is_active=True)
        db.add(u)
        db.commit()
    db.close()

    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    return res.json()["access_token"]

def create_test_case(token: str, title: str) -> str:
    res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": title})
    return res.json()["id"]

def test_evidence_upload_valid_csv():
    token = get_token("ev_investigator_1", "investigator")
    case_id = create_test_case(token, "Evidence Test Case 1")

    csv_content = b"call_id,caller,receiver,duration\n1,9876543210,9876543211,45\n"
    res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("cdr_sample.csv", csv_content, "text/csv")}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    ev = data[0]
    assert ev["original_name"] == "cdr_sample.csv"
    assert ev["detected_type"] == "cdr"
    assert len(ev["sha256"]) == 64

def test_evidence_magic_byte_validation_pdf():
    token = get_token("ev_investigator_2", "investigator")
    case_id = create_test_case(token, "PDF Validation Case")

    # Invalid PDF: missing %PDF header
    fake_pdf = b"NOT_A_REAL_PDF_HEADER_CONTENT"
    bad_res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("fake_document.pdf", fake_pdf, "application/pdf")}
    )
    assert bad_res.status_code == 400
    assert "Missing %PDF magic byte signature" in bad_res.json()["detail"]

    # Valid PDF signature
    valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    good_res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("real_document.pdf", valid_pdf, "application/pdf")}
    )
    assert good_res.status_code == 200

def test_evidence_verify_and_tamper_detection():
    token = get_token("ev_investigator_3", "investigator")
    case_id = create_test_case(token, "Integrity Verification Case")

    txt_content = b"FIR Statement: Money transferred to designated account."
    upload_res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("fir_report.txt", txt_content, "text/plain")}
    )
    ev_id = upload_res.json()[0]["id"]

    # 1. Verification should initially pass 100%
    verify_res = client.post(f"/evidence/{ev_id}/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify_res.status_code == 200
    assert verify_res.json()["valid"] is True
    assert verify_res.json()["stored_hash"] == verify_res.json()["computed_hash"]

    # 2. Tamper with the file on disk
    from backend.app.db.sql import EvidenceFile
    db = SessionLocal()
    ev_record = db.query(EvidenceFile).filter(EvidenceFile.id == ev_id).first()
    file_path = Path(ev_record.stored_path)
    db.close()

    # Clear read-only attribute, modify contents, restore read-only
    os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
    with open(file_path, "ab") as f:
        f.write(b"\nTAMPERED_APPENDED_LINE")
    os.chmod(file_path, stat.S_IREAD)

    # 3. Verification should now FAIL and flag tampering
    tampered_verify = client.post(f"/evidence/{ev_id}/verify", headers={"Authorization": f"Bearer {token}"})
    assert tampered_verify.status_code == 200
    assert tampered_verify.json()["valid"] is False
    assert tampered_verify.json()["stored_hash"] != tampered_verify.json()["computed_hash"]

def test_non_member_cannot_verify_or_upload_evidence():
    token_owner = get_token("ev_owner_4", "investigator")
    token_stranger = get_token("ev_stranger_4", "investigator")
    case_id = create_test_case(token_owner, "Restricted Evidence Case")

    # Stranger cannot upload
    up_res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token_stranger}"},
        files={"files": ("file.csv", b"a,b\n1,2\n", "text/csv")}
    )
    assert up_res.status_code == 403

def test_delete_evidence():
    token = get_token("ev_investigator_5", "investigator")
    case_id = create_test_case(token, "Delete Evidence Case")

    res = client.post(
        f"/cases/{case_id}/evidence",
        headers={"Authorization": f"Bearer {token}"},
        files={"files": ("temp_file.txt", b"temporary data", "text/plain")}
    )
    ev_id = res.json()[0]["id"]

    del_res = client.delete(f"/evidence/{ev_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Confirm it's no longer listed
    list_res = client.get(f"/cases/{case_id}/evidence", headers={"Authorization": f"Bearer {token}"})
    assert not any(f["id"] == ev_id for f in list_res.json())
