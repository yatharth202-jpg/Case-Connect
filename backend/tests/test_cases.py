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

def test_create_case_as_investigator():
    token = get_token("case_investigator_1", "investigator")
    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Test Operation Alpha", "description": "Layered fraud enquiry", "priority": "high"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Test Operation Alpha"
    assert data["priority"] == "high"
    assert data["evidence_count"] == 0

def test_viewer_cannot_create_case():
    token = get_token("case_viewer_1", "viewer")
    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Unauthorized Case Creation", "priority": "low"}
    )
    assert res.status_code == 403

def test_case_membership_isolation_non_member_forbidden():
    # User 1 creates a case
    token1 = get_token("inves_owner", "investigator")
    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Confidential Ring Case", "priority": "high"}
    )
    case_id = res.json()["id"]

    # User 2 (not a member) tries to view it
    token2 = get_token("inves_stranger", "investigator")
    forbidden_res = client.get(
        f"/cases/{case_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert forbidden_res.status_code == 403
    assert "Access forbidden" in forbidden_res.json()["detail"]

    # Admin CAN view it even without explicit membership
    admin_token = get_token("case_admin_super", "admin")
    admin_res = client.get(
        f"/cases/{case_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["id"] == case_id

def test_add_member_grants_access():
    token1 = get_token("inves_owner_2", "investigator")
    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {token1}"},
        json={"title": "Joint Operation Beta", "priority": "medium"}
    )
    case_id = res.json()["id"]

    # Stranger user
    token_stranger = get_token("inves_stranger_2", "investigator")
    db = SessionLocal()
    stranger_user = db.query(User).filter(User.username == "inves_stranger_2").first()
    stranger_id = stranger_user.id
    db.close()

    # Before adding: 403
    assert client.get(f"/cases/{case_id}", headers={"Authorization": f"Bearer {token_stranger}"}).status_code == 403

    # Owner adds stranger as member
    add_res = client.post(
        f"/cases/{case_id}/members",
        headers={"Authorization": f"Bearer {token1}"},
        json={"user_id": stranger_id, "role": "analyst"}
    )
    assert add_res.status_code == 200

    # After adding: 200 OK
    assert client.get(f"/cases/{case_id}", headers={"Authorization": f"Bearer {token_stranger}"}).status_code == 200
