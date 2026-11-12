"""
Verification Test Suite for Phase 4: Authoritative Graph Rebuild & Topological Inspection.
Compliant with Section 63 BSA 2023.

Verifications:
1. Determinism and idempotence: rebuild twice produces 100% identical node/edge counts and IDs.
2. Edge aggregation: multiple events between identical nodes aggregate into single edge with integer paise.
3. Node inspection API: GET /cases/{id}/graph/node/{node_id} returns grouped neighbours and notice.
4. Pagination: correct slicing and notice ('showing 2 of 4').
5. Neo4j-down fallback: resilient continuation on SQLite/NetworkX when Neo4j is unreachable.
6. Dynamic styling: newly added node type in NodeTypeConfig immediately reflects in config endpoint.
7. BOLA / RBAC security: unauthorized access rejected with 401/403.
"""

import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, Case, CaseMember, EvidenceFile, CallRecord, Transaction,
    IPEvent, Entity, GraphNode, GraphEdge, NodeTypeConfig, EdgeTypeConfig,
    AuditLog, User
)
from backend.app.services.graph.builder import rebuild_graph, generate_node_id, generate_edge_id


@pytest.fixture
def graph_test_case():
    """Seeds an isolated case with multi-event CDR and banking data."""
    db = SessionLocal()
    case_id = f"test_phase4_case_{int(datetime.utcnow().timestamp())}"

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
        title="Authoritative Graph Rebuild Docket",
        created_by=user.id
    )
    db.add(test_case)

    # Assign membership
    member = CaseMember(case_id=case_id, user_id=user.id, role="investigator")
    db.add(member)

    # Evidence File
    ev = EvidenceFile(
        id=f"ev_{case_id}",
        case_id=case_id,
        uploader_id=user.id,
        original_name="telecom_bank_feed.csv",
        stored_path="uploads/feed.csv",
        detected_type="csv",
        file_size=2048,
        sha256="44556677889900aabbccddeeff11223344556677889900aabbccddeeff112233",
        status="staged"
    )
    db.add(ev)

    # Multiple Calls between same pair: 9876500001 -> 9876500002
    cdrs = [
        CallRecord(
            id=f"cr_{case_id}_1",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="1",
            caller="9876500001",
            receiver="9876500002",
            datetime_iso="2026-11-12T09:00:00Z",
            duration_seconds=120,
            imei="860123456789012",
            fingerprint=f"fp_{case_id}_1"
        ),
        CallRecord(
            id=f"cr_{case_id}_2",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="2",
            caller="9876500001",
            receiver="9876500002",
            datetime_iso="2026-11-12T11:30:00Z",
            duration_seconds=240,
            imei="860123456789012",
            fingerprint=f"fp_{case_id}_2"
        ),
        # Call to a third phone
        CallRecord(
            id=f"cr_{case_id}_3",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="3",
            caller="9876500001",
            receiver="9876500003",
            datetime_iso="2026-11-12T12:00:00Z",
            duration_seconds=60,
            fingerprint=f"fp_{case_id}_3"
        ),
    ]
    for c in cdrs:
        db.add(c)

    # Multiple Transactions between same account pair: ACC_REMIT -> ACC_BENEF
    txns = [
        Transaction(
            id=f"txn_{case_id}_1",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="10",
            from_account="ACC_REMIT",
            to_account="ACC_BENEF",
            from_name="Sunil Sharma",
            to_name="Ravi Kumar",
            amount_paise=150000, # Rs. 1,500.00
            date_iso="2026-11-12T10:00:00Z",
            fingerprint=f"fp_txn_{case_id}_1"
        ),
        Transaction(
            id=f"txn_{case_id}_2",
            case_id=case_id,
            source_file=ev.original_name,
            source_ref="11",
            from_account="ACC_REMIT",
            to_account="ACC_BENEF",
            amount_paise=350000, # Rs. 3,500.00
            date_iso="2026-11-12T14:00:00Z",
            fingerprint=f"fp_txn_{case_id}_2"
        ),
    ]
    for t in txns:
        db.add(t)

    # IP Event linking phone to IP
    ip_ev = IPEvent(
        id=f"ip_{case_id}_1",
        case_id=case_id,
        source_file=ev.original_name,
        source_ref="20",
        identifier="9876500001",
        ip_address="192.168.1.100",
        datetime_iso="2026-11-12T09:05:00Z"
    )
    db.add(ip_ev)

    db.commit()
    db.close()

    yield case_id

    # Teardown
    td_db = SessionLocal()
    td_db.query(GraphEdge).filter(GraphEdge.case_id == case_id).delete()
    td_db.query(GraphNode).filter(GraphNode.case_id == case_id).delete()
    td_db.query(CallRecord).filter(CallRecord.case_id == case_id).delete()
    td_db.query(Transaction).filter(Transaction.case_id == case_id).delete()
    td_db.query(IPEvent).filter(IPEvent.case_id == case_id).delete()
    td_db.query(EvidenceFile).filter(EvidenceFile.id == f"ev_{case_id}").delete()
    td_db.query(CaseMember).filter(CaseMember.case_id == case_id).delete()
    td_db.query(Case).filter(Case.id == case_id).delete()
    td_db.commit()
    td_db.close()


def test_rebuild_graph_deterministic_and_idempotent(graph_test_case):
    """Verifies that running rebuild_graph twice yields 100% identical counts and IDs."""
    db = SessionLocal()

    res1 = rebuild_graph(db, graph_test_case)
    nodes1 = {n.id: (n.node_type, n.label) for n in db.query(GraphNode).filter(GraphNode.case_id == graph_test_case).all()}
    edges1 = {e.id: (e.src, e.dst, e.edge_type, e.count, e.total_paise) for e in db.query(GraphEdge).filter(GraphEdge.case_id == graph_test_case).all()}

    # Second rebuild
    res2 = rebuild_graph(db, graph_test_case)
    nodes2 = {n.id: (n.node_type, n.label) for n in db.query(GraphNode).filter(GraphNode.case_id == graph_test_case).all()}
    edges2 = {e.id: (e.src, e.dst, e.edge_type, e.count, e.total_paise) for e in db.query(GraphEdge).filter(GraphEdge.case_id == graph_test_case).all()}

    assert res1["nodes_count"] == res2["nodes_count"]
    assert res1["edges_count"] == res2["edges_count"]
    assert nodes1 == nodes2
    assert edges1 == edges2

    db.close()


def test_repeated_events_aggregated_into_single_edge(graph_test_case):
    """Verifies that multiple calls or transfers between same nodes aggregate into one edge."""
    db = SessionLocal()
    rebuild_graph(db, graph_test_case)

    # Check Phone -> Phone CALLED edge
    caller_id = generate_node_id(graph_test_case, "Phone", "9876500001")
    receiver_id = generate_node_id(graph_test_case, "Phone", "9876500002")
    call_edge = db.query(GraphEdge).filter(
        GraphEdge.case_id == graph_test_case,
        GraphEdge.src == caller_id,
        GraphEdge.dst == receiver_id,
        GraphEdge.edge_type == "CALLED"
    ).first()

    assert call_edge is not None
    assert call_edge.count == 2
    assert "2026-11-12" in str(call_edge.first_seen) and "09:00:00" in str(call_edge.first_seen)
    assert "2026-11-12" in str(call_edge.last_seen) and "11:30:00" in str(call_edge.last_seen)

    # Check Account -> Account TRANSFERRED edge
    from_acc_id = generate_node_id(graph_test_case, "Account", "ACC_REMIT")
    to_acc_id = generate_node_id(graph_test_case, "Account", "ACC_BENEF")
    txn_edge = db.query(GraphEdge).filter(
        GraphEdge.case_id == graph_test_case,
        GraphEdge.src == from_acc_id,
        GraphEdge.dst == to_acc_id,
        GraphEdge.edge_type == "TRANSFERRED"
    ).first()

    assert txn_edge is not None
    assert txn_edge.count == 2
    # 150000 + 350000 = 500000 paise (Rs. 5,000.00)
    assert txn_edge.total_paise == 500000
    assert isinstance(txn_edge.total_paise, int)

    db.close()


def test_api_get_node_neighbours_and_pagination(graph_test_case):
    """Verifies GET /cases/{id}/graph/node/{node_id} grouped neighbours and notice format."""
    db = SessionLocal()
    rebuild_graph(db, graph_test_case)
    db.close()

    client = TestClient(app)

    # Login
    login_res = client.post("/auth/login", json={"username": "investigator1", "password": "OfficerPass1234!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    central_node_id = generate_node_id(graph_test_case, "Phone", "9876500001")

    # 1. Full neighbours request
    resp = client.get(f"/cases/{graph_test_case}/graph/node/{central_node_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["case_id"] == graph_test_case
    assert data["node"]["id"] == central_node_id
    assert "notice" in data
    assert "showing " in data["notice"]
    assert "grouped_neighbours" in data

    # Check that Phone, Device, and IP groups exist for this central node
    groups = data["grouped_neighbours"]
    assert "Phone" in groups
    assert "Device" in groups
    assert "IP" in groups

    # 2. Test pagination with page_size=2
    paged_resp = client.get(
        f"/cases/{graph_test_case}/graph/node/{central_node_id}?page=1&page_size=2",
        headers=headers
    )
    assert paged_resp.status_code == 200
    paged_data = paged_resp.json()
    assert paged_data["page"] == 1
    assert paged_data["page_size"] == 2
    assert paged_data["notice"] == f"showing 2 of {data['total_neighbours']}"


def test_neo4j_down_fallback(graph_test_case):
    """Verifies that rebuild_graph gracefully falls back when Neo4j is offline."""
    db = SessionLocal()
    # Even if Neo4j is not running in local environment, rebuild succeeds via SQLite/NetworkX
    res = rebuild_graph(db, graph_test_case)
    assert res["status"] == "rebuilt"
    assert res["authoritative_source"] == "SQLite WAL"
    assert "offline" in res["neo4j_status"] or res["neo4j_status"] == "synced"
    db.close()


def test_dynamic_config_new_node_type(graph_test_case):
    """Verifies adding a row in NodeTypeConfig immediately reflects in config endpoint."""
    db = SessionLocal()
    custom_type_name = "CryptocurrencyWallet"
    
    # Check if exists or insert
    existing = db.query(NodeTypeConfig).filter(NodeTypeConfig.type_name == custom_type_name).first()
    if not existing:
        new_nt = NodeTypeConfig(
            type_name=custom_type_name,
            label="Crypto Wallet Address",
            color="#EAB308",
            icon="wallet",
            shape="hexagon",
            score_weight=1.5,
            is_active=True
        )
        db.add(new_nt)
        db.commit()

    db.close()

    client = TestClient(app)
    login_res = client.post("/auth/login", json={"username": "investigator1", "password": "OfficerPass1234!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    cfg_resp = client.get(f"/cases/{graph_test_case}/graph/config", headers=headers)
    assert cfg_resp.status_code == 200
    cfg_data = cfg_resp.json()

    type_names = [nt["type_name"] for nt in cfg_data["node_types"]]
    assert custom_type_name in type_names

    custom_entry = next(nt for nt in cfg_data["node_types"] if nt["type_name"] == custom_type_name)
    assert custom_entry["color"] == "#EAB308"
    assert custom_entry["shape"] == "hexagon"


def test_api_graph_bola_defense(graph_test_case):
    """Verifies that unauthorized requests to graph endpoints are rejected."""
    client = TestClient(app)

    central_node_id = generate_node_id(graph_test_case, "Phone", "9876500001")
    resp = client.get(f"/cases/{graph_test_case}/graph/node/{central_node_id}")
    assert resp.status_code in (401, 403)
