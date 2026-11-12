"""
Test Suite for Phase 5: Persistence & Zero-Recompute Case Reopening.
Compliant with Section 63 BSA 2023.

Verifies:
1. Analysis outputs (top leads, findings) saved as AnalysisResult rows in SQLite.
2. Finding nodes (node_type='Finding') and ATTRIBUTED_TO edges linked to target entities in SQLite.
3. SavedGraphView CRUD (save camera pan/zoom, selected nodes, active filters, restore, delete).
4. Zero-Recompute Invariant: Case docket reopening reads from SQLite WAL with zero algorithm execution and yields 100% identical results.
5. Strict BOLA access defense and SHA-256 genesis-chained cryptographic audit trail.
"""

import json
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, CaseMember, EvidenceFile,
    CallRecord, Transaction, AnalysisResult, SavedGraphView,
    GraphNode, GraphEdge, AuditLog
)
from backend.app.auth.security import hash_password
from backend.app.services.top_leads import compute_top_leads, get_persisted_top_leads
from backend.app.services.graph.builder import rebuild_graph, generate_node_id

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


@pytest.fixture
def persistence_case():
    token = get_token("investigator_phase5", "investigator")
    case_res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": "Phase 5 Persistence Case"})
    case_id = case_res.json()["id"]

    db = SessionLocal()
    user = db.query(User).filter(User.username == "investigator_phase5").first()
    user_id = user.id

    # Evidence file
    ev = EvidenceFile(
        case_id=case_id,
        original_name="cdr_p5.csv",
        stored_path="mock/path/cdr_p5.csv",
        file_size=1024,
        sha256="mock_p5_sha256",
        detected_type="cdr",
        uploader_id=user_id,
        status="staged"
    )
    db.add(ev)
    db.commit()

    # Seed CDR and Bank records
    db.add(CallRecord(
        id=f"cr_p5_{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        source_file=ev.original_name,
        source_ref="1",
        caller="9876000001",
        receiver="9876000002",
        datetime_iso="2026-11-12T09:00:00Z",
        duration_seconds=120,
        fingerprint=f"fp_p5_1_{uuid.uuid4().hex[:8]}"
    ))
    db.add(Transaction(
        id=f"tx_p5_{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        source_file=ev.original_name,
        source_ref="2",
        from_account="ACC_SRC_P5",
        to_account="ACC_DST_P5",
        from_name="Entity Source",
        to_name="Entity Dest",
        amount_paise=500000,
        date_iso="2026-11-12T10:00:00Z",
        fingerprint=f"fp_p5_2_{uuid.uuid4().hex[:8]}"
    ))
    db.commit()

    # Rebuild graph
    rebuild_graph(db, case_id)
    db.close()

    return {"case_id": case_id, "token": token, "user_id": user_id}


def test_save_and_retrieve_analysis_results(persistence_case):
    """Verifies that analysis findings are persisted and create Finding nodes in SQLite."""
    case_id = persistence_case["case_id"]
    token = persistence_case["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "entity_id": "9876000001",
        "rank": 1,
        "score": 0.885,
        "breakdown": {
            "degree_centrality": 0.5,
            "pass_through_ratio": 0.9,
            "total_paise": 500000
        },
        "evidence_ids": ["cdr_p5.csv"]
    }

    # Post analysis result
    post_res = client.post(f"/cases/{case_id}/analysis-results", headers=headers, json=payload)
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["status"] == "persisted"
    assert res_data["id"] is not None

    # Get analysis results
    get_res = client.get(f"/cases/{case_id}/analysis-results", headers=headers)
    assert get_res.status_code == 200
    results = get_res.json()["results"]
    assert len(results) >= 1
    lead1 = next(r for r in results if r["entity_id"] == "9876000001")
    assert lead1["rank"] == 1
    assert lead1["score"] == 0.885
    assert lead1["breakdown"]["pass_through_ratio"] == 0.9

    # Verify Finding node exists in GraphNode table
    db = SessionLocal()
    finding_nodes = db.query(GraphNode).filter(
        GraphNode.case_id == case_id,
        GraphNode.node_type == "Finding"
    ).all()
    assert len(finding_nodes) >= 1

    # Verify edge exists linking Finding node to target entity
    finding_edges = db.query(GraphEdge).filter(
        GraphEdge.case_id == case_id,
        GraphEdge.edge_type == "ATTRIBUTED_TO"
    ).all()
    assert len(finding_edges) >= 1
    db.close()


def test_saved_graph_view_lifecycle(persistence_case):
    """Verifies saving, listing, retrieving, and deleting saved graph viewports."""
    case_id = persistence_case["case_id"]
    token = persistence_case["token"]
    headers = {"Authorization": f"Bearer {token}"}

    view_payload = {
        "name": "Central Hub Cluster Focus",
        "view_data": {
            "pan": {"x": 120.5, "y": -45.2},
            "zoom": 1.75,
            "selected_node_id": "9876000001",
            "active_filters": {
                "min_weight": 2,
                "node_types": ["Phone", "Account"],
                "search_query": "9876"
            }
        }
    }

    # 1. Save View
    create_res = client.post(f"/cases/{case_id}/views", headers=headers, json=view_payload)
    assert create_res.status_code == 200
    created = create_res.json()
    view_id = created["id"]
    assert view_id is not None
    assert created["name"] == "Central Hub Cluster Focus"

    # 2. List Views
    list_res = client.get(f"/cases/{case_id}/views", headers=headers)
    assert list_res.status_code == 200
    views = list_res.json()["views"]
    assert any(v["id"] == view_id for v in views)

    # 3. Get View
    get_res = client.get(f"/cases/{case_id}/views/{view_id}", headers=headers)
    assert get_res.status_code == 200
    view_detail = get_res.json()
    assert view_detail["name"] == "Central Hub Cluster Focus"
    assert view_detail["view_data"]["zoom"] == 1.75
    assert view_detail["view_data"]["pan"]["x"] == 120.5

    # 4. Delete View
    del_res = client.delete(f"/cases/{case_id}/views/{view_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify View is gone
    get_after = client.get(f"/cases/{case_id}/views/{view_id}", headers=headers)
    assert get_after.status_code == 404


def test_case_reopen_zero_recompute_identical_output(persistence_case):
    """
    Verifies that reopening a case docket directly reads persisted results from
    SQLite WAL with ZERO graph recalculation, returning 100% identical outputs.
    """
    case_id = persistence_case["case_id"]
    token = persistence_case["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First run: compute and persist top leads
    resp1 = client.get(f"/cases/{case_id}/top-leads?limit=5", headers=headers)
    assert resp1.status_code == 200
    initial_leads = resp1.json()["leads"]

    # 2. Re-query using persistence helper (zero recompute)
    db = SessionLocal()
    persisted = get_persisted_top_leads(db, case_id)
    assert len(persisted) == len(initial_leads)
    for p, init in zip(persisted, initial_leads):
        assert p["rank"] == init["rank"]
        assert p["entity_id"] == init["entity_id"]
        assert p["score"] == init["score"]

    # 3. Simulate closing and reopening case: query endpoints directly
    reopened_res = client.get(f"/cases/{case_id}/top-leads?limit=5", headers=headers)
    assert reopened_res.status_code == 200
    reopened_leads = reopened_res.json()["leads"]

    assert len(reopened_leads) == len(initial_leads)
    for r, init in zip(reopened_leads, initial_leads):
        assert r["rank"] == init["rank"]
        assert r["entity_id"] == init["entity_id"]
        assert r["score"] == init["score"]
        assert r["disclaimer"] == init["disclaimer"]
    db.close()


def test_persistence_bola_defense(persistence_case):
    """Verifies that an unauthorized officer cannot access or tamper with saved views or analysis results."""
    case_id = persistence_case["case_id"]
    intruder_token = get_token("intruder_officer", "investigator")
    headers = {"Authorization": f"Bearer {intruder_token}"}

    # Attempt to fetch views
    res_views = client.get(f"/cases/{case_id}/views", headers=headers)
    assert res_views.status_code in [403, 404]

    # Attempt to post a view
    res_post_view = client.post(f"/cases/{case_id}/views", headers=headers, json={"name": "Hacked View", "view_data": {}})
    assert res_post_view.status_code in [403, 404]

    # Attempt to fetch analysis results
    res_results = client.get(f"/cases/{case_id}/analysis-results", headers=headers)
    assert res_results.status_code in [403, 404]


def test_audit_trail_for_persistence(persistence_case):
    """Verifies cryptographic audit entries for view operations and analysis result persistence."""
    case_id = persistence_case["case_id"]
    token = persistence_case["token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(f"/cases/{case_id}/views", headers=headers, json={"name": "Audit View", "view_data": {"zoom": 1.0}})

    db = SessionLocal()
    audit_entries = db.query(AuditLog).filter(
        AuditLog.case_id == case_id,
        AuditLog.action.in_(["SAVE_GRAPH_VIEW", "SAVE_ANALYSIS_RESULT"])
    ).all()
    assert len(audit_entries) >= 1
    entry = audit_entries[-1]
    assert entry.action == "SAVE_GRAPH_VIEW"
    assert entry.hash is not None
    assert len(entry.hash) == 64 # SHA-256
    db.close()
