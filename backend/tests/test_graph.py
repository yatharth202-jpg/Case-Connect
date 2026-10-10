import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, CaseMember, EvidenceFile,
    CallRecord, Transaction, Entity, EntityLink
)
from backend.app.auth.security import hash_password
from backend.app.services.graph.builder import (
    build_detail_graph, invalidate_case_graph
)
from backend.app.services.graph.projection import (
    build_entity_projection, expand_hops_subgraph, find_shortest_path_nodes
)

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

def create_case_for_user(token: str, title: str) -> str:
    res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": title, "priority": "high"})
    return res.json()["id"]

# ---------------------------------------------------------------------
# 1. Ring Scenario: 2-hop traversal reaches organizer (unlinked to FIR)
# ---------------------------------------------------------------------
def test_ring_scenario_two_hop_reaches_organizer():
    token = get_token("analyst_graph1")
    case_id = create_case_for_user(token, "Ring Test Case")

    db = SessionLocal()
    # Setup Ring:
    # Mule Raj (in FIR) -> Manager Anand (hop 1) -> Organizer Boss (hop 2, unlinked to FIR)
    mule_phone = "9811000001"
    mgr_phone = "9811000002"
    org_phone = "9811000003"

    # Entities
    db.add(Entity(case_id=case_id, label="Person", canonical_id="mule raj", display_name="Mule Raj", properties_json="{}", source_file="fir.pdf", source_ref="1"))
    db.add(Entity(case_id=case_id, label="Person", canonical_id="mgr anand", display_name="Mgr Anand", properties_json="{}", source_file="intel.csv", source_ref="2"))
    db.add(Entity(case_id=case_id, label="Person", canonical_id="organizer boss", display_name="Organizer Boss", properties_json="{}", source_file="cdr_dump.csv", source_ref="3"))

    # Entity ownership links
    db.add(EntityLink(case_id=case_id, source_entity_id="mule raj", target_entity_id=mule_phone, relationship_type="USES", properties_json="{}", source_file="sim.csv", source_ref="1", method="officer"))
    db.add(EntityLink(case_id=case_id, source_entity_id="mgr anand", target_entity_id=mgr_phone, relationship_type="USES", properties_json="{}", source_file="sim.csv", source_ref="2", method="officer"))
    db.add(EntityLink(case_id=case_id, source_entity_id="organizer boss", target_entity_id=org_phone, relationship_type="USES", properties_json="{}", source_file="sim.csv", source_ref="3", method="officer"))

    # Call Records: Mule calls Mgr, Mgr calls Org
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="1", caller=mule_phone, receiver=mgr_phone, call_date="2024-01-01", duration_seconds=120, fingerprint=f"fp1_{case_id}"))
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="2", caller=mgr_phone, receiver=org_phone, call_date="2024-01-02", duration_seconds=180, fingerprint=f"fp2_{case_id}"))
    db.commit()
    db.close()

    invalidate_case_graph(case_id)

    # 1 Hop from Mule: Should find Mule and Manager, NOT Organizer
    res1 = client.get(f"/cases/{case_id}/graph/search?q=mule raj&hops=1&view=entity", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    data1 = res1.json()
    node_names_1 = [n.get("name") for n in data1["nodes"]]
    assert "Mule Raj" in node_names_1
    assert "Mgr Anand" in node_names_1
    assert "Organizer Boss" not in node_names_1

    # 2 Hops from Mule: Traversal MUST reach Organizer Boss
    res2 = client.get(f"/cases/{case_id}/graph/search?q=mule raj&hops=2&view=entity", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    data2 = res2.json()
    node_names_2 = [n.get("name") for n in data2["nodes"]]
    assert "Mule Raj" in node_names_2
    assert "Mgr Anand" in node_names_2
    assert "Organizer Boss" in node_names_2

    # Verify Organizer Boss has no FIR source file
    org_node = next(n for n in data2["nodes"] if n.get("name") == "Organizer Boss")
    assert org_node.get("source_file") != "fir.pdf"

# ---------------------------------------------------------------------
# 2. CDR-only graph building without crash
# ---------------------------------------------------------------------
def test_cdr_only_graph_builds_without_crash():
    token = get_token("analyst_graph2")
    case_id = create_case_for_user(token, "CDR Only Case")

    db = SessionLocal()
    # Raw calls with no entities or officer links
    db.add(CallRecord(case_id=case_id, source_file="cdr_raw.csv", source_ref="1", caller="9999000001", receiver="9999000002", call_date="2024-02-01", duration_seconds=60, fingerprint=f"cdr_fp1_{case_id}"))
    db.add(CallRecord(case_id=case_id, source_file="cdr_raw.csv", source_ref="2", caller="9999000002", receiver="9999000003", call_date="2024-02-01", duration_seconds=90, fingerprint=f"cdr_fp2_{case_id}"))
    db.commit()
    db.close()

    invalidate_case_graph(case_id)

    # Detail View Search
    res_det = client.get(f"/cases/{case_id}/graph/search?hops=2&view=detail", headers={"Authorization": f"Bearer {token}"})
    assert res_det.status_code == 200
    det_data = res_det.json()
    assert len(det_data["nodes"]) == 3
    assert len(det_data["edges"]) == 2

    # Entity View Search (phones remain self-standing uncollapsed entity nodes)
    res_ent = client.get(f"/cases/{case_id}/graph/search?hops=2&view=entity", headers={"Authorization": f"Bearer {token}"})
    assert res_ent.status_code == 200
    ent_data = res_ent.json()
    assert len(ent_data["nodes"]) == 3
    assert len(ent_data["edges"]) == 2

# ---------------------------------------------------------------------
# 3. Graph rebuild idempotence & case isolation
# ---------------------------------------------------------------------
def test_graph_rebuild_idempotence_and_case_isolation():
    token = get_token("analyst_iso1")
    case_a = create_case_for_user(token, "Isolation Case A")
    case_b = create_case_for_user(token, "Isolation Case B")

    db = SessionLocal()
    # Add entity in Case A
    db.add(Entity(case_id=case_a, label="Person", canonical_id="secret agent a", display_name="Agent A", properties_json="{}", source_file="f.csv", source_ref="1"))
    # Add entity in Case B
    db.add(Entity(case_id=case_b, label="Person", canonical_id="secret agent b", display_name="Agent B", properties_json="{}", source_file="f.csv", source_ref="1"))
    db.commit()
    db.close()

    # Rebuild Case A
    res_reb1 = client.post(f"/cases/{case_a}/graph/rebuild", headers={"Authorization": f"Bearer {token}"})
    assert res_reb1.status_code == 200
    data_reb1 = res_reb1.json()
    assert data_reb1["status"] == "rebuilt"
    assert data_reb1["case_id"] == case_a

    # Idempotent rebuild Case A
    res_reb2 = client.post(f"/cases/{case_a}/graph/rebuild", headers={"Authorization": f"Bearer {token}"})
    assert res_reb2.status_code == 200
    data_reb2 = res_reb2.json()
    assert data_reb2["entity_nodes"] == data_reb1["entity_nodes"]

    # Verify Case Isolation: Querying Case A never leaks Agent B
    res_search_a = client.get(f"/cases/{case_a}/graph/search?q=secret&hops=2&view=entity", headers={"Authorization": f"Bearer {token}"})
    assert res_search_a.status_code == 200
    names_a = [n.get("name") for n in res_search_a.json()["nodes"]]
    assert "Agent A" in names_a
    assert "Agent B" not in names_a

# ---------------------------------------------------------------------
# 4. Shared-phone relatives marked shared=True
# ---------------------------------------------------------------------
def test_shared_phone_relatives_marked_shared_true():
    token = get_token("analyst_shared")
    case_id = create_case_for_user(token, "Shared Phone Case")
    shared_mobile = "9822334455"

    db = SessionLocal()
    # Relative 1 & Relative 2
    db.add(Entity(case_id=case_id, label="Person", canonical_id="brother ramesh", display_name="Brother Ramesh", properties_json="{}", source_file="doc.csv", source_ref="1"))
    db.add(Entity(case_id=case_id, label="Person", canonical_id="sister priya", display_name="Sister Priya", properties_json="{}", source_file="doc.csv", source_ref="2"))

    # Both relatives link to the same mobile number
    db.add(EntityLink(case_id=case_id, source_entity_id="brother ramesh", target_entity_id=shared_mobile, relationship_type="USES", properties_json="{}", source_file="telco.csv", source_ref="1", method="officer"))
    db.add(EntityLink(case_id=case_id, source_entity_id="sister priya", target_entity_id=shared_mobile, relationship_type="USES", properties_json="{}", source_file="telco.csv", source_ref="2", method="officer"))
    db.commit()
    db.close()

    invalidate_case_graph(case_id)

    # In detail graph: Phone node must have shared=True
    res_det = client.get(f"/cases/{case_id}/graph/search?q={shared_mobile}&hops=1&view=detail", headers={"Authorization": f"Bearer {token}"})
    assert res_det.status_code == 200
    phone_node = next(n for n in res_det.json()["nodes"] if n.get("id") == shared_mobile)
    assert phone_node.get("shared") is True

    # In entity graph: The shared phone is NOT collapsed into either person; it remains its own shared node
    res_ent = client.get(f"/cases/{case_id}/graph/search?q={shared_mobile}&hops=1&view=entity", headers={"Authorization": f"Bearer {token}"})
    assert res_ent.status_code == 200
    ent_nodes = res_ent.json()["nodes"]
    shared_ent = next(n for n in ent_nodes if n.get("id") == shared_mobile)
    assert shared_ent.get("shared") is True
    ent_names = [n.get("name") for n in ent_nodes]
    assert "Brother Ramesh" in ent_names
    assert "Sister Priya" in ent_names

# ---------------------------------------------------------------------
# 5. Shortest path calculation
# ---------------------------------------------------------------------
def test_shortest_path_calculation():
    token = get_token("analyst_path")
    case_id = create_case_for_user(token, "Path Finding Case")

    db = SessionLocal()
    # A -> B -> C -> D
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="1", caller="9700000001", receiver="9700000002", call_date="2024-03-01", duration_seconds=50, fingerprint=f"pfp1_{case_id}"))
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="2", caller="9700000002", receiver="9700000003", call_date="2024-03-01", duration_seconds=50, fingerprint=f"pfp2_{case_id}"))
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="3", caller="9700000003", receiver="9700000004", call_date="2024-03-01", duration_seconds=50, fingerprint=f"pfp3_{case_id}"))
    # Isolated node E
    db.add(CallRecord(case_id=case_id, source_file="cdr.csv", source_ref="4", caller="9700000009", receiver="9700000009", call_date="2024-03-01", duration_seconds=10, fingerprint=f"pfp4_{case_id}"))
    db.commit()
    db.close()

    invalidate_case_graph(case_id)

    from_key = f"{case_id}|Phone|9700000001"
    to_key = f"{case_id}|Phone|9700000004"
    iso_key = f"{case_id}|Phone|9700000009"

    # Connected path
    res_path = client.get(
        f"/cases/{case_id}/graph/path?from_key={from_key}&to_key={to_key}&view=entity",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_path.status_code == 200
    path_data = res_path.json()
    assert path_data["found"] is True
    assert path_data["length"] == 3
    assert len(path_data["path_nodes"]) == 4

    # Disconnected path
    res_nopath = client.get(
        f"/cases/{case_id}/graph/path?from_key={from_key}&to_key={iso_key}&view=entity",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_nopath.status_code == 200
    assert res_nopath.json()["found"] is False

# ---------------------------------------------------------------------
# 6. Officer link creation and deletion
# ---------------------------------------------------------------------
def test_officer_link_lifecycle():
    token = get_token("analyst_link")
    case_id = create_case_for_user(token, "Officer Link Case")
    target_phone = "9655443322"

    db = SessionLocal()
    db.add(Entity(case_id=case_id, label="Person", canonical_id="target suspect", display_name="Target Person", properties_json="{}", source_file="manual.csv", source_ref="1"))
    db.commit()
    db.close()

    # 1. Create Link
    create_payload = {
        "source_entity_id": "target suspect",
        "target_entity_id": target_phone,
        "link_type": "USES"
    }
    res_create = client.post(f"/cases/{case_id}/links", json=create_payload, headers={"Authorization": f"Bearer {token}"})
    assert res_create.status_code == 200
    link_id = res_create.json()["link_id"]
    assert link_id is not None

    # Verify link shows up in graph
    res_search = client.get(f"/cases/{case_id}/graph/search?q=target suspect&hops=1&view=detail", headers={"Authorization": f"Bearer {token}"})
    assert res_search.status_code == 200
    node_ids = [n.get("id") for n in res_search.json()["nodes"]]
    assert target_phone in node_ids

    # 2. Delete Link
    res_del = client.delete(f"/cases/{case_id}/links/{link_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"

    # Verify link is removed from graph
    res_search_after = client.get(f"/cases/{case_id}/graph/search?q=target suspect&hops=1&view=detail", headers={"Authorization": f"Bearer {token}"})
    assert res_search_after.status_code == 200
    node_ids_after = [n.get("id") for n in res_search_after.json()["nodes"]]
    assert target_phone not in node_ids_after
