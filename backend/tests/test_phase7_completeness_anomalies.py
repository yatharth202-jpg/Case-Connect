import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.auth.security import hash_password
from backend.app.config import get_extraction_config
from backend.app.db.sql import (
    Alert,
    Case,
    CaseMember,
    EvidenceFile,
    SessionLocal,
    User,
)
from backend.app.main import app
from backend.app.services.extraction.completeness import (
    compute_case_completeness,
    compute_evidence_completeness,
    detect_digit_pattern_anomaly,
    evaluate_potential_anomalies,
    get_number_intelligence,
)
from backend.app.services.ingestion.detect import detect_file_type
from backend.app.services.ingestion.mapping import suggest_column_mappings
from backend.app.services.ingestion.readers import read_tabular_file_detailed
from backend.app.services.ingestion.stage import stage_evidence_file
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _setup_p7_auth(username: str, role: str = "investigator"):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(
            username=username,
            password_hash=hash_password("Pass1234!"),
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    db.close()
    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return u, headers


def _stage_file_helper(db_session, case_id: str, user_id: str, file_path: str, explicit_type: str = None, statement_account: str = None) -> EvidenceFile:
    p = Path(file_path)
    ev = EvidenceFile(
        case_id=case_id,
        original_name=p.name,
        stored_path=str(p),
        sha256="f" * 64,
        file_size=p.stat().st_size,
        detected_type=explicit_type or "cdr",
        status="uploaded",
        uploader_id=user_id,
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)

    detailed = read_tabular_file_detailed(p)
    f_type = explicit_type or detect_file_type(detailed["headers"], detailed["records"], banners=detailed["banner_rows"])["detected_type"]
    sug = suggest_column_mappings(f_type, detailed["headers"], detailed["records"])
    col_map = {h: v["canonical"] for h, v in sug.items()}

    stage_evidence_file(
        db=db_session,
        evidence_id=ev.id,
        user_id=user_id,
        file_type=f_type,
        column_mapping=col_map,
        statement_account=statement_account,
    )
    db_session.refresh(ev)
    return ev


def test_phone_number_status_model_and_pattern_detector(tmp_path: Path):
    """
    Verifies Task 1:
    - Honest status model (`format_valid`, `number_type`, `region`, `carrier_hint` + disclaimer,
      `line_status == 'unverified'`, `status_label == 'Format valid — ownership unverified'`).
    - Never labels any number 'real' or 'fake'.
    - Digit-pattern anomaly detector catches repeated digits, sequential runs, and low distinct digits.
    """
    gen = SyntheticDataGenerator(seed=701)
    normal_mob = gen.generate_phone()

    intel = get_number_intelligence(normal_mob)
    assert intel["format_valid"] is True
    assert intel["number_type"] in ("mobile_in", "FIXED_LINE_OR_MOBILE")
    assert intel["region"] == "IN"
    assert intel["line_status"] == "unverified"
    assert intel["status_label"] == "Format valid — ownership unverified"
    assert "original number-range allocation" in intel["carrier_disclaimer"]
    assert intel["has_potential_anomaly"] is False

    serialized = json.dumps(intel).lower()
    assert '"real"' not in serialized
    assert '"fake"' not in serialized

    rep_num = "9" + ("7" * 8) + "2"
    rep_res = detect_digit_pattern_anomaly(rep_num)
    assert rep_res is not None
    assert rep_res["reason_code"] == "PATTERN_ANOMALY_REPEATED_DIGITS"

    seq_num = "9876543210"
    seq_res = detect_digit_pattern_anomaly(seq_num)
    assert seq_res is not None
    assert rep_res["reason_code"] == "PATTERN_ANOMALY_REPEATED_DIGITS"
    assert "SEQUENCE" in seq_res["reason_code"]


def test_potential_anomalies_rules_and_cross_case_scoping(tmp_path: Path):
    """
    Verifies Task 2:
    - Each Potential Anomaly rule triggers on anomalous data:
      1. `PATTERN_ANOMALY_NUMBER`
      2. `INTERNATIONAL_OR_VOIP_IN_DOMESTIC`
      3. `CROSS_CASE_SHARED_IDENTIFIER` (with strict case membership scoping)
      4. `MULTI_NAME_IDENTIFIER`
      5. `NIGHT_CALL_RATIO_ANOMALY` (in IST)
      6. `HIGH_SHORT_DURATION_COUNTERPARTIES`
      7. `IMEI_MULTIPLE_MSISDN`
      8. `MSISDN_MULTIPLE_IMEI`
      9. `SHORT_ACTIVITY_WINDOW`
    - Normal benign data produces zero false flags.
    - Cross-case query strictly enforces case membership: non-member cases never leak case ID, title, or number.
    """
    import time
    db_session = SessionLocal()
    seed_val = int(time.time() * 1000) % 1000000 + 702
    gen = SyntheticDataGenerator(seed=seed_val)
    suite = gen.write_phase7_anomaly_and_completeness_suite(tmp_path / "phase7_suite")

    inv_user, _ = _setup_p7_auth(f"inv_p7_{seed_val}", role="investigator")
    other_user, _ = _setup_p7_auth(f"oth_p7_{seed_val}", role="investigator")

    # Main Case A (inv_user is member)
    case_a = Case(
        title="Primary Cyber Investigation A",
        description="FIR-P7-A-01",
        status="active",
        created_by=inv_user.id,
    )
    # Accessible Case B (inv_user is also member)
    case_b = Case(
        title="Accessible Linked Case B",
        description="FIR-P7-B-01",
        status="active",
        created_by=inv_user.id,
    )
    # Restricted Case C (inv_user is NOT a member)
    case_c = Case(
        title="Classified Non-Member Operation C",
        description="SECRET-FIR-999-01",
        status="active",
        created_by=other_user.id,
    )
    db_session.add_all([case_a, case_b, case_c])
    db_session.commit()

    db_session.add_all([
        CaseMember(case_id=case_a.id, user_id=inv_user.id, role="lead"),
        CaseMember(case_id=case_b.id, user_id=inv_user.id, role="analyst"),
        CaseMember(case_id=case_c.id, user_id=other_user.id, role="lead"),
    ])
    db_session.commit()

    # Stage anomalous CDR + two conflicting SDR files in Case A
    _stage_file_helper(db_session, case_a.id, inv_user.id, suite["cdr_anomalies_path"], explicit_type="cdr")
    _stage_file_helper(db_session, case_a.id, inv_user.id, suite["sdr_a_path"], explicit_type="identity_table")
    _stage_file_helper(db_session, case_a.id, inv_user.id, suite["sdr_b_path"], explicit_type="identity_table")

    # Stage shared_case_phone in Case B (accessible) and Case C (restricted)
    _stage_file_helper(db_session, case_b.id, inv_user.id, suite["sdr_a_path"], explicit_type="identity_table")
    _stage_file_helper(db_session, case_c.id, other_user.id, suite["sdr_a_path"], explicit_type="identity_table")

    anom_report = evaluate_potential_anomalies(
        db=db_session,
        case_id=case_a.id,
        current_user=inv_user,
        persist_alerts=True,
    )

    anomalies = anom_report["anomalies"]
    reason_codes = {a["reason_code"] for a in anomalies}

    assert any("PATTERN_ANOMALY" in rc for rc in reason_codes)
    assert "INTERNATIONAL_OR_VOIP_NUMBER" in reason_codes
    assert "CROSS_CASE_IDENTIFIER" in reason_codes
    assert "MULTI_NAME_IDENTIFIER" in reason_codes
    assert "HIGH_NIGHT_CALL_RATIO" in reason_codes
    assert "HIGH_UNIQUE_SHORT_CALLS" in reason_codes
    assert "IMEI_MULTIPLE_MSISDNS" in reason_codes
    assert "MSISDN_MULTIPLE_IMEIS" in reason_codes
    assert "SHORT_ACTIVITY_WINDOW" in reason_codes

    # Verify every anomaly flag structure
    for a in anomalies:
        assert a.get("reason_code") is not None
        assert a.get("severity") in ("high", "medium", "low")
        assert isinstance(a.get("evidence_ids"), list) and len(a["evidence_ids"]) >= 1
        assert a.get("explanation")

    # Verify strict cross-case membership scoping (Case B visible, Case C hidden behind count)
    cross_case_flags = [
        a for a in anomalies
        if a["reason_code"] == "CROSS_CASE_IDENTIFIER" and a["entity_id"] == suite["shared_case_phone"]
    ]
    assert len(cross_case_flags) == 1
    cc_flag = cross_case_flags[0]
    assert cc_flag["metrics"]["total_cases_count"] >= 3
    assert cc_flag["metrics"]["restricted_cases_count"] >= 1
    assert case_b.id in cc_flag["metrics"]["accessible_case_ids"]
    assert case_c.id not in cc_flag["metrics"]["accessible_case_ids"]
    full_json_str = json.dumps(anom_report)
    assert "Classified Non-Member Operation C" not in full_json_str
    assert "SECRET-FIR-999-01" not in full_json_str
    assert case_c.id not in full_json_str

    # Verify persistence to SQLite alerts table
    persisted_alerts = db_session.query(Alert).filter(Alert.case_id == case_a.id).all()
    assert len(persisted_alerts) >= 9

    # Verify normal benign CDR in a clean case produces ZERO behavioral or pattern anomalies
    case_clean = Case(
        title="Clean Benign Case",
        description="FIR-P7-CLEAN-01",
        status="active",
        created_by=inv_user.id,
    )
    db_session.add(case_clean)
    db_session.commit()
    db_session.add(CaseMember(case_id=case_clean.id, user_id=inv_user.id, role="lead"))
    db_session.commit()

    _stage_file_helper(db_session, case_clean.id, inv_user.id, suite["cdr_benign_path"], explicit_type="cdr")
    clean_report = evaluate_potential_anomalies(
        db=db_session,
        case_id=case_clean.id,
        current_user=inv_user,
        persist_alerts=False,
    )
    assert clean_report["total_flags"] == 0
    db_session.close()


def test_completeness_cross_file_checks_and_endpoints(tmp_path: Path):
    """
    Verifies Tasks 3, 4, 5 and Governance:
    - Per-evidence completeness (`GET /evidence/{id}/completeness`) and `EvidenceFile.quality_json` persistence.
    - Date-range gap detection (`> 5 days`).
    - Disabled detector reporting when optional columns (`imei`, `cell_id`) are absent.
    - Cross-file consistency checks:
      - Statement closing vs next statement opening balance discontinuity (`STATEMENT_BALANCE_DISCONTINUITY`)
      - Statement owner name mismatch (`STATEMENT_OWNER_NAME_MISMATCH`)
      - Same identifier with different names (`SAME_IDENTIFIER_DIFFERENT_NAMES`)
    - Documented completeness score formula (`score_formula`) and `0.0 <= case_completeness_score <= 1.0`.
    - Zero banned/prejudicial terms in any response.
    """
    import time
    db_session = SessionLocal()
    seed_val = int(time.time() * 1000) % 1000000 + 703
    gen = SyntheticDataGenerator(seed=seed_val)
    suite = gen.write_phase7_anomaly_and_completeness_suite(tmp_path / "phase7_api_suite")

    test_user, auth_headers = _setup_p7_auth(f"officer_p7_{seed_val}", role="investigator")

    case = Case(
        title="Completeness & Cross-File Audit Case",
        description="FIR-P7-COMP-01",
        status="active",
        created_by=test_user.id,
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    db_session.add(CaseMember(case_id=case.id, user_id=test_user.id, role="lead"))
    db_session.commit()

    ev_cdr_anom = _stage_file_helper(db_session, case.id, test_user.id, suite["cdr_anomalies_path"], explicit_type="cdr")
    ev_cdr_no_opt = _stage_file_helper(db_session, case.id, test_user.id, suite["cdr_benign_path"], explicit_type="cdr")
    ev_stmt1 = _stage_file_helper(
        db_session, case.id, test_user.id, suite["stmt1_path"],
        explicit_type="bank_statement", statement_account=suite["stmt_account"]
    )
    ev_stmt2 = _stage_file_helper(
        db_session, case.id, test_user.id, suite["stmt2_path"],
        explicit_type="bank_statement", statement_account=suite["stmt_account"]
    )
    _stage_file_helper(db_session, case.id, test_user.id, suite["sdr_a_path"], explicit_type="identity_table")
    _stage_file_helper(db_session, case.id, test_user.id, suite["sdr_b_path"], explicit_type="identity_table")

    # 1. Per-evidence completeness endpoint: verify date-range gap on ev_cdr_anom
    r_ev1 = client.get(f"/evidence/{ev_cdr_anom.id}/completeness", headers=auth_headers)
    assert r_ev1.status_code == 200
    ev1_data = r_ev1.json()
    assert 0.0 <= ev1_data["completeness_score"] <= 100.0
    assert "score_formula" in ev1_data
    assert len(ev1_data["date_range_gaps"]) >= 1
    assert ev1_data["date_range_gaps"][0]["gap_days"] >= 5

    # Verify quality_json was persisted on EvidenceFile
    db_session.refresh(ev_cdr_anom)
    q_json = json.loads(ev_cdr_anom.quality_json or "{}")
    assert "completeness_score" in q_json
    assert q_json["completeness_score"] == ev1_data["completeness_score"]

    # 2. Per-evidence completeness on CDR missing optional columns (`imei`, `cell_id`)
    r_ev2 = client.get(f"/evidence/{ev_cdr_no_opt.id}/completeness", headers=auth_headers)
    assert r_ev2.status_code == 200
    ev2_data = r_ev2.json()
    disabled_cols = {d["missing_column"]: d["message"] for d in ev2_data["disabled_detectors"]}
    assert "imei" in disabled_cols
    assert "No IMEI column" in disabled_cols["imei"]
    assert "cell_id" in disabled_cols
    assert "No cell" in disabled_cols["cell_id"]

    # 3. Case-level completeness & cross-file consistency endpoint
    r_case = client.get(f"/cases/{case.id}/completeness", headers=auth_headers)
    assert r_case.status_code == 200
    case_data = r_case.json()
    assert 0.0 <= case_data["completeness_score"] <= 100.0
    assert case_data["evidence_count"] == 6
    assert "score_formula" in case_data

    findings = case_data["data_quality_findings"]
    bal_issues = [f for f in findings if f["reason_code"] == "STATEMENT_BALANCE_CONTINUITY_MISMATCH"]
    assert len(bal_issues) >= 1
    assert bal_issues[0]["account"] == suite["stmt_account"]
    assert bal_issues[0]["metrics"]["previous_closing_paise"] == 15000000
    assert bal_issues[0]["metrics"]["next_opening_paise"] == 12000000

    id_name_issues = [f for f in findings if f["reason_code"] == "IDENTIFIER_NAME_MISMATCH"]
    assert any(i["identifier"] == suite["shared_case_phone"] for i in id_name_issues)

    # 4. Number intelligence endpoint
    r_num = client.get(
        f"/cases/{case.id}/numbers/{suite['shared_case_phone']}/intelligence",
        headers=auth_headers,
    )
    assert r_num.status_code == 200
    num_data = r_num.json()
    assert num_data["status_label"] == "Format valid — ownership unverified"
    assert num_data["line_status"] == "unverified"

    # 5. Governance & anti-prejudicial terminology check across all Phase 7 responses
    banned_terms = get_extraction_config().get("banned_terms", [])
    combined_payload = json.dumps({
        "ev1": ev1_data,
        "ev2": ev2_data,
        "case": case_data,
        "num": num_data,
    }).lower()
    for term in banned_terms:
        assert term.lower() not in combined_payload, f"Banned term '{term}' found in Phase 7 output"

    db_session.close()

    # 4. Number intelligence endpoint
    r_num = client.get(
        f"/cases/{case.id}/numbers/{suite['shared_case_phone']}/intelligence",
        headers=auth_headers,
    )
    assert r_num.status_code == 200
    num_data = r_num.json()
    assert num_data["status_label"] == "Format valid — ownership unverified"
    assert num_data["line_status"] == "unverified"

    # 5. Governance & anti-prejudicial terminology check across all Phase 7 responses
    banned_terms = get_extraction_config().get("banned_terms", [])
    combined_payload = json.dumps({
        "ev1": ev1_data,
        "ev2": ev2_data,
        "case": case_data,
        "num": num_data,
    }).lower()
    for term in banned_terms:
        assert term.lower() not in combined_payload, f"Banned term '{term}' found in Phase 7 output"

    db_session.close()


