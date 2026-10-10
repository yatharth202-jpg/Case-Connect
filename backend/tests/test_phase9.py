import json
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, CaseSetting, EvidenceFile,
    Entity, CallRecord, Transaction, ExtractedEntity,
    Alert, LeadDecision, SavedView
)
from backend.app.auth.security import hash_password

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


def test_txns_per_day_endpoint():
    token = get_token("investigator_phase9_txns")
    case_id = create_case(token, "Case Phase 9 Txns Per Day")
    db = SessionLocal()

    d1 = make_date_str(5)
    d2 = make_date_str(3)

    acc1 = "ACC_P9_" + "101"
    acc2 = "ACC_P9_" + "202"

    t1 = Transaction(
        case_id=case_id,
        source_file="bank_feed_1.csv",
        source_ref="1",
        txn_id="TX_P9_1",
        from_account=acc1,
        to_account=acc2,
        amount_paise=5000000, # Rs 50,000
        date_iso=d1,
        fingerprint="fp_p9_tx_1"
    )
    t2 = Transaction(
        case_id=case_id,
        source_file="bank_feed_1.csv",
        source_ref="2",
        txn_id="TX_P9_2",
        from_account=acc1,
        to_account=acc2,
        amount_paise=15000000, # Rs 150,000
        date_iso=d1,
        fingerprint="fp_p9_tx_2"
    )
    t3 = Transaction(
        case_id=case_id,
        source_file="bank_feed_1.csv",
        source_ref="3",
        txn_id="TX_P9_3",
        from_account=acc2,
        to_account=acc1,
        amount_paise=2500000, # Rs 25,000
        date_iso=d2,
        fingerprint="fp_p9_tx_3"
    )
    db.add_all([t1, t2, t3])
    db.commit()
    db.close()

    res = client.get(
        f"/cases/{case_id}/analytics/txns-per-day",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_transactions"] == 3
    assert data["total_volume_paise"] == 22500000
    assert data["total_volume_inr"] == 225000.0
    assert len(data["daily_txns"]) == 2
    assert data["peak_day"]["date"] == d1
    assert data["peak_day"]["volume_inr"] == 200000.0


def test_timeline_endpoint_and_pre_document_anomaly():
    token = get_token("investigator_phase9_timeline")
    case_id = create_case(token, "Case Phase 9 Timeline")
    db = SessionLocal()

    # Early activity: Call spike on day -10
    spike_date = make_date_str(10)
    alt = Alert(
        case_id=case_id,
        pattern_type="sudden_spike",
        severity="high",
        entity_id="TEL_P9_ORGANISER",
        alert_date=spike_date,
        explanation="Sudden spike in call activity: 45 calls (baseline 4.0 calls/day)"
    )

    # Transfer wave on day -8
    wave_date = make_date_str(8)
    t1 = Transaction(
        case_id=case_id,
        source_file="bank_mules.csv",
        source_ref="10",
        txn_id="TX_P9_MULE_1",
        from_account="ACC_P9_MULE_A",
        to_account="ACC_P9_POOL",
        amount_paise=35000000,
        date_iso=wave_date,
        fingerprint="fp_p9_mule_1"
    )

    # Document registration: FIR registered later on day -2
    fir_date = make_date_str(2)
    u_obj = db.query(User).filter(User.username == "investigator_phase9_timeline").first()
    ev_file = EvidenceFile(
        case_id=case_id,
        original_name="FIR_Cyber_Cell_2026.pdf",
        stored_path="uploads/test_fir.pdf",
        sha256="abc1234567890abcdef",
        file_size=1024,
        detected_type="text_document",
        status="ingested",
        uploader_id=u_obj.id,
        created_at=datetime.utcnow() - timedelta(days=2)
    )
    db.add(ev_file)
    db.flush()

    doc_date = ExtractedEntity(
        case_id=case_id,
        evidence_id=ev_file.id,
        entity_type="fir_date",
        raw_value=fir_date,
        normalized_value=fir_date,
        page_or_paragraph="Page 1",
        confidence=0.95,
        method="regex",
        status="confirmed"
    )

    db.add_all([alt, t1, doc_date])
    db.commit()
    db.close()

    res = client.get(
        f"/cases/{case_id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_events"] >= 3
    events = data["events"]

    # Verify chronological sort: spike_date < wave_date < fir_date
    timestamps = [e["timestamp"] for e in events]
    assert timestamps == sorted(timestamps)

    # Check timing insight: pre-document anomaly detected
    insight = data["timing_insight"]
    assert insight is not None
    assert insight["is_pre_document_anomaly"] is True
    assert insight["delta_days"] == 8 # 10 days ago vs 2 days ago = 8 days delta
    assert insight["earliest_anomaly_date"] == spike_date
    assert insight["earliest_document_date"] == fir_date


def test_case_settings_recompute_and_audit():
    token = get_token("investigator_phase9_settings")
    case_id = create_case(token, "Case Phase 9 Settings Recompute")

    # Update settings
    settings_override = {
        "communication": {
            "spike": {
                "mad_multiplier": 2.5,
                "min_call_floor": 3
            }
        }
    }
    put_res = client.put(
        f"/cases/{case_id}/settings",
        headers={"Authorization": f"Bearer {token}"},
        json=settings_override
    )
    assert put_res.status_code == 200

    # Call recompute endpoint
    recomp_res = client.post(
        f"/cases/{case_id}/settings/recompute",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert recomp_res.status_code == 200
    recomp_data = recomp_res.json()
    assert recomp_data["status"] == "success"

    # Verify audit log recorded action 'analytics_recompute'
    db = SessionLocal()
    from backend.app.db.sql import AuditLog
    entry = db.query(AuditLog).filter(
        AuditLog.case_id == case_id,
        AuditLog.action == "analytics_recompute"
    ).first()
    assert entry is not None
    db.close()


def test_saved_views_crud():
    token = get_token("investigator_phase9_views")
    case_id = create_case(token, "Case Phase 9 Views")

    # 1. Create Saved View
    view_payload = {
        "title": "Mule Ring 2-Hop Inspection View",
        "view_config": {
            "selected_node": "ACC_P9_MULE_A",
            "hops": 2,
            "filter_types": ["phone", "account"],
            "active_tab": "graph"
        }
    }
    create_res = client.post(
        f"/cases/{case_id}/saved-views",
        headers={"Authorization": f"Bearer {token}"},
        json=view_payload
    )
    assert create_res.status_code == 200
    view_data = create_res.json()
    assert view_data["title"] == "Mule Ring 2-Hop Inspection View"
    view_id = view_data["id"]

    # 2. List Saved Views
    list_res = client.get(
        f"/cases/{case_id}/saved-views",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert list_res.status_code == 200
    views_list = list_res.json()
    assert len(views_list) >= 1
    assert any(v["id"] == view_id for v in views_list)

    # 3. Delete Saved View
    del_res = client.delete(
        f"/cases/{case_id}/saved-views/{view_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify deleted
    list_res2 = client.get(
        f"/cases/{case_id}/saved-views",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert not any(v["id"] == view_id for v in list_res2.json())
