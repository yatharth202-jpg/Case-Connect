import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, User
from backend.app.auth.security import hash_password

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_auth_users():
    db = SessionLocal()
    # Create test users if they don't exist
    for uname, role in [("test_admin", "admin"), ("test_inves", "investigator"), ("test_viewer", "viewer")]:
        existing = db.query(User).filter(User.username == uname).first()
        if not existing:
            u = User(
                username=uname,
                password_hash=hash_password("Pass1234!"),
                role=role,
                is_active=True
            )
            db.add(u)
    db.commit()
    db.close()

def test_login_success():
    res = client.post("/auth/login", json={"username": "test_admin", "password": "Pass1234!"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "test_admin"
    assert data["user"]["role"] == "admin"

def test_login_invalid_password():
    res = client.post("/auth/login", json={"username": "test_admin", "password": "WrongPassword"})
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json()["detail"]

def test_login_nonexistent_user():
    res = client.post("/auth/login", json={"username": "nobody_exists", "password": "Pass1234!"})
    assert res.status_code == 401

def test_get_me_authenticated():
    # Login first
    login_res = client.post("/auth/login", json={"username": "test_inves", "password": "Pass1234!"})
    token = login_res.json()["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "test_inves"
    assert data["role"] == "investigator"

def test_get_me_unauthenticated():
    res = client.get("/auth/me")
    assert res.status_code == 401

def test_logout_records_audit():
    login_res = client.post("/auth/login", json={"username": "test_admin", "password": "Pass1234!"})
    token = login_res.json()["access_token"]

    res = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"
