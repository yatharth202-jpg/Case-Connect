import json
import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, CaseMember, Entity, EntityLink,
    MatchSuggestion, ProfileMember, CallRecord
)
from backend.app.auth.security import hash_password
from backend.app.services.graph.builder import build_detail_graph
from backend.app.services.graph.projection import build_entity_projection

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

def create_case(token: str, title: str) -> str:
    res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": title, "priority": "high"})
    return res.json()["id"]


# ---------------------------------------------------------------------
# 1. Name variants of planted person -> HIGH suggestions
# ---------------------------------------------------------------------
def test_name_variants_produce_high_match_suggestions():
    inv_token = get_token("inv_matching_1", role="investigator")
    case_id = create_case(inv_token, "Planted Recruiter Matching Case")

    db = SessionLocal()
    phone_id = "9876543210"
    
    # 3 FIR variants of the same recruiter sharing a phone
    variants = ["Amit Sharma", "A. Sharma", "Amit Kumar Sharma"]
    ent_ids = []
    for idx, var in enumerate(variants):
        eid = f"rec_var_{idx}"
        ent_ids.append(eid)
        db.add(Entity(
            id=f"e_{case_id}_{eid}",
            case_id=case_id,
            label="Person",
            canonical_id=eid,
            display_name=var,
            source_file="FIR_001",
            source_ref=f"Page {idx+1}",
            method="ner",
            confidence=0.9
        ))
        db.add(EntityLink(
            id=f"el_{case_id}_{eid}",
            case_id=case_id,
            source_entity_id=eid,
            target_entity_id=phone_id,
            relationship_type="USES",
            source_file="FIR_001",
            source_ref=f"Page {idx+1}",
            method="structured",
            confidence=1.0
        ))
    db.commit()
    db.close()

    # Generate matches
    gen_res = client.post(
        f"/cases/{case_id}/matches/generate",
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert gen_res.status_code == 200
    assert gen_res.json()["new_suggestions"] >= 3

    # Query HIGH matches
    list_res = client.get(
        f"/cases/{case_id}/matches?level=HIGH",
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 3

    for item in items:
        assert item["level"] == "HIGH"
        assert item["status"] == "pending"
        assert item["score"] >= 90.0
        assert any("Shared mobile phone" in r for r in item["reasons"])


# ---------------------------------------------------------------------
# 2. Relatives sharing phone -> SHARED_DEVICE warning, never merge
# ---------------------------------------------------------------------
def test_relatives_sharing_phone_flags_shared_device():
    inv_token = get_token("inv_matching_2", role="investigator")
    case_id = create_case(inv_token, "Relatives Shared Phone Case")

    db = SessionLocal()
    phone_id = "9112233445"
    
    # Distinct relatives with same surname sharing a phone
    db.add(Entity(
        id=f"e_{case_id}_rel_a",
        case_id=case_id,
        label="Person",
        canonical_id="rel_a",
        display_name="Rohan Verma",
        source_file="SDR_Record",
        source_ref="Row 1",
        method="structured",
        confidence=1.0
    ))
    db.add(Entity(
        id=f"e_{case_id}_rel_b",
        case_id=case_id,
        label="Person",
        canonical_id="rel_b",
        display_name="Suman Verma",
        source_file="SDR_Record",
        source_ref="Row 2",
        method="structured",
        confidence=1.0
    ))
    db.add(EntityLink(
        id=f"el_{case_id}_rel_a",
        case_id=case_id,
        source_entity_id="rel_a",
        target_entity_id=phone_id,
        relationship_type="USES",
        source_file="SDR_Record",
        source_ref="Row 1",
        method="structured",
        confidence=1.0
    ))
    db.add(EntityLink(
        id=f"el_{case_id}_rel_b",
        case_id=case_id,
        source_entity_id="rel_b",
        target_entity_id=phone_id,
        relationship_type="USES",
        source_file="SDR_Record",
        source_ref="Row 2",
        method="structured",
        confidence=1.0
    ))
    db.commit()
    db.close()

    # Generate matches
    client.post(
        f"/cases/{case_id}/matches/generate",
        headers={"Authorization": f"Bearer {inv_token}"}
    )

    list_res = client.get(
        f"/cases/{case_id}/matches?level=SHARED_DEVICE",
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    match_item = items[0]
    assert match_item["level"] == "SHARED_DEVICE"
    assert any("merge prohibited" in r.lower() for r in match_item["reasons"])

    # Attempting to approve SHARED_DEVICE must fail with 400
    approve_res = client.post(
        f"/matches/{match_item['id']}/approve",
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    assert approve_res.status_code == 400


# ---------------------------------------------------------------------
# 3. Initial-only name ambiguous with >= 2 people -> MEDIUM, never HIGH
# ---------------------------------------------------------------------
def test_ambiguous_initial_is_not_high():
    inv_token = get_token("inv_matching_3", role="investigator")
    case_id = create_case(inv_token, "Ambiguous Initial Case")

    db = SessionLocal()
    phone_id = "9988776655"

    # Initial-only "R. Sharma" plus two different distinct persons "Rahul Sharma" & "Ramesh Sharma"
    persons_data = [
        ("amb_1", "R. Sharma"),
        ("amb_2", "Rahul Sharma"),
        ("amb_3", "Ramesh Sharma")
    ]
    for eid, name in persons_data:
        db.add(Entity(
            id=f"e_{case_id}_{eid}",
            case_id=case_id,
            label="Person",
            canonical_id=eid,
            display_name=name,
            source_file="Complaint",
            source_ref="Para 1",
            method="ner",
            confidence=0.8
        ))
        db.add(EntityLink(
            id=f"el_{case_id}_{eid}",
            case_id=case_id,
            source_entity_id=eid,
            target_entity_id=phone_id,
            relationship_type="USES",
            source_file="Complaint",
            source_ref="Para 1",
            method="structured",
            confidence=1.0
        ))
    db.commit()
    db.close()

    client.post(
        f"/cases/{case_id}/matches/generate",
        headers={"Authorization": f"Bearer {inv_token}"}
    )

    # Check that pair involving "R. Sharma" is flagged MEDIUM due to ambiguity
    matches_res = client.get(
        f"/cases/{case_id}/matches",
        headers={"Authorization": f"Bearer {inv_token}"}
    )
    items = matches_res.json()["items"]
    
    # Check that any match involving amb_1 ("R. Sharma") is never HIGH
    for it in items:
        if it["entity_a"]["id"] == "amb_1" or it["entity_b"]["id"] == "amb_1":
            assert it["level"] != "HIGH", f"Ambiguous initial match was unexpectedly HIGH: {it}"


# ---------------------------------------------------------------------
# 4. Approve then Undo: Restores Previous Graph Exactly
# ---------------------------------------------------------------------
def test_approve_then_undo_restores_entity_graph():
    inv_token = get_token("inv_matching_4", role="investigator")
    case_id = create_case(inv_token, "Approve and Undo Graph Test")

    db = SessionLocal()
    phone_a = "9000000001"
    phone_b = "9000000002"
    shared_acct = "100200300400"

    # Two persons sharing an account
    db.add(Entity(id=f"e_{case_id}_u1", case_id=case_id, label="Person", canonical_id="p_orig_1", display_name="Vikas Gupta", source_file="Doc", source_ref="1", method="ner", confidence=1.0))
    db.add(Entity(id=f"e_{case_id}_u2", case_id=case_id, label="Person", canonical_id="p_orig_2", display_name="V. Gupta", source_file="Doc", source_ref="2", method="ner", confidence=1.0))
    
    db.add(EntityLink(id=f"el_{case_id}_u1a", case_id=case_id, source_entity_id="p_orig_1", target_entity_id=phone_a, relationship_type="USES", source_file="Doc", source_ref="1", method="structured", confidence=1.0))
    db.add(EntityLink(id=f"el_{case_id}_u2a", case_id=case_id, source_entity_id="p_orig_2", target_entity_id=phone_b, relationship_type="USES", source_file="Doc", source_ref="2", method="structured", confidence=1.0))
    db.add(EntityLink(id=f"el_{case_id}_u1b", case_id=case_id, source_entity_id="p_orig_1", target_entity_id=shared_acct, relationship_type="OWNS", source_file="Doc", source_ref="1", method="structured", confidence=1.0))
    db.add(EntityLink(id=f"el_{case_id}_u2b", case_id=case_id, source_entity_id="p_orig_2", target_entity_id=shared_acct, relationship_type="OWNS", source_file="Doc", source_ref="2", method="structured", confidence=1.0))

    # Add call between phone_a and external phone
    db.add(CallRecord(
        id=f"c_undo_{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        source_file="CDR_Doc",
        source_ref="Row 1",
        caller=phone_a,
        receiver="9999999999",
        datetime_iso="2026-08-01T10:00:00",
        duration_seconds=60,
        imei="",
        fingerprint=f"fp_{uuid.uuid4().hex[:8]}"
    ))
    db.commit()

    # Step A: Baseline graph counts before merge
    detail_pre = build_detail_graph(db, case_id)
    proj_pre = build_entity_projection(detail_pre)
    nodes_pre = set(proj_pre.nodes())
    edges_pre = len(proj_pre.edges())
    db.close()

    # Step B: Generate and approve match
    client.post(f"/cases/{case_id}/matches/generate", headers={"Authorization": f"Bearer {inv_token}"})
    list_res = client.get(f"/cases/{case_id}/matches?level=HIGH", headers={"Authorization": f"Bearer {inv_token}"})
    match_id = list_res.json()["items"][0]["id"]

    app_res = client.post(f"/matches/{match_id}/approve", headers={"Authorization": f"Bearer {inv_token}"})
    assert app_res.status_code == 200
    profile_id = app_res.json()["profile_id"]

    # Verify MasterProfile exists and is returned by /profiles API
    prof_list = client.get(f"/cases/{case_id}/profiles", headers={"Authorization": f"Bearer {inv_token}"}).json()
    assert any(p["profile_id"] == profile_id for p in prof_list)

    # Verify detail profile API
    prof_detail = client.get(f"/cases/{case_id}/profiles/{profile_id}", headers={"Authorization": f"Bearer {inv_token}"}).json()
    assert prof_detail["profile_id"] == profile_id
    assert len(prof_detail["members"]) == 2

    # Step C: Rebuild graph after merge -> projection has MasterProfile node instead of separate persons
    db = SessionLocal()
    detail_post = build_detail_graph(db, case_id)
    proj_post = build_entity_projection(detail_post)
    mp_key = f"{case_id}|MasterProfile|{profile_id}"
    assert mp_key in proj_post.nodes()
    db.close()

    # Step D: Undo match
    undo_res = client.post(f"/matches/{match_id}/undo", headers={"Authorization": f"Bearer {inv_token}"})
    assert undo_res.status_code == 200
    assert undo_res.json()["status"] == "undone"

    # Step E: Rebuild graph after undo -> exact previous graph restored
    db = SessionLocal()
    detail_undone = build_detail_graph(db, case_id)
    proj_undone = build_entity_projection(detail_undone)
    nodes_undone = set(proj_undone.nodes())
    edges_undone = len(proj_undone.edges())
    db.close()

    assert nodes_undone == nodes_pre, f"Nodes differed: {nodes_undone} vs {nodes_pre}"
    assert edges_undone == edges_pre, f"Edge count differed: {edges_undone} vs {edges_pre}"


# ---------------------------------------------------------------------
# 5. Authorization & Non-Member 403 Enforcement
# ---------------------------------------------------------------------
def test_matching_authorization_and_cross_case_isolation():
    inv_token = get_token("inv_owner_match", role="investigator")
    other_token = get_token("inv_other_match", role="investigator")
    viewer_token = get_token("viewer_match", role="viewer")

    case_id = create_case(inv_token, "Auth Matching Case")

    # Viewer cannot generate or approve matches (403)
    gen_viewer = client.post(
        f"/cases/{case_id}/matches/generate",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert gen_viewer.status_code == 403

    # Non-member cannot view matches (403)
    list_non_member = client.get(
        f"/cases/{case_id}/matches",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert list_non_member.status_code == 403
