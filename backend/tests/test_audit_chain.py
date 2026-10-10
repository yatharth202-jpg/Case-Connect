import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, User, AuditLog
from backend.app.auth.security import hash_password
from backend.app.audit.service import record_audit_log, verify_audit_chain

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

def test_audit_chain_validity():
    db = SessionLocal()
    # Write a sequence of entries
    u = db.query(User).first()
    user_id = u.id if u else "system_user"

    log1 = record_audit_log(db, user_id=user_id, action="test_action_1", details={"step": 1})
    log2 = record_audit_log(db, user_id=user_id, action="test_action_2", details={"step": 2})
    log3 = record_audit_log(db, user_id=user_id, action="test_action_3", details={"step": 3})

    assert log2.prev_hash == log1.hash
    assert log3.prev_hash == log2.hash

    verification = verify_audit_chain(db)
    assert verification["valid"] is True
    assert verification["checked_rows"] >= 3
    assert verification["broken_at"] is None
    db.close()

def test_audit_verify_endpoint_admin_only():
    admin_token = get_token("audit_admin_user", "admin")
    inves_token = get_token("audit_inves_user", "investigator")

    # Investigator gets 403
    inves_res = client.get("/audit/verify", headers={"Authorization": f"Bearer {inves_token}"})
    assert inves_res.status_code == 403

    # Admin gets 200 with verification result
    admin_res = client.get("/audit/verify", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200
    assert "valid" in admin_res.json()
    assert "checked_rows" in admin_res.json()

def test_tampering_breaks_audit_chain():
    db = SessionLocal()
    u = db.query(User).first()
    user_id = u.id if u else "system_user"

    # Add fresh log rows
    entry_a = record_audit_log(db, user_id=user_id, action="pre_tamper_event", details={"data": "secure_a"})
    entry_b = record_audit_log(db, user_id=user_id, action="target_event", details={"data": "secure_b"})
    entry_c = record_audit_log(db, user_id=user_id, action="post_tamper_event", details={"data": "secure_c"})

    # Tamper with entry_b directly in SQLite (simulate rogue DBA tampering)
    entry_b.details_json = '{"data":"MALICIOUS_ALTERATION"}'
    db.commit()

    # Verification must catch the tampering and return valid=False
    tamper_result = verify_audit_chain(db)
    assert tamper_result["valid"] is False
    assert tamper_result["broken_at"] is not None
    assert "tampering detected" in tamper_result["error"].lower() or "broken" in tamper_result["error"].lower()

    # Revert alteration to leave test DB healthy
    from backend.app.audit.service import compute_row_hash
    entry_b.details_json = '{"data":"secure_b"}'
    db.commit()
    db.close()
