import re
import ipaddress
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple, Dict, Any, List

from backend.app.services.ingestion.validators import (
    to_ascii_digits,
    validate_phone,
    validate_bank_account,
    validate_amount,
    validate_vehicle,
    validate_aadhaar,
    validate_pan,
    validate_imei,
    validate_imsi,
    validate_ifsc,
    validate_upi_vpa,
    infer_column_dayfirst,
    parse_forensic_datetime,
    utc_to_display_tz,
    is_curfew_hour,
    classify_numeric_identifier,
)

TITLE_PREFIXES = re.compile(r"^(mr\.|mrs\.|ms\.|shri|smt\.|dr\.|adv\.|mohd\.|md\.)\s+", re.IGNORECASE)


def normalize_phone(raw: Any, default_region: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Normalizes telephone / mobile numbers by delegating to `validators.validate_phone` (`phonenumbers`).
    Returns a dictionary containing both backward-compatible keys (`number`, `valid_mobile`, `kind`)
    and Extraction V2 metadata (`e164`, `national_number`, `number_type`, `region`, `carrier_hint`,
    `is_masked`, `source_raw`, `line_status`, `carrier_disclaimer`).
    Note: Carrier metadata reflects original allocation and cannot prove current ownership or active status.
    """
    res = validate_phone(raw, default_region=default_region)
    if not res["ok"] or not res["normalized"]:
        return None
    meta = res["meta"]
    return {
        "number": res["normalized"],
        "valid_mobile": meta.get("valid_mobile", False),
        "kind": meta.get("kind", "other"),
        "e164": meta.get("e164"),
        "national_number": meta.get("national_number"),
        "format_valid": meta.get("format_valid", False),
        "number_type": meta.get("number_type", "UNKNOWN"),
        "region": meta.get("region"),
        "carrier_hint": meta.get("carrier_hint"),
        "location_hint": meta.get("location_hint"),
        "is_masked": meta.get("is_masked", False),
        "line_status": meta.get("line_status", "unverified"),
        "source_raw": meta.get("source_raw"),
        "carrier_disclaimer": meta.get("carrier_disclaimer"),
        "reason_code": res["reason_code"],
    }


def normalize_account(raw: Any) -> Optional[str]:
    """
    Normalizes bank account identifier via `validators.validate_bank_account` and `to_ascii_digits`.
    Trims, converts Unicode digits to ASCII, converts to uppercase, removes spaces and hyphens.
    """
    if raw is None:
        return None
    res = validate_bank_account(raw)
    if res["normalized"]:
        return res["normalized"]
    s = to_ascii_digits(raw).strip()
    if not s:
        return None
    cleaned = re.sub(r"[\s\-]", "", s).upper()
    return cleaned if cleaned else None


def normalize_amount(raw: Any, dr_cr_indicator: Optional[str] = None) -> Optional[int]:
    """
    Parses currency amounts into integer PAISE using Decimal via `validators.validate_amount` (NEVER float).
    1 Rupee = 100 Paise.
    Handles Devanagari digits, Indian formatted numbers ('5,00,000.00'), units ('38.5 lakh', '1.8 crore'),
    accounting negatives ('(1,200)'), Cr/Dr indicators, and currency symbols (Rs., INR, ₹, /-).
    """
    res = validate_amount(raw, dr_cr_indicator=dr_cr_indicator)
    if not res["ok"]:
        return None
    return res["normalized"]


def normalize_duration(raw: Any) -> int:
    """
    Normalizes call duration into integer seconds using Decimal (never float).
    Supports Devanagari/Indic digits, integer seconds, 'mm:ss', or 'hh:mm:ss'.
    """
    if raw is None:
        return 0
    s = to_ascii_digits(raw).strip()
    if not s:
        return 0

    if ":" in s:
        parts = s.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            return 0

    try:
        return int(Decimal(s))
    except (InvalidOperation, ValueError):
        return 0


def normalize_datetime(
    raw_date: Any,
    raw_time: Any = None,
    dayfirst: Optional[bool] = None,
    default_tz: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Parses date and time via `validators.parse_forensic_datetime` into:
      (local_date 'YYYY-MM-DD', local_time 'HH:MM:SS', utc_iso 'YYYY-MM-DDTHH:MM:SSZ').
    Attaches configured display timezone (default Asia/Kolkata) to naive timestamps and converts
    to UTC ISO-8601 for storage. Returns ('', '', '') if unparsable (never invents a fake date).
    """
    res = parse_forensic_datetime(raw_date, raw_time=raw_time, dayfirst=dayfirst, default_tz=default_tz)
    if not res["ok"]:
        return "", "", ""
    meta = res["meta"]
    return meta["local_date"], meta["local_time"], meta["utc_iso"]


def normalize_datetime_detailed(
    raw_date: Any,
    raw_time: Any = None,
    dayfirst: Optional[bool] = None,
    default_tz: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns full structured datetime parse result including `tz_source` ('assumed_local' vs 'explicit'),
    `utc_iso`, `local_date`, `local_time`, `local_iso`, and `dayfirst_used`.
    """
    return parse_forensic_datetime(raw_date, raw_time=raw_time, dayfirst=dayfirst, default_tz=default_tz)


def normalize_name(raw: Any) -> Tuple[str, str]:
    """
    Returns (clean_original, normalized_canonical).
    Canonical form: lowercase, stripped honorific titles, collapsed whitespace.
    """
    if raw is None:
        return "", ""
    orig = str(raw).strip()
    canon = TITLE_PREFIXES.sub("", orig)
    canon = re.sub(r"[^\w\s]", "", canon)
    canon = re.sub(r"\s+", " ", canon).strip().lower()
    return orig, canon


def normalize_vehicle(raw: Any) -> Optional[str]:
    """Normalizes Indian vehicle registration (DL01AB1234) via `validators.validate_vehicle`."""
    if raw is None:
        return None
    res = validate_vehicle(raw)
    return res["normalized"]


def normalize_email(raw: Any) -> Optional[str]:
    """Normalizes email address."""
    if raw is None:
        return None
    s = to_ascii_digits(raw).strip().lower()
    if "@" in s and "." in s.split("@")[-1]:
        return s
    return None


def normalize_ip(raw: Any) -> Tuple[Optional[str], bool]:
    """Validates IPv4 or IPv6 address (converts Indic digits first)."""
    if raw is None:
        return None, False
    s = to_ascii_digits(raw).strip()
    try:
        ip_obj = ipaddress.ip_address(s)
        return str(ip_obj), True
    except ValueError:
        return s, False


__all__ = [
    "normalize_phone",
    "normalize_account",
    "normalize_amount",
    "normalize_duration",
    "normalize_datetime",
    "normalize_datetime_detailed",
    "normalize_name",
    "normalize_vehicle",
    "normalize_email",
    "normalize_ip",
    "to_ascii_digits",
    "validate_phone",
    "validate_bank_account",
    "validate_amount",
    "validate_vehicle",
    "validate_aadhaar",
    "validate_pan",
    "validate_imei",
    "validate_imsi",
    "validate_ifsc",
    "validate_upi_vpa",
    "infer_column_dayfirst",
    "parse_forensic_datetime",
    "utc_to_display_tz",
    "is_curfew_hour",
    "classify_numeric_identifier",
]
