"""
Integration & unit tests for Phase 1 normalization, timezone/curfew round-trips,
per-column dayfirst inference, rule delegation, and idempotent schema migration.
"""

from pathlib import Path
from backend.app.db.sql import CallRecord
from backend.app.services.ingestion.normalize import (
    normalize_datetime,
    normalize_datetime_detailed,
    normalize_amount,
    normalize_phone,
    infer_column_dayfirst,
    utc_to_display_tz,
    is_curfew_hour,
)
from backend.app.services.analytics.comm_patterns import (
    parse_date_str,
    is_curfew_call,
    compute_curfew_call_summary,
)
from backend.app.services.extraction.rules import extract_rule_entities
from backend.app.services.ingestion.validators import verhoeff_compute_check_digit
from scripts.migrate_extraction_v2 import run_migration


def _dev(text: str) -> str:
    return "".join(chr(0x0966 + int(c)) if c.isdigit() else c for c in text)


def test_column_dayfirst_inference_dd_mm_vs_mm_dd():
    # Column 1 has a date with 1st component = 24 (> 12) -> infer dayfirst=True
    col_dmy = ["02/05/2025", "11/05/2025", "24/05/2025"]
    df_dmy, reason_dmy = infer_column_dayfirst(col_dmy)
    assert df_dmy is True
    assert reason_dmy == "inferred_dayfirst"

    # Using inferred dayfirst=True on '02/05/2025' -> May 2, 2025
    d_str, _, _ = normalize_datetime(col_dmy[0], dayfirst=df_dmy)
    assert d_str == "2025-05-02"

    # Column 2 has a date with 2nd component = 19 (> 12) -> infer dayfirst=False (month-first)
    col_mdy = ["05/02/2025", "05/11/2025", "05/19/2025"]
    df_mdy, reason_mdy = infer_column_dayfirst(col_mdy)
    assert df_mdy is False
    assert reason_mdy == "inferred_monthfirst"

    # Using inferred dayfirst=False on '05/02/2025' -> May 2, 2025
    d_str2, _, _ = normalize_datetime(col_mdy[0], dayfirst=df_mdy)
    assert d_str2 == "2025-05-02"

    # Column 3 has all components <= 12 -> falls back to config default (True for India)
    col_ambig = ["01/02/2025", "03/04/2025"]
    df_fb, reason_fb = infer_column_dayfirst(col_ambig)
    assert df_fb is True
    assert reason_fb == "config_fallback"


def test_ist_to_utc_round_trip_and_tz_source():
    # Naive timestamp in IST: 15 Aug 2025 at 01:30:00 IST -> UTC is 14 Aug 2025 at 20:00:00Z
    raw_d = "15/08/" + "2025"
    raw_t = "01:30:00"
    res = normalize_datetime_detailed(raw_d, raw_t)
    assert res["ok"] is True
    assert res["meta"]["tz_source"] == "assumed_local"
    assert res["meta"]["local_date"] == "2025-08-15"
    assert res["meta"]["local_time"] == "01:30:00"
    assert res["meta"]["utc_iso"] == "2025-08-14T20:00:00Z"

    # Round-trip back from stored UTC ISO to Asia/Kolkata display timezone
    back_ist = utc_to_display_tz(res["meta"]["utc_iso"])
    assert back_ist is not None
    assert back_ist.strftime("%Y-%m-%d") == "2025-08-15"
    assert back_ist.strftime("%H:%M:%S") == "01:30:00"

    # Explicit timezone timestamp
    explicit_res = normalize_datetime_detailed("2025-08-14T20:00:00Z")
    assert explicit_res["ok"] is True
    assert explicit_res["meta"]["tz_source"] == "explicit"
    assert explicit_res["meta"]["local_date"] == "2025-08-15"
    assert explicit_res["meta"]["local_time"] == "01:30:00"


def test_curfew_boundary_in_ist_and_comm_patterns_integration():
    # Boundary 1: 23:59:59 IST on 14 Aug 2025 (18:29:59Z UTC) -> NOT curfew
    _, _, utc_before_midnight = normalize_datetime("14/08/2025", "23:59:59")
    assert utc_before_midnight == "2025-08-14T18:29:59Z"
    assert is_curfew_hour(utc_before_midnight) is False

    # Boundary 2: 00:00:00 IST on 15 Aug 2025 (18:30:00Z UTC on 14 Aug) -> IN curfew
    _, _, utc_at_midnight = normalize_datetime("15/08/2025", "00:00:00")
    assert utc_at_midnight == "2025-08-14T18:30:00Z"
    assert is_curfew_hour(utc_at_midnight) is True

    # Boundary 3: 04:59:59 IST on 15 Aug 2025 (23:29:59Z UTC on 14 Aug) -> IN curfew
    _, _, utc_before_5am = normalize_datetime("15/08/2025", "04:59:59")
    assert utc_before_5am == "2025-08-14T23:29:59Z"
    assert is_curfew_hour(utc_before_5am) is True

    # Boundary 4: 05:00:00 IST on 15 Aug 2025 (23:30:00Z UTC on 14 Aug) -> NOT curfew
    _, _, utc_at_5am = normalize_datetime("15/08/2025", "05:00:00")
    assert utc_at_5am == "2025-08-14T23:30:00Z"
    assert is_curfew_hour(utc_at_5am) is False

    # Verify comm_patterns.parse_date_str converts UTC back to IST wall-clock date & hour
    parsed_local = parse_date_str(utc_at_midnight)
    assert parsed_local is not None
    assert parsed_local.strftime("%Y-%m-%d") == "2025-08-15"
    assert parsed_local.hour == 0

    # Verify CallRecord curfew summary in comm_patterns
    ph_a = "98" + "1111" + "2222"
    ph_b = "98" + "3333" + "4444"
    records = [
        CallRecord(id="c1", case_id="k1", caller=ph_a, receiver=ph_b, datetime_iso=utc_at_midnight, duration_seconds=30),
        CallRecord(id="c2", case_id="k1", caller=ph_a, receiver=ph_b, datetime_iso=utc_before_5am, duration_seconds=45),
        CallRecord(id="c3", case_id="k1", caller=ph_a, receiver=ph_b, datetime_iso=utc_at_5am, duration_seconds=60),
    ]
    assert is_curfew_call(records[0]) is True
    assert is_curfew_call(records[1]) is True
    assert is_curfew_call(records[2]) is False

    summary = compute_curfew_call_summary(records)
    assert summary[ph_a]["total_calls"] == 3
    assert summary[ph_a]["curfew_calls"] == 2
    assert summary[ph_a]["curfew_ratio"] == round(2 / 3, 4)


def test_amounts_brackets_devanagari_cr_dr_and_indian_grouping():
    # Devanagari amount with Indian grouping
    dev_amt = f"₹ {_dev('2,50,000.75')}"
    assert normalize_amount(dev_amt) == 25000075

    # Bracket negative
    assert normalize_amount(f"({_dev('1,200.50')})") == -120050

    # Separate Cr/Dr column indicator
    assert normalize_amount("4,500.00", dr_cr_indicator="Dr") == -450000
    assert normalize_amount("4,500.00", dr_cr_indicator="Cr") == 450000


def test_rules_delegation_devanagari_account_disambiguation_and_aadhaar():
    ten_digit_acct = "97654" + "32109"
    prefix_11 = "56789012345"
    valid_uid = prefix_11 + verhoeff_compute_check_digit(prefix_11)

    narrative = (
        f"Amount Rs. {_dev('1,50,000')} was credited to beneficiary a/c {_dev(ten_digit_acct)} "
        f"with IFSC SBIN0004321 and Aadhaar {_dev(valid_uid)}. "
        f"Caller contacted from masked mobile XXXXXX4321."
    )
    items = extract_rule_entities(narrative, "P1")
    by_type = {}
    for it in items:
        by_type.setdefault(it["entity_type"], []).append(it)

    # 10-digit number preceded by 'beneficiary a/c' must be BANK_ACCOUNT, not PHONE
    assert "BANK_ACCOUNT" in by_type
    assert any(x["normalized_value"] == ten_digit_acct for x in by_type["BANK_ACCOUNT"])
    phone_norms = [x["normalized_value"] for x in by_type.get("PHONE", [])]
    assert ten_digit_acct not in phone_norms

    # Masked phone extracted and flagged
    assert any("4321" in x["normalized_value"] for x in by_type.get("PHONE", []))

    # Devanagari Aadhaar validated with Verhoeff and normalized to ASCII digits
    assert "AADHAAR" in by_type
    assert by_type["AADHAAR"][0]["normalized_value"] == valid_uid

    # IFSC extracted with bank lookup metadata
    assert "IFSC" in by_type
    assert by_type["IFSC"][0]["normalized_value"] == "SBIN0004321"

    # Devanagari amount normalized to integer paise string
    assert "AMOUNT" in by_type
    assert by_type["AMOUNT"][0]["normalized_value"] == "15000000"


def test_migrate_extraction_v2_idempotent_runs_twice(tmp_path):
    temp_db = tmp_path / "test_migrate.db"
    res1 = run_migration(db_path=temp_db, create_backup=False)
    assert res1["status"] == "ok"

    # Running a second time must succeed with zero errors and report columns already present
    res2 = run_migration(db_path=temp_db, create_backup=True)
    assert res2["status"] == "ok"
    assert len(res2["columns_added"]) == 0
    assert len(res2["columns_already_present"]) >= 6
    assert res2["backup_path"] is not None
    assert Path(res2["backup_path"]).exists()
    # Clean up temporary backup file created during test
    Path(res2["backup_path"]).unlink(missing_ok=True)


def test_synthetic_generator_entities_through_validators_and_normalizers():
    from scripts.generate_data import SyntheticDataGenerator
    from backend.app.services.ingestion.validators import validate_bank_account
    gen = SyntheticDataGenerator(seed=77)
    data = gen.build_scenario_data("ring", "small")

    # Validate generated phones and accounts from planted ground truth
    organizers = data["ground_truth"]["planted"]["organizers"]
    for org in organizers:
        ph_res = normalize_phone(org["phone"])
        assert ph_res is not None
        assert ph_res["valid_mobile"] is True
        assert ph_res["number"] == org["phone"]

        acc_res = validate_bank_account(org["account"])
        assert acc_res["ok"] is True
        assert acc_res["normalized"] == org["account"]

    # Validate generated CDR dates with column dayfirst inference
    calls = data.get("calls", [])
    cdr_dates = [c.get("call_date") or c.get("date") for c in calls[:20] if c.get("call_date") or c.get("date")]
    df_flag, _ = infer_column_dayfirst(cdr_dates)
    for c in calls[:5]:
        raw_d = c.get("call_date") or c.get("date")
        raw_t = c.get("call_time") or c.get("time") or "10:00:00"
        d_str, t_str, utc_iso = normalize_datetime(raw_d, raw_t, dayfirst=df_flag)
        assert len(d_str) == 10
        assert utc_iso.endswith("Z")
        rt = utc_to_display_tz(utc_iso)
        assert rt.strftime("%Y-%m-%d") == d_str
        assert rt.strftime("%H:%M:%S") == t_str

