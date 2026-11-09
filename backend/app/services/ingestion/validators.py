"""
Unified, config-driven normalization and validator engine for CaseConnect AI (Extraction V2).

All validators are pure functions (no database or network I/O), read their parameters from
backend/config/defaults.yaml (and backend/config/reference/ifsc_bank_codes.json) via
backend.app.config, never raise exceptions on malformed input, and return a standardized
dictionary:
    {
        "ok": bool,
        "normalized": Any,
        "reason_code": str,
        "meta": Dict[str, Any]
    }

NOTE ON TELECOM METADATA:
Carrier and geographic region metadata derived from `phonenumbers` reflect original
number-range allocation only and cannot prove current subscriber ownership or that a
line is currently active.
"""

import re
import ipaddress
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional, Tuple

import phonenumbers
from phonenumbers import PhoneNumberType, geocoder, carrier
from dateutil import parser as dt_parser

from backend.app.config import get_extraction_config, get_ifsc_bank_codes

# ---------------------------------------------------------------------------
# 1. Unicode Numeral Script Conversion (Devanagari & Indic scripts -> ASCII)
# ---------------------------------------------------------------------------

SCRIPT_DIGIT_RANGES: Dict[str, Tuple[int, int]] = {
    "devanagari": (0x0966, 0x096F),       # ० १ २ ३ ४ ५ ६ ७ ८ ९
    "bengali": (0x09E6, 0x09EF),          # ०-९ Bengali
    "gurmukhi": (0x0A66, 0x0A6F),         # ੦-੯ Gurmukhi
    "gujarati": (0x0AE6, 0x0AEF),         # ૦-૯ Gujarati
    "odia": (0x0B66, 0x0B6F),             # ୦-୯ Odia
    "tamil": (0x0BE6, 0x0BEF),            # ௦-௯ Tamil
    "telugu": (0x0C66, 0x0C6F),           # ౦-౯ Telugu
    "kannada": (0x0CE6, 0x0CEF),          # ೦-೯ Kannada
    "malayalam": (0x0D66, 0x0D6F),        # ൦-൯ Malayalam
    "arabic_indic": (0x0660, 0x0669),     # ٠-٩ Arabic-Indic
    "ext_arabic_indic": (0x06F0, 0x06F9), # ۰-۹ Extended Arabic-Indic / Persian
    "fullwidth": (0xFF10, 0xFF19),        # ０-９ Fullwidth
}


def to_ascii_digits(text: Any, scripts: Optional[List[str]] = None) -> str:
    """
    Converts Devanagari and other configured Unicode numeral systems to ASCII '0'-'9'.
    Never raises on None or non-string input.
    """
    if text is None:
        return ""
    s = str(text)
    if not s:
        return ""

    if scripts is None:
        cfg = get_extraction_config()
        scripts = cfg.get("digit_scripts") or list(SCRIPT_DIGIT_RANGES.keys())

    active_ranges: List[Tuple[int, int]] = []
    for name in scripts:
        key = str(name).strip().lower()
        if key in SCRIPT_DIGIT_RANGES:
            active_ranges.append(SCRIPT_DIGIT_RANGES[key])
            if key == "arabic_indic" and SCRIPT_DIGIT_RANGES["ext_arabic_indic"] not in active_ranges:
                active_ranges.append(SCRIPT_DIGIT_RANGES["ext_arabic_indic"])
    if not active_ranges:
        active_ranges = [SCRIPT_DIGIT_RANGES["devanagari"]]

    out_chars: List[str] = []
    for ch in s:
        cp = ord(ch)
        if cp < 128:
            out_chars.append(ch)
            continue
        converted = False
        for start_cp, end_cp in active_ranges:
            if start_cp <= cp <= end_cp:
                out_chars.append(chr(ord("0") + (cp - start_cp)))
                converted = True
                break
        if not converted:
            out_chars.append(ch)
    return "".join(out_chars)


# ---------------------------------------------------------------------------
# 2. Verhoeff Checksum (Aadhaar) & Luhn Checksum (IMEI)
# ---------------------------------------------------------------------------

_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

_VERHOEFF_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_validate(num_str: str) -> bool:
    """Returns True if num_str is all ASCII digits and satisfies the Verhoeff checksum."""
    if not num_str or not num_str.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(num_str)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def verhoeff_compute_check_digit(prefix_digits: str) -> str:
    """Computes the Verhoeff check digit for a numeric prefix string."""
    c = 0
    for i, ch in enumerate(reversed(prefix_digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(ch)]]
    return str(_VERHOEFF_INV[c])


def luhn_validate(num_str: str) -> bool:
    """Returns True if num_str is all ASCII digits and satisfies the Luhn mod-10 checksum."""
    if not num_str or not num_str.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(num_str)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (total % 10) == 0


def luhn_compute_check_digit(prefix_digits: str) -> str:
    """Computes the Luhn check digit for a numeric prefix string (e.g., 14-digit IMEI prefix)."""
    total = 0
    for i, ch in enumerate(reversed(prefix_digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - (total % 10)) % 10)


# ---------------------------------------------------------------------------
# 3. Structured Identifier Validators
# ---------------------------------------------------------------------------

def validate_aadhaar(raw: Any) -> Dict[str, Any]:
    """
    Validates a 12-digit Indian Aadhaar number:
      - Converts configured Unicode digits to ASCII.
      - Must be 12 digits, first digit in 2..9.
      - Verifies Verhoeff checksum when extraction.validators.aadhaar_checksum is True.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    if not s:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    cleaned = re.sub(r"[\s\-]", "", s)
    if not cleaned.isdigit() or len(cleaned) != 12:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_AADHAAR_LENGTH_OR_CHARS",
            "meta": {"source_raw": source_raw},
        }

    if cleaned[0] not in "23456789":
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_AADHAAR_LEADING_DIGIT",
            "meta": {"source_raw": source_raw, "leading_digit": cleaned[0]},
        }

    cfg = get_extraction_config().get("validators", {})
    enforce_checksum = bool(cfg.get("aadhaar_checksum", True))
    checksum_ok = verhoeff_validate(cleaned)

    if enforce_checksum and not checksum_ok:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "AADHAAR_VERHOEFF_CHECKSUM_FAILED",
            "meta": {"source_raw": source_raw, "verhoeff_ok": False},
        }

    return {
        "ok": True,
        "normalized": cleaned,
        "reason_code": "VALID_AADHAAR",
        "meta": {
            "source_raw": source_raw,
            "verhoeff_ok": checksum_ok,
            "masked_display": f"XXXX-XXXX-{cleaned[-4:]}",
        },
    }


PAN_REGEX = re.compile(r"^([A-Z]{3})([A-Z])([A-Z])([0-9]{4})([A-Z])$")
PAN_ENTITY_TYPES: Dict[str, str] = {
    "P": "Individual / Person",
    "C": "Company",
    "H": "Hindu Undivided Family (HUF)",
    "F": "Partnership Firm",
    "A": "Association of Persons (AOP)",
    "T": "Trust",
    "B": "Body of Individuals (BOI)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "G": "Government Agency",
}


def validate_pan(raw: Any) -> Dict[str, Any]:
    """
    Validates an Indian Permanent Account Number (PAN): ^[A-Z]{5}[0-9]{4}[A-Z]$.
    Exposes the 4th character entity-type indicator in meta.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip().upper()
    cleaned = re.sub(r"[\s\-]", "", s)
    if not cleaned:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    m = PAN_REGEX.match(cleaned)
    if not m:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_PAN_FORMAT",
            "meta": {"source_raw": source_raw},
        }

    type_letter = m.group(2)
    return {
        "ok": True,
        "normalized": cleaned,
        "reason_code": "VALID_PAN",
        "meta": {
            "source_raw": source_raw,
            "entity_type_letter": type_letter,
            "entity_type_label": PAN_ENTITY_TYPES.get(type_letter, "Other"),
            "surname_initial": m.group(3),
        },
    }


def validate_imei(raw: Any) -> Dict[str, Any]:
    """
    Validates a 15-digit mobile equipment identifier (IMEI) with Luhn checksum.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    cleaned = re.sub(r"[\s\-/]", "", s)
    if not cleaned:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    if not cleaned.isdigit() or len(cleaned) != 15:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_IMEI_LENGTH",
            "meta": {"source_raw": source_raw},
        }

    cfg = get_extraction_config().get("validators", {})
    enforce_luhn = bool(cfg.get("imei_luhn", True))
    luhn_ok = luhn_validate(cleaned)

    if enforce_luhn and not luhn_ok:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "IMEI_LUHN_CHECKSUM_FAILED",
            "meta": {"source_raw": source_raw, "luhn_ok": False, "tac": cleaned[:8]},
        }

    return {
        "ok": True,
        "normalized": cleaned,
        "reason_code": "VALID_IMEI",
        "meta": {
            "source_raw": source_raw,
            "luhn_ok": luhn_ok,
            "tac": cleaned[:8],
            "serial": cleaned[8:14],
            "check_digit": cleaned[14],
        },
    }


def validate_imsi(raw: Any) -> Dict[str, Any]:
    """
    Validates a 15-digit International Mobile Subscriber Identity (IMSI, no checksum).
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    cleaned = re.sub(r"[\s\-]", "", s)
    if not cleaned:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    if not cleaned.isdigit() or len(cleaned) != 15:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_IMSI_LENGTH",
            "meta": {"source_raw": source_raw},
        }

    return {
        "ok": True,
        "normalized": cleaned,
        "reason_code": "VALID_IMSI",
        "meta": {
            "source_raw": source_raw,
            "mcc": cleaned[:3],
            "mnc_prefix": cleaned[3:6],
        },
    }


IFSC_REGEX = re.compile(r"^([A-Z]{4})0([A-Z0-9]{6})$")


def validate_ifsc(raw: Any, bank_codes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Validates Indian Financial System Code (IFSC): ^[A-Z]{4}0[A-Z0-9]{6}$
    with optional bank-code lookup from backend/config/reference/ifsc_bank_codes.json.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip().upper()
    cleaned = re.sub(r"[\s\-]", "", s)
    if not cleaned:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    m = IFSC_REGEX.match(cleaned)
    if not m:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_IFSC_FORMAT",
            "meta": {"source_raw": source_raw},
        }

    bank_prefix = m.group(1)
    branch_code = m.group(2)
    ref_codes = bank_codes if bank_codes is not None else get_ifsc_bank_codes()

    if not ref_codes:
        return {
            "ok": True,
            "normalized": cleaned,
            "reason_code": "VALID_IFSC_FORMAT_ONLY",
            "meta": {
                "source_raw": source_raw,
                "bank_code": bank_prefix,
                "branch_code": branch_code,
                "bank_name": None,
                "known_bank": None,
            },
        }

    bank_name = ref_codes.get(bank_prefix)
    return {
        "ok": True,
        "normalized": cleaned,
        "reason_code": "VALID_IFSC" if bank_name else "VALID_IFSC_UNLISTED_BANK",
        "meta": {
            "source_raw": source_raw,
            "bank_code": bank_prefix,
            "branch_code": branch_code,
            "bank_name": bank_name,
            "known_bank": bool(bank_name),
        },
    }


MASKED_DIGITS_REGEX = re.compile(r"^[X*x#\-_\s]{2,14}(\d{3,6})$")


def validate_bank_account(raw: Any) -> Dict[str, Any]:
    """
    Validates a bank account number (digit-only within configured [account_len_min, account_len_max]).
    Also provides normalized alphanumeric fallback in meta for institutional internal account codes.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    if not s:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    masked_match = MASKED_DIGITS_REGEX.match(s)
    if masked_match:
        last_digits = masked_match.group(1)
        return {
            "ok": False,
            "normalized": f"ENDING_{last_digits}",
            "reason_code": "MASKED_ACCOUNT_NUMBER",
            "meta": {"source_raw": source_raw, "is_masked": True, "last_digits": last_digits},
        }

    cleaned = re.sub(r"[\s\-]", "", s).upper()
    cfg = get_extraction_config().get("validators", {})
    min_len = int(cfg.get("account_len_min", 9))
    max_len = int(cfg.get("account_len_max", 18))

    if cleaned.isdigit():
        if min_len <= len(cleaned) <= max_len:
            return {
                "ok": True,
                "normalized": cleaned,
                "reason_code": "VALID_BANK_ACCOUNT",
                "meta": {"source_raw": source_raw, "length": len(cleaned), "is_masked": False},
            }
        return {
            "ok": False,
            "normalized": cleaned,
            "reason_code": "ACCOUNT_LENGTH_OUT_OF_BOUNDS",
            "meta": {
                "source_raw": source_raw,
                "length": len(cleaned),
                "min_len": min_len,
                "max_len": max_len,
            },
        }

    return {
        "ok": False,
        "normalized": cleaned if cleaned else None,
        "reason_code": "NON_DIGIT_ACCOUNT_IDENTIFIER",
        "meta": {"source_raw": source_raw, "is_alphanumeric": True},
    }


UPI_VPA_REGEX = re.compile(r"^([a-zA-Z0-9.\-_]{2,64})@([a-zA-Z0-9]{2,32})$")
COMMON_EMAIL_PROVIDERS = {
    "gmail", "yahoo", "outlook", "hotmail", "icloud", "rediffmail", "protonmail", "live", "msn", "aol"
}


def validate_upi_vpa(raw: Any) -> Dict[str, Any]:
    """
    Validates a UPI Virtual Payment Address (handle@psp) and splits it into handle and psp.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    if not s:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    m = UPI_VPA_REGEX.match(s)
    if not m:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "INVALID_UPI_VPA_FORMAT",
            "meta": {"source_raw": source_raw},
        }

    handle = m.group(1).lower()
    psp = m.group(2).lower()
    if psp in COMMON_EMAIL_PROVIDERS:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "EMAIL_PROVIDER_NOT_UPI_PSP",
            "meta": {"source_raw": source_raw, "handle": handle, "psp": psp},
        }

    normalized = f"{handle}@{psp}"
    return {
        "ok": True,
        "normalized": normalized,
        "reason_code": "VALID_UPI_VPA",
        "meta": {"source_raw": source_raw, "handle": handle, "psp": psp},
    }


VEHICLE_STD_REGEX = re.compile(r"^([A-Z]{2})(\d{1,2})([A-Z]{0,3})(\d{4})$")
VEHICLE_BH_REGEX = re.compile(r"^(\d{2})BH(\d{4})([A-Z]{1,2})$")
INDIAN_STATE_CODES = {
    "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN", "GA", "GJ",
    "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD", "MH", "ML", "MN", "MP",
    "MZ", "NL", "OD", "OR", "PB", "PY", "RJ", "SK", "TN", "TR", "TS", "TG",
    "UK", "UA", "UP", "WB",
}


def validate_vehicle(raw: Any) -> Dict[str, Any]:
    """
    Validates Indian vehicle registration numbers (standard state RTO or BH series)
    and extracts the state_code as metadata.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip().upper()
    cleaned = re.sub(r"[\s\-]", "", s)
    if not cleaned:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    m_std = VEHICLE_STD_REGEX.match(cleaned)
    if m_std:
        state_code, rto_num, series, serial_num = m_std.groups()
        norm_rto = rto_num.zfill(2)
        normalized = f"{state_code}{norm_rto}{series}{serial_num}"
        known_state = state_code in INDIAN_STATE_CODES
        return {
            "ok": True,
            "normalized": normalized,
            "reason_code": "VALID_VEHICLE_REGISTRATION" if known_state else "VALID_VEHICLE_UNRECOGNIZED_STATE",
            "meta": {
                "source_raw": source_raw,
                "state_code": state_code,
                "rto_code": f"{state_code}{norm_rto}",
                "series": series,
                "number": serial_num,
                "known_state_code": known_state,
            },
        }

    m_bh = VEHICLE_BH_REGEX.match(cleaned)
    if m_bh:
        reg_year, serial_num, series = m_bh.groups()
        return {
            "ok": True,
            "normalized": cleaned,
            "reason_code": "VALID_BH_SERIES_VEHICLE",
            "meta": {
                "source_raw": source_raw,
                "state_code": "BH",
                "registration_year": reg_year,
                "series": series,
                "number": serial_num,
                "known_state_code": True,
            },
        }

    return {
        "ok": False,
        "normalized": cleaned if len(cleaned) >= 6 else None,
        "reason_code": "INVALID_VEHICLE_FORMAT",
        "meta": {"source_raw": source_raw},
    }


# ---------------------------------------------------------------------------
# 4. Phone Normalization via `phonenumbers`
# ---------------------------------------------------------------------------

CARRIER_DISCLAIMER = (
    "Carrier and region info reflects original number-range allocation only and cannot "
    "prove current subscriber ownership or that a line is active."
)

_PHONE_TYPE_MAP = {
    PhoneNumberType.MOBILE: "MOBILE",
    PhoneNumberType.FIXED_LINE: "FIXED_LINE",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
    PhoneNumberType.TOLL_FREE: "TOLL_FREE",
    PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
    PhoneNumberType.SHARED_COST: "SHARED_COST",
    PhoneNumberType.VOIP: "VOIP",
    PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
    PhoneNumberType.PAGER: "PAGER",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "VOICEMAIL",
    PhoneNumberType.UNKNOWN: "UNKNOWN",
}

MASKED_PHONE_REGEX = re.compile(r"^(?:\+?91[\s\-]?)?(?:[\d]{0,4}[X*#x]{2,8}[\d]{2,5})$")


def validate_phone(raw: Any, default_region: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses and normalizes telephone / mobile numbers using `phonenumbers` with the
    configured default region (default 'IN').
      - Produces E.164 and national 10-digit form.
      - Populates valid_mobile, number_type, region, carrier_hint, is_masked, source_raw.
      - Keeps landline, short-code, SMS header, masked, and international numbers
        (flagged via valid_mobile=False and meta, never silently dropped).
      - NOTE: Carrier info reflects original allocation and cannot prove current
        ownership or that a line is active.
    """
    if raw is None:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": None}}

    source_raw = str(raw).strip()
    if not source_raw:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_INPUT", "meta": {"source_raw": source_raw}}

    s = to_ascii_digits(source_raw).strip()
    if default_region is None:
        default_region = str(get_extraction_config().get("default_region", "IN")).upper()

    # 1. Check for Masked Phone Numbers (e.g. XXXXXX1234, +91-98XXXX3210, ******4321)
    compact_mask = re.sub(r"[\s\-()]", "", s)
    if any(ch in compact_mask for ch in "Xx*#") and any(ch.isdigit() for ch in compact_mask):
        if MASKED_PHONE_REGEX.match(compact_mask) or re.search(r"[Xx*#]{2,}\d{2,6}$", compact_mask):
            trailing_digits = re.findall(r"\d+", compact_mask)
            last_part = trailing_digits[-1] if trailing_digits else compact_mask
            norm_masked = compact_mask.upper()
            return {
                "ok": True,
                "normalized": norm_masked,
                "reason_code": "MASKED_PHONE_NUMBER",
                "meta": {
                    "number": norm_masked,
                    "e164": None,
                    "national_number": last_part,
                    "valid_mobile": False,
                    "format_valid": False,
                    "kind": "masked",
                    "number_type": "MASKED",
                    "region": default_region,
                    "carrier_hint": None,
                    "location_hint": None,
                    "is_masked": True,
                    "line_status": "unverified",
                    "source_raw": source_raw,
                    "carrier_disclaimer": CARRIER_DISCLAIMER,
                },
            }

    # 2. Check for Alphanumeric SMS Sender Headers (e.g. AD-HDFCBK, VM-SBIINB)
    clean_alpha = re.sub(r"[^A-Za-z0-9]", "", s)
    if any(c.isalpha() for c in clean_alpha) and len(clean_alpha) <= 12:
        norm_header = clean_alpha.upper()
        return {
            "ok": True,
            "normalized": norm_header,
            "reason_code": "SMS_SENDER_HEADER",
            "meta": {
                "number": norm_header,
                "e164": None,
                "national_number": norm_header,
                "valid_mobile": False,
                "format_valid": True,
                "kind": "sms_header",
                "number_type": "SMS_HEADER",
                "region": default_region,
                "carrier_hint": None,
                "location_hint": None,
                "is_masked": False,
                "line_status": "unverified",
                "source_raw": source_raw,
                "carrier_disclaimer": CARRIER_DISCLAIMER,
            },
        }

    # 3. Extract digits and preserve leading '+'
    digits = re.sub(r"\D", "", s)
    if not digits:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "NO_DIGITS_FOUND",
            "meta": {"source_raw": source_raw},
        }

    # Short codes / emergency numbers (3 to 6 digits)
    if len(digits) <= 6:
        return {
            "ok": True,
            "normalized": digits,
            "reason_code": "SHORT_CODE_NUMBER",
            "meta": {
                "number": digits,
                "e164": None,
                "national_number": digits,
                "valid_mobile": False,
                "format_valid": False,
                "kind": "other",
                "number_type": "SHORT_CODE",
                "region": default_region,
                "carrier_hint": None,
                "location_hint": None,
                "is_masked": False,
                "line_status": "unverified",
                "source_raw": source_raw,
                "carrier_disclaimer": CARRIER_DISCLAIMER,
            },
        }

    # Prepare candidate string for phonenumbers
    parse_input = s
    if not s.startswith("+"):
        if default_region == "IN" and len(digits) == 12 and digits.startswith("91"):
            parse_input = f"+{digits}"
        elif default_region == "IN" and len(digits) == 11 and digits.startswith("0"):
            parse_input = digits

    try:
        parsed = phonenumbers.parse(parse_input, default_region)
        is_possible = phonenumbers.is_possible_number(parsed)
        is_valid = phonenumbers.is_valid_number(parsed)
        num_type_enum = phonenumbers.number_type(parsed)
        num_type_str = _PHONE_TYPE_MAP.get(num_type_enum, "UNKNOWN")
        region_code = phonenumbers.region_code_for_number(parsed) or default_region
        nat_str = str(parsed.national_number)
        e164_str = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164) if (is_valid or is_possible) else None

        try:
            carrier_str = carrier.name_for_number(parsed, "en") or None
        except Exception:
            carrier_str = None
        try:
            loc_str = geocoder.description_for_number(parsed, "en") or None
        except Exception:
            loc_str = None

        # In India, 10-digit numbers starting with 6,7,8,9 are mobile numbers
        is_in_mobile = (
            region_code == "IN"
            and len(nat_str) == 10
            and nat_str[0] in "6789"
            and (is_valid or num_type_enum in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE, PhoneNumberType.UNKNOWN))
        )

        if is_in_mobile and num_type_str == "UNKNOWN":
            num_type_str = "MOBILE"

        if region_code != default_region and s.startswith("+"):
            kind = "international"
            if num_type_str == "UNKNOWN":
                num_type_str = "INTERNATIONAL"
        elif is_in_mobile:
            kind = "mobile"
        elif num_type_enum == PhoneNumberType.FIXED_LINE:
            kind = "landline"
        else:
            kind = "other"

        canonical_num = nat_str if is_in_mobile else (e164_str.lstrip("+") if (kind == "international" and e164_str) else digits)

        return {
            "ok": True,
            "normalized": canonical_num,
            "reason_code": "VALID_MOBILE" if is_in_mobile else f"PARSED_{num_type_str}",
            "meta": {
                "number": canonical_num,
                "e164": e164_str,
                "national_number": nat_str,
                "valid_mobile": bool(is_in_mobile),
                "format_valid": bool(is_valid or is_in_mobile),
                "kind": kind,
                "number_type": num_type_str,
                "region": region_code,
                "carrier_hint": carrier_str,
                "location_hint": loc_str,
                "is_masked": False,
                "line_status": "unverified",
                "source_raw": source_raw,
                "carrier_disclaimer": CARRIER_DISCLAIMER,
            },
        }
    except Exception:
        # Fallback if phonenumbers cannot parse (keep raw digits, flag as other/unverified)
        norm_digits = digits
        if len(norm_digits) == 12 and norm_digits.startswith("91"):
            norm_digits = norm_digits[2:]
        elif len(norm_digits) == 11 and norm_digits.startswith("0"):
            norm_digits = norm_digits[1:]
        is_in_mob = len(norm_digits) == 10 and norm_digits[0] in "6789"
        return {
            "ok": True,
            "normalized": norm_digits,
            "reason_code": "FALLBACK_DIGIT_NORMALIZATION",
            "meta": {
                "number": norm_digits,
                "e164": f"+91{norm_digits}" if is_in_mob else None,
                "national_number": norm_digits,
                "valid_mobile": is_in_mob,
                "format_valid": is_in_mob,
                "kind": "mobile" if is_in_mob else "other",
                "number_type": "MOBILE" if is_in_mob else "UNKNOWN",
                "region": default_region,
                "carrier_hint": None,
                "location_hint": None,
                "is_masked": False,
                "line_status": "unverified",
                "source_raw": source_raw,
                "carrier_disclaimer": CARRIER_DISCLAIMER,
            },
        }


# ---------------------------------------------------------------------------
# 5. Timezone-Safe Date Parsing, Per-Column Dayfirst Inference & Curfew Helper
# ---------------------------------------------------------------------------

_SLASH_DASH_DATE_RE = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})(?:\s|$|T)")


def infer_column_dayfirst(values: List[Any], fallback_dayfirst: Optional[bool] = None) -> Tuple[bool, str]:
    """
    Infers dayfirst (DD/MM vs MM/DD) across an entire column by scanning all values:
      - If any date has 1st numeric component > 12 (and <= 31), returns (True, "inferred_dayfirst").
      - If any date has 2nd numeric component > 12 (and <= 31), returns (False, "inferred_monthfirst").
      - Otherwise returns (fallback_dayfirst, "config_fallback").
    """
    cfg_date = get_extraction_config().get("date_parse", {})
    if fallback_dayfirst is None:
        fallback_dayfirst = bool(cfg_date.get("fallback_dayfirst", True))

    if not cfg_date.get("dayfirst_inference", True):
        return fallback_dayfirst, "inference_disabled"

    saw_first_gt_12 = False
    saw_second_gt_12 = False

    for v in values or []:
        if v is None:
            continue
        s = to_ascii_digits(v).strip()
        if not s:
            continue
        m = _SLASH_DASH_DATE_RE.match(s)
        if not m:
            continue
        try:
            p1 = int(m.group(1))
            p2 = int(m.group(2))
        except ValueError:
            continue

        if 13 <= p1 <= 31 and 1 <= p2 <= 12:
            saw_first_gt_12 = True
        elif 13 <= p2 <= 31 and 1 <= p1 <= 12:
            saw_second_gt_12 = True

    if saw_first_gt_12 and not saw_second_gt_12:
        return True, "inferred_dayfirst"
    if saw_second_gt_12 and not saw_first_gt_12:
        return False, "inferred_monthfirst"
    return fallback_dayfirst, "config_fallback"


def _get_display_zoneinfo(display_tz: Optional[str] = None) -> ZoneInfo:
    tz_name = display_tz or str(get_extraction_config().get("timezone_display", "Asia/Kolkata"))
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("Asia/Kolkata")


def parse_forensic_datetime(
    raw_date: Any,
    raw_time: Any = None,
    dayfirst: Optional[bool] = None,
    default_tz: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Timezone-safe, India-aware datetime parser and validator:
      1. Converts Devanagari/Indic digits to ASCII.
      2. Parses using dayfirst (column-inferred or config fallback).
      3. Attaches Asia/Kolkata (or configured timezone_display) to naive timestamps
         with tz_source="assumed_local", or preserves explicit timezone with tz_source="explicit".
      4. Converts to UTC ISO-8601 ('YYYY-MM-DDTHH:MM:SSZ') for storage while keeping
         local display date/time in metadata.
      5. Never invents a fake fallback date on invalid input (returns ok=False).
    """
    cfg_ext = get_extraction_config()
    cfg_date = cfg_ext.get("date_parse", {})
    if dayfirst is None:
        dayfirst = bool(cfg_date.get("fallback_dayfirst", True))

    local_zi = _get_display_zoneinfo(default_tz)
    tz_name = getattr(local_zi, "key", str(local_zi))

    dt_obj: Optional[datetime] = None
    tz_source = "assumed_local"

    if isinstance(raw_date, datetime):
        dt_obj = raw_date
        if dt_obj.tzinfo is not None and dt_obj.tzinfo.utcoffset(dt_obj) is not None:
            tz_source = "explicit"
    elif isinstance(raw_date, date):
        dt_obj = datetime.combine(raw_date, time(0, 0, 0))

    if dt_obj is None and raw_date is not None:
        s = to_ascii_digits(raw_date).strip()
        if s and s.lower() not in {"nan", "null", "none", "-", "n/a"}:
            # Check if string carries explicit timezone marker (Z or +/-HH:MM)
            has_explicit_tz = bool(
                s.endswith("Z")
                or s.endswith("z")
                or re.search(r"[+-]\d{2}:?\d{2}$", s)
            )
            if has_explicit_tz:
                tz_source = "explicit"
                try:
                    dt_obj = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
                except Exception:
                    try:
                        dt_obj = dt_parser.parse(s, dayfirst=dayfirst)
                    except Exception:
                        dt_obj = None
            else:
                # Choose format order based on dayfirst preference
                dmy_formats = [
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y %H:%M",
                    "%d/%m/%Y",
                    "%d-%m-%Y %H:%M:%S",
                    "%d-%m-%Y %H:%M",
                    "%d-%m-%Y",
                    "%d.%m.%Y %H:%M:%S",
                    "%d.%m.%Y",
                    "%d/%m/%y %H:%M:%S",
                    "%d/%m/%y",
                    "%d-%m-%y",
                ]
                mdy_formats = [
                    "%m/%d/%Y %H:%M:%S",
                    "%m/%d/%Y %H:%M",
                    "%m/%d/%Y",
                    "%m-%d-%Y %H:%M:%S",
                    "%m-%d-%Y %H:%M",
                    "%m-%d-%Y",
                    "%m/%d/%y %H:%M:%S",
                    "%m/%d/%y",
                    "%m-%d-%y",
                ]
                iso_and_named_formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M",
                    "%Y-%m-%d",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y/%m/%d",
                    "%d-%b-%Y %H:%M:%S",
                    "%d-%b-%Y",
                    "%d %b %Y %H:%M:%S",
                    "%d %b %Y",
                    "%d %B %Y",
                    "%d-%b-%y",
                ]
                ordered_formats = (
                    iso_and_named_formats + (dmy_formats + mdy_formats if dayfirst else mdy_formats + dmy_formats)
                )
                for fmt in ordered_formats:
                    try:
                        dt_obj = datetime.strptime(s, fmt)
                        break
                    except ValueError:
                        continue

                if dt_obj is None:
                    try:
                        # Avoid dateutil inventing dates from bare numbers without separators
                        if re.search(r"[/\-.\s:]", s):
                            dt_obj = dt_parser.parse(s, dayfirst=dayfirst)
                            if dt_obj.tzinfo is not None and dt_obj.tzinfo.utcoffset(dt_obj) is not None:
                                tz_source = "explicit"
                    except Exception:
                        dt_obj = None

    if dt_obj is None:
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "UNPARSABLE_DATETIME",
            "meta": {"source_raw_date": raw_date, "source_raw_time": raw_time},
        }

    # Attach separate raw_time if provided and dt_obj has no time component yet
    if raw_time is not None and not (
        isinstance(raw_date, datetime) and (dt_obj.hour != 0 or dt_obj.minute != 0 or dt_obj.second != 0)
    ):
        ts = to_ascii_digits(raw_time).strip()
        if ts and ts.lower() not in {"nan", "null", "none", "-"}:
            t_val: Optional[time] = None
            for t_fmt in ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]:
                try:
                    t_val = datetime.strptime(ts, t_fmt).time()
                    break
                except ValueError:
                    continue
            if t_val is None:
                try:
                    t_val = dt_parser.parse(ts).time()
                except Exception:
                    t_val = None
            if t_val is not None:
                orig_tz = dt_obj.tzinfo
                dt_obj = datetime.combine(dt_obj.date(), t_val)
                if orig_tz is not None:
                    dt_obj = dt_obj.replace(tzinfo=orig_tz)

    # Attach display timezone if naive, then compute both local display and UTC timestamps
    if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) is None:
        tz_source = "assumed_local"
        local_dt = dt_obj.replace(tzinfo=local_zi)
    else:
        tz_source = "explicit"
        local_dt = dt_obj.astimezone(local_zi)

    utc_dt = local_dt.astimezone(timezone.utc)
    local_date_str = local_dt.strftime("%Y-%m-%d")
    local_time_str = local_dt.strftime("%H:%M:%S")
    local_iso_str = local_dt.isoformat()
    utc_iso_str = utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "ok": True,
        "normalized": utc_iso_str,
        "reason_code": "VALID_DATETIME",
        "meta": {
            "local_date": local_date_str,
            "local_time": local_time_str,
            "local_iso": local_iso_str,
            "utc_iso": utc_iso_str,
            "tz_source": tz_source,
            "timezone_display": tz_name,
            "dayfirst_used": dayfirst,
        },
    }


def utc_to_display_tz(iso_or_dt: Any, display_tz: Optional[str] = None) -> Optional[datetime]:
    """
    Converts a stored UTC ISO-8601 timestamp (e.g. '2026-08-14T20:00:00Z') or datetime
    back into the configured display timezone (default 'Asia/Kolkata').
    If a naive timestamp without 'Z' or offset is passed, it is interpreted in display_tz.
    """
    if iso_or_dt is None:
        return None
    local_zi = _get_display_zoneinfo(display_tz)

    if isinstance(iso_or_dt, datetime):
        if iso_or_dt.tzinfo is None or iso_or_dt.tzinfo.utcoffset(iso_or_dt) is None:
            return iso_or_dt.replace(tzinfo=local_zi)
        return iso_or_dt.astimezone(local_zi)

    if isinstance(iso_or_dt, date):
        return datetime.combine(iso_or_dt, time(0, 0, 0), tzinfo=local_zi)

    s = to_ascii_digits(iso_or_dt).strip()
    if not s:
        return None

    has_explicit_tz = bool(
        s.endswith("Z")
        or s.endswith("z")
        or re.search(r"[+-]\d{2}:?\d{2}$", s)
    )
    if has_explicit_tz:
        try:
            aware_dt = datetime.fromisoformat(s.replace("Z", "+00:00").replace("z", "+00:00"))
            return aware_dt.astimezone(local_zi)
        except Exception:
            try:
                aware_dt = dt_parser.parse(s)
                if aware_dt.tzinfo is None:
                    aware_dt = aware_dt.replace(tzinfo=timezone.utc)
                return aware_dt.astimezone(local_zi)
            except Exception:
                return None

    # Naive string: parse and attach local_zi
    for fmt in [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]:
        try:
            naive_dt = datetime.strptime(s, fmt)
            return naive_dt.replace(tzinfo=local_zi)
        except ValueError:
            continue

    try:
        parsed_dt = dt_parser.parse(s)
        if parsed_dt.tzinfo is None:
            return parsed_dt.replace(tzinfo=local_zi)
        return parsed_dt.astimezone(local_zi)
    except Exception:
        return None


def is_curfew_hour(
    iso_or_dt: Any,
    display_tz: Optional[str] = None,
    start_hour: Optional[int] = None,
    end_hour: Optional[int] = None,
) -> bool:
    """
    Returns True if the given UTC or local timestamp falls inside the nocturnal/curfew
    window [start_hour, end_hour) in the configured display timezone (default 00:00-05:00 IST).
    Specifically:
      - 00:00:00 IST -> True (inside curfew)
      - 04:59:59 IST -> True (inside curfew)
      - 05:00:00 IST -> False (curfew ended at 05:00)
    """
    local_dt = utc_to_display_tz(iso_or_dt, display_tz=display_tz)
    if local_dt is None:
        return False

    curfew_cfg = get_extraction_config().get("curfew_hours", {})
    s_hr = int(curfew_cfg.get("start_hour", 0)) if start_hour is None else int(start_hour)
    e_hr = int(curfew_cfg.get("end_hour", 5)) if end_hour is None else int(end_hour)

    h = local_dt.hour
    if s_hr < e_hr:
        return s_hr <= h < e_hr
    # Wrap-around window (e.g. 23 to 5)
    return h >= s_hr or h < e_hr


# ---------------------------------------------------------------------------
# 6. Exact DecimalPaise Amount Validator
# ---------------------------------------------------------------------------

def validate_amount(raw: Any, dr_cr_indicator: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses currency amounts into integer PAISE using exact Decimal arithmetic (never float).
      - Converts Devanagari/Indic digits to ASCII.
      - Handles accounting bracket negatives '(1,200.50)' when allow_bracket_negative is enabled.
      - Handles 'Cr'/'Dr' suffix or separate dr_cr_indicator column.
      - Handles Indian lakh/crore comma grouping and multiplier words ('lakh', 'lac', 'crore', 'cr').
      - Strips currency symbols (₹, Rs., INR, /-).
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    if not s or s.lower() in {"nan", "null", "none", "-", "nil"}:
        return {"ok": False, "normalized": None, "reason_code": "EMPTY_OR_NULL_AMOUNT", "meta": {"source_raw": source_raw}}

    cfg_amt = get_extraction_config().get("amount", {})
    allow_brackets = bool(cfg_amt.get("allow_bracket_negative", True))
    allow_indian = bool(cfg_amt.get("indian_grouping", True))

    is_negative = False
    direction_hint: Optional[str] = None

    if allow_brackets and s.startswith("(") and s.endswith(")"):
        is_negative = True
        direction_hint = "debit"
        s = s[1:-1].strip()

    s_lower = s.lower()

    multiplier = Decimal(1)
    if allow_indian:
        if re.search(r"\b(?:crores?|cr\.?)\b", s_lower) and not re.search(r"\d\s*cr\.?\s*$", s_lower):
            multiplier = Decimal(10000000)
        elif "crore" in s_lower or re.search(r"\d(?:\.\d+)?\s+cr\b", s_lower):
            # Distinguish '1.5 cr' (crore) vs '1,200.00 Cr' (credit indicator)
            # If number is small (< 1000) and has 'cr' after space without decimals like .00, check context
            if "crore" in s_lower or re.search(r"\b\d+(?:\.\d+)?\s*cr\s*(?:rupees|inr|rs|\/-)", s_lower) or (
                not re.search(r"\.\d{2}\s*cr\.?$", s_lower) and "," not in s_lower
            ):
                multiplier = Decimal(10000000)
        elif re.search(r"\b(?:lakhs?|lacs?)\b", s_lower):
            multiplier = Decimal(100000)

    # Check Cr / Dr accounting suffix when multiplier is 1
    if multiplier == Decimal(1):
        if re.search(r"(?:\b|\d)\s*(?:dr\.?|debit)\s*$", s_lower):
            is_negative = True
            direction_hint = "debit"
        elif re.search(r"(?:\b|\d)\s*(?:cr\.?|credit)\s*$", s_lower):
            direction_hint = "credit"

    # Separate Cr/Dr column override
    if dr_cr_indicator is not None:
        ind = to_ascii_digits(dr_cr_indicator).strip().lower()
        if ind in {"dr", "dr.", "debit", "d", "withdrawal", "out"}:
            is_negative = True
            direction_hint = "debit"
        elif ind in {"cr", "cr.", "credit", "c", "deposit", "in"}:
            is_negative = False
            direction_hint = "credit"

    # Strip currency symbols, words, and trailing '/-'
    s_cleaned = re.sub(
        r"[₹$€£\s]|rs\.?|inr|cash|rupees|lakhs?|lacs?|crores?|cr\.?|dr\.?|debit|credit|\/-|\/",
        "",
        s,
        flags=re.IGNORECASE,
    )
    s_cleaned = s_cleaned.replace(",", "")

    # Must match a clean decimal number (reject strings with multiple dots or extra junk)
    if not re.fullmatch(r"[-+]?(?:\d+\.?\d*|\.\d+)", s_cleaned):
        num_match = re.search(r"[-+]?(?:\d+\.?\d*|\.\d+)", s_cleaned)
        if not num_match:
            return {
                "ok": False,
                "normalized": None,
                "reason_code": "INVALID_AMOUNT_FORMAT",
                "meta": {"source_raw": source_raw},
            }
        num_token = num_match.group(0)
    else:
        num_token = s_cleaned

    try:
        dec_val = Decimal(num_token) * multiplier
        if dec_val < 0:
            is_negative = True
        if is_negative:
            dec_val = -abs(dec_val)
        paise = int((dec_val * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return {
            "ok": True,
            "normalized": paise,
            "reason_code": "VALID_AMOUNT_PAISE",
            "meta": {
                "source_raw": source_raw,
                "amount_paise": paise,
                "is_negative": paise < 0,
                "direction_hint": direction_hint,
                "multiplier_applied": int(multiplier),
            },
        }
    except (InvalidOperation, ValueError):
        return {
            "ok": False,
            "normalized": None,
            "reason_code": "DECIMAL_CONVERSION_FAILED",
            "meta": {"source_raw": source_raw},
        }


# ---------------------------------------------------------------------------
# 7. Context-Aware Numeric Identifier Disambiguation
# ---------------------------------------------------------------------------

_ACCOUNT_CONTEXT_RE = re.compile(
    r"\b(?:account(?:\s*no\.?)?|a/c(?:\s*no\.?)?|acct|beneficiary|remitter|saving|current|ifsc|branch|bank\s*a/c|ac[_\s]?no)\b",
    re.IGNORECASE,
)
_PHONE_CONTEXT_RE = re.compile(
    r"\b(?:mobile|phone|msisdn|cell|caller|receiver|callee|calling|called|contact|sim|whatsapp|tel|mob|b[\-_]?party|a[\-_]?party)\b",
    re.IGNORECASE,
)
_AADHAAR_CONTEXT_RE = re.compile(
    r"\b(?:aadhaar|aadhar|uid|uidai|unique\s*id)\b",
    re.IGNORECASE,
)
_IMEI_CONTEXT_RE = re.compile(
    r"\b(?:imei|handset|device\s*id|equipment)\b",
    re.IGNORECASE,
)
_IMSI_CONTEXT_RE = re.compile(
    r"\b(?:imsi|subscriber\s*id)\b",
    re.IGNORECASE,
)


def classify_numeric_identifier(
    raw: Any,
    context: str = "",
    column_header: str = "",
) -> Dict[str, Any]:
    """
    Context-aware disambiguation when a 10/12/15-digit number could be
    PHONE vs BANK_ACCOUNT vs AADHAAR vs IMEI vs IMSI.
    Uses:
      (a) column header / context words ('A/c', 'Mob', 'UID', 'IMEI'),
      (b) validators (Verhoeff for Aadhaar, Luhn for IMEI, phonenumbers for mobile),
      (c) digit length.
    If still ambiguous, stores candidate_types with confidence and sets needs_review=True
    instead of guessing silently.
    """
    source_raw = "" if raw is None else str(raw)
    s = to_ascii_digits(source_raw).strip()
    digits = re.sub(r"\D", "", s)
    combined_ctx = f"{column_header or ''} {context or ''}".strip()

    has_acc_ctx = bool(_ACCOUNT_CONTEXT_RE.search(combined_ctx))
    has_ph_ctx = bool(_PHONE_CONTEXT_RE.search(combined_ctx))
    has_uid_ctx = bool(_AADHAAR_CONTEXT_RE.search(combined_ctx))
    has_imei_ctx = bool(_IMEI_CONTEXT_RE.search(combined_ctx))
    has_imsi_ctx = bool(_IMSI_CONTEXT_RE.search(combined_ctx))

    # Strip +91 / 91 prefix ONLY when phone context is present or explicit +91 is written
    explicit_plus91 = bool(re.match(r"^\+?91[\s\-]\d{5}[\s\-]?\d{5}$", s) or s.startswith("+91"))
    ten_digit_from_91 = digits[2:] if (len(digits) == 12 and digits.startswith("91") and (explicit_plus91 or has_ph_ctx)) else None

    candidates: List[Dict[str, Any]] = []

    # Case A: 10-digit number (or +91 10-digit) -> PHONE vs BANK_ACCOUNT
    if len(digits) == 10 or ten_digit_from_91:
        d10 = ten_digit_from_91 or digits
        ph_res = validate_phone(s)
        acc_res = validate_bank_account(d10)

        if has_acc_ctx and not has_ph_ctx and not s.startswith("+"):
            candidates.append({"type": "BANK_ACCOUNT", "confidence": 0.92, "normalized": d10})
            if ph_res["meta"].get("valid_mobile"):
                candidates.append({"type": "PHONE", "confidence": 0.25, "normalized": ph_res["normalized"]})
            return {
                "ok": True,
                "entity_type": "BANK_ACCOUNT",
                "normalized": d10,
                "confidence": 0.92,
                "needs_review": False,
                "candidate_types": candidates,
                "reason_code": "CONTEXT_ACCOUNT_KEYWORD",
            }

        if (has_ph_ctx or explicit_plus91) and not has_acc_ctx and ph_res["meta"].get("valid_mobile"):
            candidates.append({"type": "PHONE", "confidence": 0.95, "normalized": ph_res["normalized"]})
            if acc_res["ok"]:
                candidates.append({"type": "BANK_ACCOUNT", "confidence": 0.20, "normalized": d10})
            return {
                "ok": True,
                "entity_type": "PHONE",
                "normalized": ph_res["normalized"],
                "confidence": 0.95,
                "needs_review": False,
                "candidate_types": candidates,
                "reason_code": "CONTEXT_PHONE_KEYWORD",
            }

        # Both or neither context present:
        if has_acc_ctx and has_ph_ctx:
            candidates = [
                {"type": "PHONE", "confidence": 0.55, "normalized": ph_res["normalized"]},
                {"type": "BANK_ACCOUNT", "confidence": 0.55, "normalized": d10},
            ]
            return {
                "ok": True,
                "entity_type": "PHONE" if explicit_plus91 else "BANK_ACCOUNT",
                "normalized": ph_res["normalized"] if explicit_plus91 else d10,
                "confidence": 0.55,
                "needs_review": True,
                "candidate_types": candidates,
                "reason_code": "AMBIGUOUS_PHONE_OR_ACCOUNT_CONTEXT",
            }

        # Neutral context on 10-digit number
        if ph_res["meta"].get("valid_mobile"):
            candidates = [
                {"type": "PHONE", "confidence": 0.80, "normalized": ph_res["normalized"]},
                {"type": "BANK_ACCOUNT", "confidence": 0.45, "normalized": d10},
            ]
            return {
                "ok": True,
                "entity_type": "PHONE",
                "normalized": ph_res["normalized"],
                "confidence": 0.80,
                "needs_review": True,
                "candidate_types": candidates,
                "reason_code": "NEUTRAL_10_DIGIT_MOBILE_VS_ACCOUNT",
            }

        if acc_res["ok"]:
            return {
                "ok": True,
                "entity_type": "BANK_ACCOUNT",
                "normalized": acc_res["normalized"],
                "confidence": 0.85,
                "needs_review": False,
                "candidate_types": [{"type": "BANK_ACCOUNT", "confidence": 0.85, "normalized": acc_res["normalized"]}],
                "reason_code": "NON_MOBILE_10_DIGIT_ACCOUNT",
            }

    # Case B: 12-digit number -> AADHAAR vs BANK_ACCOUNT
    if len(digits) == 12:
        uid_res = validate_aadhaar(digits)
        acc_res = validate_bank_account(digits)

        if has_uid_ctx and uid_res["ok"]:
            return {
                "ok": True,
                "entity_type": "AADHAAR",
                "normalized": uid_res["normalized"],
                "confidence": 0.96,
                "needs_review": False,
                "candidate_types": [{"type": "AADHAAR", "confidence": 0.96, "normalized": uid_res["normalized"]}],
                "reason_code": "CONTEXT_AND_VERHOEFF_AADHAAR",
            }

        if has_acc_ctx and not has_uid_ctx:
            candidates = [{"type": "BANK_ACCOUNT", "confidence": 0.90, "normalized": digits}]
            if uid_res["ok"]:
                candidates.append({"type": "AADHAAR", "confidence": 0.35, "normalized": digits})
            return {
                "ok": True,
                "entity_type": "BANK_ACCOUNT",
                "normalized": digits,
                "confidence": 0.90,
                "needs_review": False,
                "candidate_types": candidates,
                "reason_code": "CONTEXT_ACCOUNT_12_DIGIT",
            }

        if uid_res["ok"] and acc_res["ok"]:
            # Passes Verhoeff in neutral context: could be Aadhaar or 12-digit Bank Account!
            candidates = [
                {"type": "AADHAAR", "confidence": 0.70, "normalized": digits},
                {"type": "BANK_ACCOUNT", "confidence": 0.60, "normalized": digits},
            ]
            return {
                "ok": True,
                "entity_type": "AADHAAR",
                "normalized": digits,
                "confidence": 0.70,
                "needs_review": True,
                "candidate_types": candidates,
                "reason_code": "AMBIGUOUS_12_DIGIT_AADHAAR_VS_ACCOUNT",
            }

        if acc_res["ok"]:
            return {
                "ok": True,
                "entity_type": "BANK_ACCOUNT",
                "normalized": digits,
                "confidence": 0.85,
                "needs_review": False,
                "candidate_types": [{"type": "BANK_ACCOUNT", "confidence": 0.85, "normalized": digits}],
                "reason_code": "VERHOEFF_FAILED_12_DIGIT_ACCOUNT",
            }

    # Case C: 15-digit number -> IMEI vs IMSI vs BANK_ACCOUNT
    if len(digits) == 15:
        imei_res = validate_imei(digits)
        imsi_res = validate_imsi(digits)
        acc_res = validate_bank_account(digits)

        if has_imei_ctx and imei_res["ok"]:
            return {
                "ok": True,
                "entity_type": "IMEI",
                "normalized": digits,
                "confidence": 0.96,
                "needs_review": False,
                "candidate_types": [{"type": "IMEI", "confidence": 0.96, "normalized": digits}],
                "reason_code": "CONTEXT_AND_LUHN_IMEI",
            }
        if has_imsi_ctx and imsi_res["ok"]:
            return {
                "ok": True,
                "entity_type": "IMSI",
                "normalized": digits,
                "confidence": 0.92,
                "needs_review": False,
                "candidate_types": [{"type": "IMSI", "confidence": 0.92, "normalized": digits}],
                "reason_code": "CONTEXT_IMSI",
            }
        if has_acc_ctx:
            return {
                "ok": True,
                "entity_type": "BANK_ACCOUNT",
                "normalized": digits,
                "confidence": 0.90,
                "needs_review": False,
                "candidate_types": [{"type": "BANK_ACCOUNT", "confidence": 0.90, "normalized": digits}],
                "reason_code": "CONTEXT_ACCOUNT_15_DIGIT",
            }
        if imei_res["ok"]:
            candidates = [
                {"type": "IMEI", "confidence": 0.78, "normalized": digits},
                {"type": "BANK_ACCOUNT", "confidence": 0.50, "normalized": digits},
            ]
            return {
                "ok": True,
                "entity_type": "IMEI",
                "normalized": digits,
                "confidence": 0.78,
                "needs_review": True,
                "candidate_types": candidates,
                "reason_code": "AMBIGUOUS_15_DIGIT_IMEI_VS_ACCOUNT",
            }

    # Default: check bank account bounds
    acc_res = validate_bank_account(digits)
    if acc_res["ok"]:
        return {
            "ok": True,
            "entity_type": "BANK_ACCOUNT",
            "normalized": acc_res["normalized"],
            "confidence": 0.85,
            "needs_review": False,
            "candidate_types": [{"type": "BANK_ACCOUNT", "confidence": 0.85, "normalized": acc_res["normalized"]}],
            "reason_code": "BANK_ACCOUNT_BY_LENGTH",
        }

    return {
        "ok": False,
        "entity_type": "UNKNOWN",
        "normalized": digits or s,
        "confidence": 0.0,
        "needs_review": True,
        "candidate_types": [],
        "reason_code": "UNCLASSIFIED_NUMERIC_STRING",
    }

