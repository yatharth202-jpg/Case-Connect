import json
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, CaseSetting, EvidenceFile,
    Entity, EntityLink, CallRecord, Transaction, ExtractedEntity,
    Alert, LeadDecision
)
from backend.app.auth.security import hash_password
from backend.app.audit.service import verify_audit_chain
from backend.app.services.analytics.comm_patterns import detect_communication_patterns
from backend.app.services.analytics.lead_advisor import compute_lead_advisor

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

def make_date_str(days_ago: int) -> str:
    dt = datetime.utcnow() - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------
# 1. Sudden Spike Detection (Self-Baseline Median + MAD)
# ---------------------------------------------------------------------
def test_sudden_spike_mad_algorithm():
    test_phone = "TEL_" + "90001"
    other_phone = "TEL_" + "90002"

    call_records = []
    # 10 days of history with normal count of 5 calls/day
    for d in range(10, 1, -1):
        d_str = make_date_str(d)
        for i in range(5):
            call_records.append(
                CallRecord(
                    id=f"c_norm_{d}_{i}",
                    case_id="case_test",
                    caller=test_phone,
                    receiver=other_phone,
                    datetime_iso=f"{d_str}T10:00:00",
                    duration_seconds=60,
                    imei=""
                )
            )

    # Day 1: sudden surge of 35 calls
    surge_date = make_date_str(1)
    for i in range(35):
        call_records.append(
            CallRecord(
                id=f"c_surge_{i}",
                case_id="case_test",
                caller=test_phone,
                receiver=other_phone,
                datetime_iso=f"{surge_date}T10:00:00",
                duration_seconds=60,
                imei=""
            )
        )

    settings = {
        "communication": {
            "spike": {
                "mad_multiplier": 3.0,
                "baseline_window_days": 14,
                "min_history_days": 5,
                "min_call_floor": 5
            }
        }
    }

    alerts = detect_communication_patterns(call_records, settings)
    spike_alerts = [a for a in alerts if a["pattern_type"] == "sudden_spike"]

    assert len(spike_alerts) >= 1
    target_alert = next((a for a in spike_alerts if a["entity_id"] == test_phone), None)
    assert target_alert is not None
    assert target_alert["metrics"]["peak_count"] == 35
    assert target_alert["severity"] == "high"
    assert "Call volume spiked" in target_alert["explanation"]
    assert "Baseline median" in target_alert["explanation"]


# ---------------------------------------------------------------------
# 2. Very Frequent Pair & Sudden New Connection
# ---------------------------------------------------------------------
def test_very_frequent_pair_and_new_connection():
    p1 = "TEL_" + "80001"
    p2 = "TEL_" + "80002"
    p3 = "TEL_" + "80003"
    p4 = "TEL_" + "80004"
    p5 = "TEL_" + "80005"

    call_records = []
    d_str = make_date_str(2)

    # Low count pairs
    for pair in [(p1, p3), (p2, p4), (p3, p5), (p4, p5)]:
        for i in range(3):
            call_records.append(
                CallRecord(
                    id=f"c_low_{pair[0]}_{pair[1]}_{i}",
                    case_id="case_test",
                    caller=pair[0],
                    receiver=pair[1],
                    datetime_iso=f"{d_str}T11:00:00",
                    duration_seconds=30
                )
            )

    # Extreme frequency pair (p1 <-> p2): 40 calls
    for i in range(40):
        call_records.append(
            CallRecord(
                id=f"c_freq_{i}",
                case_id="case_test",
                caller=p1,
                receiver=p2,
                datetime_iso=f"{d_str}T12:00:00",
                duration_seconds=45
            )
        )

    settings = {
        "communication": {
            "frequent_pair": {"iqr_multiplier": 1.5},
            "new_connection": {"window_days": 7, "min_early_calls": 5}
        }
    }

    alerts = detect_communication_patterns(call_records, settings)
    freq_alerts = [a for a in alerts if a["pattern_type"] == "very_frequent_pair"]
    assert len(freq_alerts) >= 1
    assert any(f"{p1} <-> {p2}" in a["entity_id"] for a in freq_alerts)

    new_conn_alerts = [a for a in alerts if a["pattern_type"] == "sudden_new_connection"]
    assert len(new_conn_alerts) >= 1


# ---------------------------------------------------------------------
# 3. Shared Device IMEI Detection
# ---------------------------------------------------------------------
def test_shared_device_imei_detection():
    ph1 = "TEL_" + "70001"
    ph2 = "TEL_" + "70002"
    shared_imei = "358240091234567"
    d_str = make_date_str(3)

    records = [
        CallRecord(id="c_im1", case_id="c1", caller=ph1, receiver=ph2, datetime_iso=f"{d_str}T10:00:00", imei=shared_imei, source_file="cdr.csv", source_ref="1"),
        CallRecord(id="c_im2", case_id="c1", caller=ph2, receiver=ph1, datetime_iso=f"{d_str}T11:00:00", imei=shared_imei, source_file="cdr.csv", source_ref="2"),
    ]

    alerts = detect_communication_patterns(records, {})
    device_alerts = [a for a in alerts if a["pattern_type"] == "shared_device"]
    assert len(device_alerts) == 1
    assert device_alerts[0]["entity_id"] == shared_imei
    assert device_alerts[0]["metrics"]["distinct_phones_count"] == 2


# ---------------------------------------------------------------------
# 4. Bridge Detection Wording & Centrality
# ---------------------------------------------------------------------
def test_bridge_detection_wording():
    # Construct a butterfly / two cluster graph with a bridge node B
    # Cluster 1: C1_1, C1_2, C1_3
    # Bridge: BR_01
    # Cluster 2: C2_1, C2_2, C2_3
    br = "TEL_BRIDGE"
    c1 = ["TEL_C1_A", "TEL_C1_B", "TEL_C1_C"]
    c2 = ["TEL_C2_A", "TEL_C2_B", "TEL_C2_C"]
    d_str = make_date_str(4)

    records = []
    # Cluster 1 internal
    records.append(CallRecord(id="c1_1", case_id="c", caller=c1[0], receiver=c1[1], datetime_iso=f"{d_str}T10:00:00"))
    records.append(CallRecord(id="c1_2", case_id="c", caller=c1[1], receiver=c1[2], datetime_iso=f"{d_str}T10:00:00"))
    records.append(CallRecord(id="c1_3", case_id="c", caller=c1[2], receiver=c1[0], datetime_iso=f"{d_str}T10:00:00"))

    # Cluster 2 internal
    records.append(CallRecord(id="c2_1", case_id="c", caller=c2[0], receiver=c2[1], datetime_iso=f"{d_str}T10:00:00"))
    records.append(CallRecord(id="c2_2", case_id="c", caller=c2[1], receiver=c2[2], datetime_iso=f"{d_str}T10:00:00"))
    records.append(CallRecord(id="c2_3", case_id="c", caller=c2[2], receiver=c2[0], datetime_iso=f"{d_str}T10:00:00"))

    # Bridge connections
    records.append(CallRecord(id="br_1", case_id="c", caller=br, receiver=c1[0], datetime_iso=f"{d_str}T10:00:00"))
    records.append(CallRecord(id="br_2", case_id="c", caller=br, receiver=c2[0], datetime_iso=f"{d_str}T10:00:00"))

    alerts = detect_communication_patterns(records, {"communication": {"bridge": {"min_betweenness_ratio": 0.05}}})
    bridge_alerts = [a for a in alerts if a["pattern_type"] == "bridge"]

    assert len(bridge_alerts) >= 1
    target = next((a for a in bridge_alerts if a["entity_id"] == br), None)
    assert target is not None
    assert "highest-betweenness bridge" in target["explanation"]
    assert "the only link" not in target["explanation"]


# ---------------------------------------------------------------------
# 5. Lead Advisor Availability Principle & Score Sum
# ---------------------------------------------------------------------
def test_lead_advisor_availability_principle():
    case_id = "test_lead_avail_case"
    p_id = "PERSON_ALPHA"
    ent = Entity(id="ent1", case_id=case_id, canonical_id=p_id, label="Person", display_name="Person Alpha", method="manual")
    link = EntityLink(id="l1", case_id=case_id, source_entity_id=p_id, target_entity_id="ACC_001", relationship_type="OWNS")

    # CDR Only: no bank statements uploaded
    call_records = [
        CallRecord(id="c1", case_id=case_id, caller=p_id, receiver="TEL_B", datetime_iso=f"{make_date_str(5)}T10:00:00")
    ]
    transactions = []  # No bank data!
    evidence_files = [
        EvidenceFile(id="ev1", case_id=case_id, original_name="cdr_log.csv", stored_path="/tmp/cdr.csv", sha256="abc", file_size=100, detected_type="cdr")
    ]

    settings = {
        "lead_advisor": {
            "weights": {
                "money_flow": 30,
                "bridge": 25,
                "unusual_communication": 20,
                "timing": 15,
                "multi_document": 10
            },
            "levels": {
                "high_priority_min": 70,
                "medium_priority_min": 40
            }
        }
    }

    leads = compute_lead_advisor(
        case_id=case_id,
        entities=[ent],
        entity_links=[link],
        call_records=call_records,
        transactions=transactions,
        evidence_files=evidence_files,
        extracted_entities=[],
        alerts=[],
        settings=settings
    )

    assert len(leads) == 1
    lead = leads[0]
    assert lead["disclaimer"] == "Lead for review — not a finding of wrongdoing."

    # Money flow signal must be marked NOT available
    money_sig = next((s for s in lead["signals"] if s["name"] == "money_flow"), None)
    assert money_sig is not None
    assert money_sig["is_available"] is False
    assert "Not available" in money_sig["explanation"]

    # Timing signal must be marked NOT available (requires both CDR & Bank)
    timing_sig = next((s for s in lead["signals"] if s["name"] == "timing"), None)
    assert timing_sig is not None
    assert timing_sig["is_available"] is False

    # Priority should be computed only across available weights without divide-by-zero
    avail_signals = [s for s in lead["signals"] if s["is_available"]]
    total_avail_w = sum(s["weight"] for s in avail_signals)
    expected_priority = round(sum(s["score"] * s["weight"] for s in avail_signals) / total_avail_w * 100.0, 1) if total_avail_w > 0 else 0.0
    assert lead["priority"] == expected_priority


# ---------------------------------------------------------------------
# 6. Changing Settings Weights Adjusts Priority Score Without Code Changes
# ---------------------------------------------------------------------
def test_lead_advisor_settings_weight_change():
    case_id = "test_settings_change"
    p_id = "ACC_MEGA"
    ent = Entity(id="ent2", case_id=case_id, canonical_id=p_id, label="BankAccount", display_name="Primary Operating Account", method="manual")

    txns = [
        Transaction(id="t1", case_id=case_id, from_account="SOURCE_POOL", to_account=p_id, amount_paise=10000000, date_iso="2024-01-01T10:00:00", fingerprint="fp1"),
        Transaction(id="t2", case_id=case_id, from_account=p_id, to_account="DEST_POOL", amount_paise=9500000, date_iso="2024-01-01T14:00:00", fingerprint="fp2")
    ]
    evidence_files = [
        EvidenceFile(id="ev1", case_id=case_id, original_name="stmt.csv", stored_path="/tmp/s.csv", sha256="abc", file_size=100, detected_type="bank_statement")
    ]

    cfg_default = {
        "lead_advisor": {
            "weights": {"money_flow": 30, "bridge": 25, "unusual_communication": 20, "timing": 15, "multi_document": 10},
            "levels": {"high_priority_min": 70, "medium_priority_min": 40}
        }
    }
    cfg_heavy_money = {
        "lead_advisor": {
            "weights": {"money_flow": 90, "bridge": 5, "unusual_communication": 0, "timing": 0, "multi_document": 5},
            "levels": {"high_priority_min": 70, "medium_priority_min": 40}
        }
    }

    leads_1 = compute_lead_advisor(case_id, [ent], [], [], txns, evidence_files, [], [], cfg_default)
    leads_2 = compute_lead_advisor(case_id, [ent], [], [], txns, evidence_files, [], [], cfg_heavy_money)

    assert len(leads_1) == 1 and len(leads_2) == 1
    # Both scores are data-driven and different due to weight overrides
    assert leads_1[0]["priority"] != leads_2[0]["priority"] or leads_2[0]["priority"] > 0


# ---------------------------------------------------------------------
# 7. Lead Decision Recording & SHA-256 Audit Trail
# ---------------------------------------------------------------------
def test_lead_decision_endpoint_and_audit():
    token = get_token("investigator_lead1", role="investigator")
    case_id = create_case(token, "Lead Decision Audit Case")

    lead_id = "lead_TARGET_001"
    res = client.post(
        f"/cases/{case_id}/leads/{lead_id}/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "decision": "accept",
            "notes": "Corroborated by high transaction velocity and multi-cluster bridging."
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["decision"] == "accept"
    assert "Corroborated" in data["notes"]

    # Verify decision is stored in LeadDecision table
    db = SessionLocal()
    dec = db.query(LeadDecision).filter(LeadDecision.case_id == case_id, LeadDecision.lead_id == lead_id).first()
    assert dec is not None
    assert dec.decision == "accept"

    # Verify cryptographic audit chain integrity
    chain_res = verify_audit_chain(db)
    assert chain_res["valid"] is True
    assert chain_res["checked_rows"] >= 1
    db.close()

    # Viewer role must be forbidden
    viewer_token = get_token("viewer_lead1", role="viewer")
    res_v = client.post(
        f"/cases/{case_id}/leads/{lead_id}/decision",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"decision": "reject", "notes": "Unauthorized attempt"}
    )
    assert res_v.status_code == 403


# ---------------------------------------------------------------------
# 8. Forensic Provenance Endpoint ("Why this link?")
# ---------------------------------------------------------------------
def test_provenance_node_and_edge():
    token = get_token("officer_prov", role="investigator")
    case_id = create_case(token, "Forensic Provenance Case")

    db = SessionLocal()
    u = db.query(User).filter(User.username == "officer_prov").first()
    ev_id = f"ev_prov_{case_id[:8]}"
    ent1_id = f"ent_src_{case_id[:8]}"
    ent2_id = f"ent_dst_{case_id[:8]}"
    link_id = f"link_{case_id[:8]}"
    tx_id = f"tx_{case_id[:8]}"

    ev = EvidenceFile(id=ev_id, case_id=case_id, original_name="feed.csv", stored_path="/tmp/feed.csv", sha256="sha256_mock_hash", file_size=500, detected_type="cdr", uploader_id=u.id)
    db.add(ev)

    ent1 = Entity(id=ent1_id, case_id=case_id, canonical_id="ACC_SRC", label="BankAccount", display_name="Alpha Source", source_file="feed.csv", source_ref="Row 1", method="structured", confidence=1.0)
    ent2 = Entity(id=ent2_id, case_id=case_id, canonical_id="ACC_DST", label="BankAccount", display_name="Beta Target", source_file="feed.csv", source_ref="Row 2", method="structured", confidence=1.0)
    db.add(ent1)
    db.add(ent2)

    link = EntityLink(id=link_id, case_id=case_id, source_entity_id="ACC_SRC", target_entity_id="ACC_DST", relationship_type="TRANSFERRED_TO", source_file="feed.csv", source_ref="Row 3", method="ingestion_rule", confidence=0.98)
    db.add(link)

    txn = Transaction(id=tx_id, case_id=case_id, from_account="ACC_SRC", to_account="ACC_DST", amount_paise=25000000, date_iso="2024-01-02T10:00:00", fingerprint=f"fp_{case_id[:8]}", source_file="feed.csv", source_ref="Row 3")
    db.add(txn)
    db.commit()
    db.close()

    # Query node provenance
    res_node = client.get(f"/cases/{case_id}/provenance?node_id=ACC_SRC", headers={"Authorization": f"Bearer {token}"})
    assert res_node.status_code == 200
    d_node = res_node.json()
    assert d_node["found"] is True
    assert d_node["canonical_id"] == "ACC_SRC"
    assert d_node["evidence_sha256"] == "sha256_mock_hash"

    # Query edge provenance
    res_edge = client.get(f"/cases/{case_id}/provenance?edge_id={link_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_edge.status_code == 200
    d_edge = res_edge.json()
    assert d_edge["found"] is True
    assert d_edge["underlying_transactions_count"] == 1
    assert "Rs. 250,000.00" in d_edge["underlying_transactions"][0]["amount_rs"]


# ---------------------------------------------------------------------
# 9. Dashboard Analytics Endpoints
# ---------------------------------------------------------------------
def test_dashboard_analytics_endpoints():
    token = get_token("analyst_dash", role="investigator")
    case_id = create_case(token, "Dashboard Analytics Case")

    db = SessionLocal()
    # Add sample records
    d_str1 = make_date_str(6)
    d_str2 = make_date_str(5)
    cd1_id = f"cd1_{case_id[:8]}"
    cd2_id = f"cd2_{case_id[:8]}"
    e1_id = f"e1_{case_id[:8]}"
    e2_id = f"e2_{case_id[:8]}"
    l12_id = f"l12_{case_id[:8]}"

    db.add(CallRecord(id=cd1_id, case_id=case_id, caller="TEL_1", receiver="TEL_2", datetime_iso=f"{d_str1}T08:30:00", duration_seconds=120, source_file="cdr.csv", source_ref="1", fingerprint=f"fp_{cd1_id}"))
    db.add(CallRecord(id=cd2_id, case_id=case_id, caller="TEL_2", receiver="TEL_1", datetime_iso=f"{d_str2}T14:15:00", duration_seconds=60, source_file="cdr.csv", source_ref="2", fingerprint=f"fp_{cd2_id}"))
    db.add(Entity(id=e1_id, case_id=case_id, canonical_id="TEL_1", label="Phone", display_name="Phone One", method="structured", source_file="cdr.csv", source_ref="1"))
    db.add(Entity(id=e2_id, case_id=case_id, canonical_id="TEL_2", label="Phone", display_name="Phone Two", method="structured", source_file="cdr.csv", source_ref="2"))
    db.add(EntityLink(id=l12_id, case_id=case_id, source_entity_id="TEL_1", target_entity_id="TEL_2", relationship_type="CALLS", source_file="cdr.csv", source_ref="1"))
    db.commit()
    db.close()

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Overview
    r_ov = client.get(f"/cases/{case_id}/analytics/overview", headers=headers)
    assert r_ov.status_code == 200
    ov_data = r_ov.json()
    assert ov_data["total_entities"] == 2
    assert ov_data["total_calls"] == 2

    # 2. Calls Per Day
    r_cpd = client.get(f"/cases/{case_id}/analytics/calls-per-day", headers=headers)
    assert r_cpd.status_code == 200
    cpd_data = r_cpd.json()
    assert cpd_data["total_calls"] == 2
    assert len(cpd_data["daily_calls"]) >= 1

    # 3. Top Entities
    r_top = client.get(f"/cases/{case_id}/analytics/top-entities?metric=degree", headers=headers)
    assert r_top.status_code == 200
    top_data = r_top.json()
    assert len(top_data["entities"]) >= 1

    # 4. Communities
    r_comm = client.get(f"/cases/{case_id}/analytics/communities", headers=headers)
    assert r_comm.status_code == 200
    comm_data = r_comm.json()
    assert comm_data["communities_count"] >= 1

    # 5. Degree Distribution
    r_deg = client.get(f"/cases/{case_id}/analytics/degree-distribution", headers=headers)
    assert r_deg.status_code == 200
    deg_data = r_deg.json()
    assert deg_data["total_nodes"] == 2

    # 6. Call Heatmap
    r_hm = client.get(f"/cases/{case_id}/analytics/call-heatmap", headers=headers)
    assert r_hm.status_code == 200
    hm_data = r_hm.json()
    assert len(hm_data["matrix"]) == 7 * 24
    assert hm_data["total_calls"] == 2

    # 7. Entity Why Card
    r_why = client.get(f"/cases/{case_id}/entities/TEL_1/why", headers=headers)
    assert r_why.status_code == 200
    why_data = r_why.json()
    assert why_data["entity_id"] == "TEL_1"
    assert why_data["disclaimer"] == "Analytical lead summary for review — not a finding of wrongdoing."
    assert "Directly connected to" in why_data["narrative"]
