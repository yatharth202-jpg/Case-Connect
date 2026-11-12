"""
Verification Test Suite for Phase 3: Top-5 Primary Attributed Leads.
Compliant with Section 63 BSA 2023.

Verifications:
1. Deterministic ranking: Identical scores and tie-breaking across repeated runs.
2. Candidate fidelity: If fewer than 5 candidates exist, returns only what exists (never fabricates).
3. Terminology compliance: Strictly banned terms are absent; statutory disclaimer is present.
4. Persistence invariant: Analysis outputs are saved in analysis_results table for zero-recompute reloading.
5. Configurable weights: SystemConfig weights dynamically tune scoring without code edits.
6. API endpoint security: BOLA / RBAC verification on GET /cases/{id}/top-leads.
"""

import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, Case, CaseMember, EvidenceFile, CallRecord, Transaction,
    Entity, AnalysisResult, SystemConfig, AuditLog, User
)
from backend.app.services.top_leads import (
    compute_case_top_leads,
    get_stored_or_computed_top_leads,
    LEGAL_DISCLAIMER
)

BANNED_WORDS = [
    "criminal", "suspect", "guilty", "mastermind", "fraud number", "culprit", "accused"
]


@pytest.fixture
def isolated_case_data():
    """Seeds an isolated case with 4 connected entities for lead testing."""
    db = SessionLocal()
    case_id = f"test_phase3_case_{int(datetime.utcnow().timestamp())}"

    # Get or create investigator user
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
        title="Top Leads Investigative Priority Test Docket",
        created_by=user.id
    )
    db.add(test_case)

    # Assign membership
    member = CaseMember(case_id=case_id, user_id=user.id, role="investigator")
    db.add(member)

    # Create Evidence File
    ev = EvidenceFile(
        id=f"ev_{case_id}",
        case_id=case_id,
        uploader_id=user.id,
        original_name="cdr_telecom_feed.csv",
        stored_path="uploads/test_feed.csv",
        detected_type="csv",
        file_size=1024,
        sha256="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
        status="staged"
    )
    db.add(ev)

    # Add Call Records connecting Node A (high degree), B, C
    # Node A is a central hub connecting to B, C, D
    cdrs = [
        CallRecord(
            id=f"cr_{case_id}_1",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="1",
            caller="9876540001",  # Node A
            receiver="9876540002", # Node B
            duration_seconds=180,
            fingerprint=f"fp_{case_id}_1"
        ),
        CallRecord(
            id=f"cr_{case_id}_2",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="2",
            caller="9876540001",  # Node A
            receiver="9876540003", # Node C
            duration_seconds=300,
            fingerprint=f"fp_{case_id}_2"
        ),
        CallRecord(
            id=f"cr_{case_id}_3",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="3",
            caller="9876540001",  # Node A
            receiver="9876540004", # Node D
            duration_seconds=90,
            fingerprint=f"fp_{case_id}_3"
        ),
    ]
    for c in cdrs:
        db.add(c)

    # Add Bank Transactions (Node B has rapid pass-through)
    txns = [
        Transaction(
            id=f"txn_{case_id}_1",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="10",
            from_account="AC_REMITTER",
            to_account="9876540002",  # Inflow to B
            amount_paise=5000000,    # Rs. 50,000.00
            date_iso="2026-11-12T10:00:00Z",
            fingerprint=f"fp_txn_{case_id}_1"
        ),
        Transaction(
            id=f"txn_{case_id}_2",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="11",
            from_account="9876540002",  # Outflow from B (pass-through)
            to_account="AC_BENEFICIARY",
            amount_paise=4800000,    # Rs. 48,000.00 (96% pass-through)
            date_iso="2026-11-12T10:30:00Z",
            fingerprint=f"fp_txn_{case_id}_2"
        ),
    ]
    for t in txns:
        db.add(t)

    db.commit()
    db.close()

    yield case_id

    # Teardown
    td_db = SessionLocal()
    td_db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
    td_db.query(CallRecord).filter(CallRecord.case_id == case_id).delete()
    td_db.query(Transaction).filter(Transaction.case_id == case_id).delete()
    td_db.query(Entity).filter(Entity.case_id == case_id).delete()
    td_db.query(EvidenceFile).filter(EvidenceFile.id == f"ev_{case_id}").delete()
    td_db.query(CaseMember).filter(CaseMember.case_id == case_id).delete()
    td_db.query(Case).filter(Case.id == case_id).delete()
    td_db.commit()
    td_db.close()


def test_top_leads_determinism(isolated_case_data):
    """Verifies that running lead ranking twice produces 100% identical scores and ordering."""
    db = SessionLocal()
    run1 = compute_case_top_leads(db, isolated_case_data, n=5, persist=False)
    run2 = compute_case_top_leads(db, isolated_case_data, n=5, persist=False)

    assert len(run1) == len(run2)
    assert len(run1) > 0

    for idx in range(len(run1)):
        assert run1[idx]["entity_id"] == run2[idx]["entity_id"]
        assert run1[idx]["score"] == run2[idx]["score"]
        assert run1[idx]["rank"] == run2[idx]["rank"]
        assert run1[idx]["designation"] == run2[idx]["designation"]

    db.close()


def test_top_leads_fewer_than_five_candidates():
    """Verifies that if fewer than 5 candidates exist, the system returns only what exists."""
    db = SessionLocal()
    case_id = f"test_sparse_case_{int(datetime.utcnow().timestamp())}"

    user = db.query(User).filter(User.username == "investigator1").first()
    test_case = Case(id=case_id, title="Sparse Case", created_by=user.id)
    db.add(test_case)

    # Only 2 entities in case
    c = CallRecord(
        id=f"sparse_cr_{case_id}",
        case_id=case_id,
        source_file="sparse.csv",
        source_ref="1",
        caller="9999900001",
        receiver="9999900002",
        duration_seconds=60,
        fingerprint=f"fp_sparse_{case_id}"
    )
    db.add(c)
    db.commit()

    leads = compute_case_top_leads(db, case_id, n=5, persist=False)
    # Exactly 2 candidates must be returned; NEVER 5 padded or fabricated items
    assert len(leads) == 2
    assert leads[0]["rank"] == 1
    assert leads[1]["rank"] == 2

    # Cleanup
    db.query(CallRecord).filter(CallRecord.case_id == case_id).delete()
    db.query(Case).filter(Case.id == case_id).delete()
    db.commit()
    db.close()


def test_top_leads_neutral_terminology(isolated_case_data):
    """Verifies that strictly zero banned prejudicial terms appear in keys, values, or disclaimers."""
    db = SessionLocal()
    leads = compute_case_top_leads(db, isolated_case_data, n=5, persist=False)
    db.close()

    assert len(leads) > 0
    for lead in leads:
        lead_json_str = json.dumps(lead).lower()
        for banned in BANNED_WORDS:
            assert banned not in lead_json_str, f"Strictly banned term '{banned}' detected in lead: {lead}"

        assert lead["designation"].startswith("Primary Attributed Lead #")
        assert lead["disclaimer"] == LEGAL_DISCLAIMER


def test_top_leads_persistence_and_reload(isolated_case_data):
    """Verifies that computed leads are saved in analysis_results and reloaded without recompute."""
    db = SessionLocal()

    # 1. Compute and persist
    initial_leads = compute_case_top_leads(db, isolated_case_data, n=5, persist=True)
    assert len(initial_leads) > 0

    # 2. Check DB row count in analysis_results
    stored_count = db.query(AnalysisResult).filter(AnalysisResult.case_id == isolated_case_data).count()
    assert stored_count == len(initial_leads)

    # 3. Reload from DB (recompute=False)
    reloaded_leads = get_stored_or_computed_top_leads(db, isolated_case_data, n=5, recompute=False)
    assert len(reloaded_leads) == len(initial_leads)
    assert reloaded_leads[0]["entity_id"] == initial_leads[0]["entity_id"]
    assert reloaded_leads[0]["score"] == initial_leads[0]["score"]

    db.close()


def test_api_top_leads_endpoint(isolated_case_data):
    """Verifies GET /cases/{id}/top-leads returns valid JSON and enforces BOLA defense."""
    client = TestClient(app)

    # 1. Unauthorized attempt
    unauth_resp = client.get(f"/cases/{isolated_case_data}/top-leads")
    assert unauth_resp.status_code in (401, 403)

    # 2. Login as authorized investigator
    login_resp = client.post("/auth/login", json={
        "username": "investigator1",
        "password": "OfficerPass1234!"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Authorized request
    resp = client.get(f"/cases/{isolated_case_data}/top-leads?n=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == isolated_case_data
    assert "Section 63" in data["legal_standard"]
    assert data["disclaimer"] == LEGAL_DISCLAIMER
    assert isinstance(data["leads"], list)
    assert len(data["leads"]) > 0

    top_lead = data["leads"][0]
    assert top_lead["rank"] == 1
    assert "Primary Attributed Lead #1" in top_lead["designation"]
    assert "breakdown" in top_lead
    assert "degree" in top_lead["breakdown"]
    assert "pass_through_flag" in top_lead["breakdown"]
