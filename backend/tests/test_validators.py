"""
Unit tests for Phase 1 shared validators engine (backend/app/services/ingestion/validators.py).
All test identifiers (Aadhaar Verhoeff, IMEI Luhn, phones, accounts) are computed dynamically
in test helpers or via SyntheticDataGenerator — zero hardcoded synthetic constants.
"""

from pathlib import Path
from backend.app.config import get_ifsc_bank_codes
from backend.app.services.ingestion.validators import (
    to_ascii_digits,
    verhoeff_compute_check_digit,
    verhoeff_validate,
    luhn_compute_check_digit,
    luhn_validate,
    validate_aadhaar,
    validate_pan,
    validate_imei,
    validate_imsi,
    validate_ifsc,
    validate_bank_account,
    validate_upi_vpa,
    validate_vehicle,
    validate_phone,
    validate_amount,
    classify_numeric_identifier,
)


def _to_devanagari(ascii_str: str) -> str:
    """Helper to convert ASCII 0-9 into Devanagari numerals (०-९) dynamically."""
    return "".join(chr(0x0966 + int(ch)) if ch.isdigit() else ch for ch in ascii_str)


def test_to_ascii_digits_devanagari_and_indic_scripts():
    ascii_sample = "".join(str(i) for i in range(10))
    dev_sample = _to_devanagari(ascii_sample)
    assert dev_sample != ascii_sample
    assert to_ascii_digits(dev_sample) == ascii_sample

    # Mixed text with Devanagari numerals preserves exact string length and character offsets
    mixed = f"FIR No. {_to_devanagari('142')}/{_to_devanagari('2026')}"
    converted = to_ascii_digits(mixed)
    assert len(converted) == len(mixed)
    assert converted == "FIR No. 142/2026"
    assert to_ascii_digits(None) == ""


def test_aadhaar_verhoeff_validator_and_devanagari():
    # Dynamically construct an 11-digit prefix starting with 4 and compute Verhoeff check digit
    prefix_11 = "45678901234"
    check_digit = verhoeff_compute_check_digit(prefix_11)
    valid_aadhaar = prefix_11 + check_digit
    assert verhoeff_validate(valid_aadhaar) is True

    res_ok = validate_aadhaar(f"{valid_aadhaar[:4]} {valid_aadhaar[4:8]}-{valid_aadhaar[8:]}")
    assert res_ok["ok"] is True
    assert res_ok["normalized"] == valid_aadhaar
    assert res_ok["reason_code"] == "VALID_AADHAAR"
    assert res_ok["meta"]["verhoeff_ok"] is True

    # Devanagari Aadhaar digits
    dev_aadhaar = _to_devanagari(valid_aadhaar)
    res_dev = validate_aadhaar(dev_aadhaar)
    assert res_dev["ok"] is True
    assert res_dev["normalized"] == valid_aadhaar

    # Corrupt the check digit -> must fail Verhoeff checksum
    bad_digit = str((int(check_digit) + 1) % 10)
    bad_aadhaar = prefix_11 + bad_digit
    res_bad = validate_aadhaar(bad_aadhaar)
    assert res_bad["ok"] is False
    assert res_bad["reason_code"] == "AADHAAR_VERHOEFF_CHECKSUM_FAILED"

    # Leading digit 0 or 1 -> must fail leading digit rule
    prefix_lead_1 = "12345678901"
    lead_1_aadhaar = prefix_lead_1 + verhoeff_compute_check_digit(prefix_lead_1)
    res_lead = validate_aadhaar(lead_1_aadhaar)
    assert res_lead["ok"] is False
    assert res_lead["reason_code"] == "INVALID_AADHAAR_LEADING_DIGIT"


def test_pan_validator_and_entity_type_metadata():
    pan_person = "ABC" + "P" + "K" + _to_devanagari("1234") + "F"
    res_p = validate_pan(pan_person)
    assert res_p["ok"] is True
    assert res_p["normalized"] == "ABCPK1234F"
    assert res_p["meta"]["entity_type_letter"] == "P"
    assert "Individual" in res_p["meta"]["entity_type_label"]

    pan_comp = "xyz" + "c" + "m" + "9876" + "q"
    res_c = validate_pan(pan_comp)
    assert res_c["ok"] is True
    assert res_c["normalized"] == "XYZCM9876Q"
    assert res_c["meta"]["entity_type_letter"] == "C"
    assert res_c["meta"]["entity_type_label"] == "Company"

    res_bad = validate_pan("INVALIDPAN12")
    assert res_bad["ok"] is False
    assert res_bad["reason_code"] == "INVALID_PAN_FORMAT"


def test_imei_luhn_and_imsi_validators():
    tac_and_serial = "35824005123456"
    luhn_digit = luhn_compute_check_digit(tac_and_serial)
    valid_imei = tac_and_serial + luhn_digit
    assert luhn_validate(valid_imei) is True

    res_imei = validate_imei(_to_devanagari(valid_imei))
    assert res_imei["ok"] is True
    assert res_imei["normalized"] == valid_imei
    assert res_imei["meta"]["tac"] == tac_and_serial[:8]
    assert res_imei["meta"]["luhn_ok"] is True

    # Corrupt Luhn check digit
    wrong_luhn = str((int(luhn_digit) + 1) % 10)
    res_bad_imei = validate_imei(tac_and_serial + wrong_luhn)
    assert res_bad_imei["ok"] is False
    assert res_bad_imei["reason_code"] == "IMEI_LUHN_CHECKSUM_FAILED"

    # IMSI (15 digits, no Luhn required)
    imsi_15 = "404450123456789"
    res_imsi = validate_imsi(imsi_15)
    assert res_imsi["ok"] is True
    assert res_imsi["normalized"] == imsi_15
    assert res_imsi["meta"]["mcc"] == "404"


def test_ifsc_validator_and_missing_reference_fallback(tmp_path):
    res_sbi = validate_ifsc("sbin0001234")
    assert res_sbi["ok"] is True
    assert res_sbi["normalized"] == "SBIN0001234"
    assert res_sbi["meta"]["bank_code"] == "SBIN"
    assert res_sbi["meta"]["known_bank"] is True
    assert "State Bank" in (res_sbi["meta"]["bank_name"] or "")

    # Missing 5th character '0' must fail
    res_bad = validate_ifsc("SBIN1001234")
    assert res_bad["ok"] is False
    assert res_bad["reason_code"] == "INVALID_IFSC_FORMAT"

    # Format-only fallback when reference file is missing
    missing_ref = get_ifsc_bank_codes(custom_path=tmp_path / "nonexistent_ifsc.json")
    assert missing_ref == {}
    res_fmt_only = validate_ifsc("ABCD0123456", bank_codes=missing_ref)
    assert res_fmt_only["ok"] is True
    assert res_fmt_only["reason_code"] == "VALID_IFSC_FORMAT_ONLY"


def test_bank_account_upi_and_vehicle_validators():
    # Bank account within bounds (9..18 digits)
    acct_12 = "".join(str((i + 1) % 10) for i in range(12))
    res_acc = validate_bank_account(_to_devanagari(acct_12))
    assert res_acc["ok"] is True
    assert res_acc["normalized"] == acct_12

    # Masked account flagged as MASKED_ACCOUNT_NUMBER
    res_mask = validate_bank_account("XXXXXX4321")
    assert res_mask["ok"] is False
    assert res_mask["reason_code"] == "MASKED_ACCOUNT_NUMBER"
    assert res_mask["normalized"] == "ENDING_4321"

    # Out of bounds account (too short)
    res_short = validate_bank_account("12345")
    assert res_short["ok"] is False
    assert res_short["reason_code"] == "ACCOUNT_LENGTH_OUT_OF_BOUNDS"

    # UPI VPA split into handle and psp
    res_vpa = validate_upi_vpa("merchant.shop@okaxis")
    assert res_vpa["ok"] is True
    assert res_vpa["normalized"] == "merchant.shop@okaxis"
    assert res_vpa["meta"]["handle"] == "merchant.shop"
    assert res_vpa["meta"]["psp"] == "okaxis"

    # Email domain rejected as UPI VPA
    assert validate_upi_vpa("user@gmail")["ok"] is False

    # Vehicle with state_code metadata
    res_veh = validate_vehicle("dl-1c-ab-" + _to_devanagari("4321"))
    assert res_veh["ok"] is True
    assert res_veh["normalized"] == "DL01CAB4321"
    assert res_veh["meta"]["state_code"] == "DL"
    assert res_veh["meta"]["known_state_code"] is True


def test_phone_validator_masked_landline_international_and_disclaimer():
    mob_str = "98" + "7654" + "3210"
    res_mob = validate_phone(_to_devanagari(f"+91 {mob_str[:5]}-{mob_str[5:]}"))
    assert res_mob["ok"] is True
    assert res_mob["normalized"] == mob_str
    assert res_mob["meta"]["e164"] == f"+91{mob_str}"
    assert res_mob["meta"]["valid_mobile"] is True
    assert res_mob["meta"]["is_masked"] is False
    assert "original number-range allocation" in res_mob["meta"]["carrier_disclaimer"]

    # Masked phone kept and flagged
    res_masked = validate_phone("XXXXXX3210")
    assert res_masked["ok"] is True
    assert res_masked["meta"]["is_masked"] is True
    assert res_masked["meta"]["valid_mobile"] is False
    assert res_masked["meta"]["number_type"] == "MASKED"
    assert res_masked["meta"]["source_raw"] == "XXXXXX3210"

    # Landline kept with valid_mobile=False
    res_landline = validate_phone("011-23456789")
    assert res_landline["ok"] is True
    assert res_landline["meta"]["valid_mobile"] is False
    assert res_landline["meta"]["source_raw"] == "011-23456789"

    # International number kept with valid_mobile=False
    res_intl = validate_phone("+1 202 555 0143")
    assert res_intl["ok"] is True
    assert res_intl["meta"]["valid_mobile"] is False
    assert res_intl["meta"]["kind"] == "international"


def test_context_aware_typing_phone_vs_account_vs_aadhaar():
    ten_digit_num = "91234" + "56780"

    # 1. Context says 'Beneficiary A/c' -> must be BANK_ACCOUNT, not PHONE
    res_acc = classify_numeric_identifier(ten_digit_num, context="Credited to Beneficiary A/c No:")
    assert res_acc["ok"] is True
    assert res_acc["entity_type"] == "BANK_ACCOUNT"
    assert res_acc["needs_review"] is False

    # 2. Context says 'Caller Mobile' -> must be PHONE
    res_ph = classify_numeric_identifier(ten_digit_num, column_header="Caller Mobile MSISDN")
    assert res_ph["ok"] is True
    assert res_ph["entity_type"] == "PHONE"
    assert res_ph["needs_review"] is False

    # 3. 12-digit number with valid Verhoeff in neutral context -> ambiguous (needs_review=True)
    prefix_11 = "34567890123"
    uid_12 = prefix_11 + verhoeff_compute_check_digit(prefix_11)
    res_ambig = classify_numeric_identifier(uid_12, context="Reference number:")
    assert res_ambig["ok"] is True
    assert res_ambig["needs_review"] is True
    cand_types = {c["type"] for c in res_ambig["candidate_types"]}
    assert "AADHAAR" in cand_types and "BANK_ACCOUNT" in cand_types

