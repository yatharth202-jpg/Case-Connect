import json
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, User, Transaction, Case
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

# ---------------------------------------------------------------------
# 1. Outflow Traversal Reaches Multi-Hop Destination
# ---------------------------------------------------------------------
def test_money_trail_outflow_reaches_destination():
    token = get_token("analyst_money1")
    case_id = create_case(token, "Money Trail Outflow Case")

    db = SessionLocal()
    # A (Victim pool) -> B (Mule 1) -> C (Mule 2) -> D (Shell entity)
    acc_a = "ACC_COLLECT_01"
    acc_b = "ACC_MULE_02"
    acc_c = "ACC_MULE_03"
    acc_d = "ACC_SHELL_04"

    db.add(Transaction(case_id=case_id, from_account=acc_a, to_account=acc_b, amount_paise=50000000, date_iso="2024-01-10T10:00:00", fingerprint=f"t1_{case_id}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_id, from_account=acc_b, to_account=acc_c, amount_paise=48000000, date_iso="2024-01-10T14:00:00", fingerprint=f"t2_{case_id}", source_file="b.csv", source_ref="2"))
    db.add(Transaction(case_id=case_id, from_account=acc_c, to_account=acc_d, amount_paise=45000000, date_iso="2024-01-11T09:00:00", fingerprint=f"t3_{case_id}", source_file="b.csv", source_ref="3"))
    db.commit()
    db.close()

    # 1 Hop from A: reaches only B
    res1 = client.get(f"/cases/{case_id}/money-trail?account={acc_a}&hops=1&direction=out", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    data1 = res1.json()
    node_ids1 = [n["id"] for n in data1["nodes"]]
    assert acc_a in node_ids1
    assert acc_b in node_ids1
    assert acc_d not in node_ids1

    # 3 Hops from A: reaches all the way to shell account D
    res3 = client.get(f"/cases/{case_id}/money-trail?account={acc_a}&hops=3&direction=out", headers={"Authorization": f"Bearer {token}"})
    assert res3.status_code == 200
    data3 = res3.json()
    node_ids3 = [n["id"] for n in data3["nodes"]]
    assert acc_a in node_ids3
    assert acc_b in node_ids3
    assert acc_c in node_ids3
    assert acc_d in node_ids3

    # Check ordered path trace
    paths = data3["ordered_paths"]
    assert len(paths) > 0
    full_path = next(p for p in paths if p["sequence"][-1] == acc_d)
    assert full_path["sequence"] == [acc_a, acc_b, acc_c, acc_d]
    assert full_path["length"] == 3

# ---------------------------------------------------------------------
# 2. Minimum Amount Filtering and Hidden Edges
# ---------------------------------------------------------------------
def test_min_amount_filtering_and_hidden_edges():
    token = get_token("analyst_money2")
    case_id = create_case(token, "Money Trail Filter Case")

    db = SessionLocal()
    acc_src = "ACC_FILTER_SRC"
    acc_large = "ACC_FILTER_LARGE"
    acc_small = "ACC_FILTER_SMALL"

    # Large transfer: ₹50,000 (5,000,000 paise)
    db.add(Transaction(case_id=case_id, from_account=acc_src, to_account=acc_large, amount_paise=5000000, date_iso="2024-02-01T10:00:00", fingerprint=f"tf1_{case_id}", source_file="b.csv", source_ref="1"))
    # Small transfer: ₹500 (50,000 paise)
    db.add(Transaction(case_id=case_id, from_account=acc_src, to_account=acc_small, amount_paise=50000, date_iso="2024-02-01T11:00:00", fingerprint=f"tf2_{case_id}", source_file="b.csv", source_ref="2"))
    db.commit()
    db.close()

    # Query with min_amount = ₹1,000
    # ACC_SMALL should not be reachable by qualifying edges from ACC_SRC
    res = client.get(f"/cases/{case_id}/money-trail?account={acc_src}&min_amount=1000&hops=1&direction=out", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    visible_targets = [e["target"] for e in data["edges"]]
    assert acc_large in visible_targets
    assert acc_small not in visible_targets

    # Query direction=both without min_amount filter: both are visible
    res_all = client.get(f"/cases/{case_id}/money-trail?account={acc_src}&min_amount=0&hops=1&direction=out", headers={"Authorization": f"Bearer {token}"})
    assert res_all.status_code == 200
    all_targets = [e["target"] for e in res_all.json()["edges"]]
    assert acc_large in all_targets
    assert acc_small in all_targets

# ---------------------------------------------------------------------
# 3. Focus Account Totals Exact Calculation
# ---------------------------------------------------------------------
def test_focus_account_totals_exact_calculation():
    token = get_token("analyst_money3")
    case_id = create_case(token, "Money Trail Totals Case")

    db = SessionLocal()
    acc_target = "ACC_TOTALS_TARGET"
    acc_payer1 = "ACC_PAYER_1"
    acc_payer2 = "ACC_PAYER_2"
    acc_vendor = "ACC_VENDOR_1"

    # Inflows: 100,000 paise (₹1,000) + 250,000 paise (₹2,500) = 350,000 paise (₹3,500)
    db.add(Transaction(case_id=case_id, from_account=acc_payer1, to_account=acc_target, amount_paise=100000, date_iso="2024-03-01T10:00:00", fingerprint=f"tot1_{case_id}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_id, from_account=acc_payer2, to_account=acc_target, amount_paise=250000, date_iso="2024-03-01T11:00:00", fingerprint=f"tot2_{case_id}", source_file="b.csv", source_ref="2"))
    # Outflow: 150,000 paise (₹1,500)
    db.add(Transaction(case_id=case_id, from_account=acc_target, to_account=acc_vendor, amount_paise=150000, date_iso="2024-03-02T12:00:00", fingerprint=f"tot3_{case_id}", source_file="b.csv", source_ref="3"))
    db.commit()
    db.close()

    res = client.get(f"/cases/{case_id}/money-trail?account={acc_target}&hops=1&direction=both", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    totals = res.json()["totals"]

    assert totals["inflow_paise"] == 350000
    assert totals["outflow_paise"] == 150000
    assert totals["net_paise"] == 200000
    assert totals["inflow_inr"] == 3500.0
    assert totals["outflow_inr"] == 1500.0
    assert totals["net_inr"] == 2000.0
    assert totals["txn_count"] == 3
    assert totals["counterparties"] == 3

# ---------------------------------------------------------------------
# 4. Pattern Detection: Fan-In and Rapid Pass-Through
# ---------------------------------------------------------------------
def test_pattern_detection_fan_in_and_rapid_pass_through():
    token = get_token("analyst_money4")
    case_id = create_case(token, "Pattern Detection Case")

    db = SessionLocal()
    pool_acc = "ACC_POOL_HOT"
    out_acc = "ACC_CASH_OUT"

    # Fan-in: 4 distinct sources send money on same day
    db.add(Transaction(case_id=case_id, from_account="VICTIM_01", to_account=pool_acc, amount_paise=1000000, date_iso="2024-04-01T08:00:00", fingerprint=f"pat1_{case_id}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_id, from_account="VICTIM_02", to_account=pool_acc, amount_paise=1000000, date_iso="2024-04-01T09:00:00", fingerprint=f"pat2_{case_id}", source_file="b.csv", source_ref="2"))
    db.add(Transaction(case_id=case_id, from_account="VICTIM_03", to_account=pool_acc, amount_paise=1000000, date_iso="2024-04-01T10:00:00", fingerprint=f"pat3_{case_id}", source_file="b.csv", source_ref="3"))
    db.add(Transaction(case_id=case_id, from_account="VICTIM_04", to_account=pool_acc, amount_paise=1000000, date_iso="2024-04-01T11:00:00", fingerprint=f"pat4_{case_id}", source_file="b.csv", source_ref="4"))

    # Rapid pass-through: 90% leaves 4 hours later (₹36,000 out of ₹40,000)
    db.add(Transaction(case_id=case_id, from_account=pool_acc, to_account=out_acc, amount_paise=3600000, date_iso="2024-04-01T15:00:00", fingerprint=f"pat5_{case_id}", source_file="b.csv", source_ref="5"))
    db.commit()
    db.close()

    res = client.get(f"/cases/{case_id}/money-trail?account={pool_acc}&hops=1&direction=both", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    patterns = res.json()["patterns"]
    pattern_names = [p["pattern"] for p in patterns if p["account"] == pool_acc]

    assert "fan_in" in pattern_names
    assert "rapid_pass_through" in pattern_names

    # Check evidence keys are present
    fan_in_item = next(p for p in patterns if p["pattern"] == "fan_in")
    assert len(fan_in_item["evidence_txn_keys"]) >= 4

# ---------------------------------------------------------------------
# 5. Benign Account Not Flagged Rapid Pass-Through
# ---------------------------------------------------------------------
def test_benign_account_not_flagged_rapid_pass_through():
    token = get_token("analyst_money5")
    case_id = create_case(token, "Benign Account Case")

    db = SessionLocal()
    shop_acc = "ACC_SHOP_BENIGN"

    # Shop receives multiple deposits on day 1
    db.add(Transaction(case_id=case_id, from_account="CUST_1", to_account=shop_acc, amount_paise=200000, date_iso="2024-05-01T10:00:00", fingerprint=f"bg1_{case_id}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_id, from_account="CUST_2", to_account=shop_acc, amount_paise=300000, date_iso="2024-05-01T11:00:00", fingerprint=f"bg2_{case_id}", source_file="b.csv", source_ref="2"))

    # Shop pays a supplier 10 days later (beyond 48 hour window)
    db.add(Transaction(case_id=case_id, from_account=shop_acc, to_account="SUPPLIER", amount_paise=400000, date_iso="2024-05-11T10:00:00", fingerprint=f"bg3_{case_id}", source_file="b.csv", source_ref="3"))
    db.commit()
    db.close()

    res = client.get(f"/cases/{case_id}/money-trail?account={shop_acc}&hops=1&direction=both", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    patterns = res.json()["patterns"]
    rpt_flags = [p for p in patterns if p["account"] == shop_acc and p["pattern"] == "rapid_pass_through"]
    assert len(rpt_flags) == 0

# ---------------------------------------------------------------------
# 6. Case Settings Override Alters Pattern Detection
# ---------------------------------------------------------------------
def test_case_settings_override_alters_pattern_detection():
    token = get_token("analyst_money6")
    case_id = create_case(token, "Settings Override Case")

    db = SessionLocal()
    acc_test = "ACC_THRESH_TEST"

    # 3 senders (triggers default fan_in of min_sources=3)
    db.add(Transaction(case_id=case_id, from_account="S1", to_account=acc_test, amount_paise=100000, date_iso="2024-06-01T10:00:00", fingerprint=f"st1_{case_id}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_id, from_account="S2", to_account=acc_test, amount_paise=100000, date_iso="2024-06-01T10:00:00", fingerprint=f"st2_{case_id}", source_file="b.csv", source_ref="2"))
    db.add(Transaction(case_id=case_id, from_account="S3", to_account=acc_test, amount_paise=100000, date_iso="2024-06-01T10:00:00", fingerprint=f"st3_{case_id}", source_file="b.csv", source_ref="3"))
    db.commit()
    db.close()

    # Step 1: Default threshold min_sources=3 -> should be flagged
    res_before = client.get(f"/cases/{case_id}/money-trail?account={acc_test}&hops=1&direction=in", headers={"Authorization": f"Bearer {token}"})
    assert res_before.status_code == 200
    pats_before = [p["pattern"] for p in res_before.json()["patterns"] if p["account"] == acc_test]
    assert "fan_in" in pats_before

    # Step 2: Override setting: raise min_sources to 10
    new_settings = {
        "money": {
            "fan_in": {
                "min_sources": 10,
                "window_days": 7
            }
        }
    }
    put_res = client.put(f"/cases/{case_id}/settings", json=new_settings, headers={"Authorization": f"Bearer {token}"})
    assert put_res.status_code == 200

    # Step 3: Now 3 senders is below threshold of 10 -> NOT flagged
    res_after = client.get(f"/cases/{case_id}/money-trail?account={acc_test}&hops=1&direction=in", headers={"Authorization": f"Bearer {token}"})
    assert res_after.status_code == 200
    pats_after = [p["pattern"] for p in res_after.json()["patterns"] if p["account"] == acc_test and p["pattern"] == "fan_in"]
    assert len(pats_after) == 0

# ---------------------------------------------------------------------
# 7. Case Isolation for Money Trail
# ---------------------------------------------------------------------
def test_case_isolation_for_money_trail():
    token = get_token("analyst_money7")
    case_a = create_case(token, "Case Isolation A")
    case_b = create_case(token, "Case Isolation B")

    db = SessionLocal()
    acc_secret_a = "ACC_CASE_A_SECRET"
    acc_secret_b = "ACC_CASE_B_SECRET"

    db.add(Transaction(case_id=case_a, from_account="A1", to_account=acc_secret_a, amount_paise=100000, date_iso="2024-07-01", fingerprint=f"iso1_{case_a}", source_file="b.csv", source_ref="1"))
    db.add(Transaction(case_id=case_b, from_account="B1", to_account=acc_secret_b, amount_paise=100000, date_iso="2024-07-01", fingerprint=f"iso2_{case_b}", source_file="b.csv", source_ref="2"))
    db.commit()
    db.close()

    # Query Case A: Should never return ACC_CASE_B_SECRET
    res_a = client.get(f"/cases/{case_a}/money-trail?hops=2&direction=both", headers={"Authorization": f"Bearer {token}"})
    assert res_a.status_code == 200
    accounts_a = [n["id"] for n in res_a.json()["nodes"]]
    assert acc_secret_a in accounts_a
    assert acc_secret_b not in accounts_a

# ---------------------------------------------------------------------
# 8. Data-Driven Quantiles Analytics
# ---------------------------------------------------------------------
def test_txn_volume_quantiles_analytics():
    token = get_token("analyst_money8")
    case_id = create_case(token, "Quantiles Analytics Case")

    db = SessionLocal()
    # Add transactions with varied amounts: ₹100, ₹200, ₹500, ₹1000, ₹5000
    for idx, amt_inr in enumerate([100, 200, 500, 1000, 5000]):
        db.add(Transaction(
            case_id=case_id,
            from_account=f"Q_SRC_{idx}",
            to_account="Q_DST",
            amount_paise=int(amt_inr * 100),
            date_iso=f"2024-08-0{idx+1}T10:00:00",
            fingerprint=f"qfp_{idx}_{case_id}",
            source_file="q.csv",
            source_ref=str(idx)
        ))
    db.commit()
    db.close()

    res = client.get(f"/cases/{case_id}/analytics/txn-volume", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["total_txns"] == 5
    assert data["total_volume_inr"] == 6800.0
    q = data["quantiles"]
    assert q["min"] == 100.0
    assert q["max"] == 5000.0
    assert q["p50"] == 500.0
    assert len(data["daily_volume"]) == 5
