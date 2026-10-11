import re
import ipaddress
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time
from typing import Optional, Tuple, Dict, Any

TITLE_PREFIXES = re.compile(r"^(mr\.|mrs\.|ms\.|shri|smt\.|dr\.|adv\.)\s+", re.IGNORECASE)

def normalize_phone(raw: Any) -> Optional[Dict[str, Any]]:
    """
    Normalizes telephone / mobile numbers.
    Rules:
      - Strips non-alphanumeric characters.
      - If starts with +91 or 91 (12 digits), strips leading country code.
      - If starts with 0 (11 digits), strips leading 0.
      - Valid mobile = 10 digits starting with 6, 7, 8, 9.
      - Landlines, toll-free, short-codes kept with valid_mobile=False.
      - Alphanumeric sender IDs (e.g., AD-HDFCBK) classified as sms_header.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # Check for alphanumeric SMS headers
    clean_alpha = re.sub(r"[^A-Za-z0-9]", "", s)
    if any(c.isalpha() for c in clean_alpha) and len(clean_alpha) <= 12:
        return {
            "number": clean_alpha.upper(),
            "valid_mobile": False,
            "kind": "sms_header"
        }

    # Digits only
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None

    # Strip Indian country code or trunk 0
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    is_valid_mobile = (len(digits) == 10 and digits[0] in "6789")

    return {
        "number": digits,
        "valid_mobile": is_valid_mobile,
        "kind": "mobile" if is_valid_mobile else "other"
    }

def normalize_account(raw: Any) -> Optional[str]:
    """
    Normalizes bank account identifier.
    Trims, converts to uppercase, removes spaces and hyphens.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    cleaned = re.sub(r"[\s\-]", "", s).upper()
    return cleaned if cleaned else None

def normalize_amount(raw: Any) -> Optional[int]:
    """
    Parses currency amounts into integer PAISE using Decimal (NEVER float).
    1 Rupee = 100 Paise.
    Handles Indian formatted numbers ('5,00,000.00'), units ('38.5 lakh', '1.8 crore'),
    accounting negatives ('(1,200)'), currency symbols (Rs., INR, ₹, /-).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in ["nan", "null", "none", "-"]:
        return None

    # Check negative in accounting format (1,200)
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()

    s_lower = s.lower()

    # Detect Indian financial multiplier units
    multiplier = Decimal(1)
    if "crore" in s_lower or " cr" in s_lower:
        multiplier = Decimal(10000000)
    elif "lakh" in s_lower or "lac" in s_lower:
        multiplier = Decimal(100000)

    # Check accounting Dr / Cr indicator if not a crore multiplier
    if multiplier == Decimal(1) and s_lower.endswith("dr"):
        is_negative = True

    # Strip currency words, symbols, and trailing slashes
    s_cleaned = re.sub(r"[₹$€£\s]|rs\.?|inr|cash|rupees|lakh|lac|crore|cr|dr|\/-|\/", "", s, flags=re.IGNORECASE)
    # Remove commas
    s_cleaned = s_cleaned.replace(",", "")

    # Extract first valid numeric float/int from the cleaned string
    num_match = re.search(r"[-+]?\d*\.?\d+", s_cleaned)
    if not num_match:
        return None

    try:
        d = Decimal(num_match.group(0)) * multiplier
        if is_negative:
            d = -abs(d)
        # Convert to paise
        paise = int((d * Decimal(100)).quantize(Decimal("1")))
        return paise
    except (InvalidOperation, ValueError):
        return None

def normalize_duration(raw: Any) -> int:
    """
    Normalizes call duration into integer seconds.
    Supports integer seconds, 'mm:ss', or 'hh:mm:ss'.
    """
    if raw is None:
        return 0
    s = str(raw).strip()
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
        return int(float(s))
    except ValueError:
        return 0

def normalize_datetime(raw_date: Any, raw_time: Any = None, dayfirst: bool = True) -> Tuple[str, str, str]:
    """
    Parses date and time into: (YYYY-MM-DD, HH:MM:SS, ISO-8601).
    Handles dd/mm/yyyy, yyyy-mm-dd, Excel timestamps, combined strings.
    """
    dt_obj = None

    # Already datetime
    if isinstance(raw_date, datetime):
        dt_obj = raw_date
    elif isinstance(raw_date, date):
        dt_obj = datetime.combine(raw_date, time(0, 0, 0))

    if dt_obj is None and raw_date is not None:
        s = str(raw_date).strip()
        if s:
            # First try fast common Indian & ISO formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M",
                "%d/%m/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%d-%b-%Y",
                "%d-%b-%Y %H:%M:%S",
                "%d-%b-%y",
                "%d/%m/%y",
                "%d-%m-%y"
            ]:
                try:
                    dt_obj = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue

            # Fallback to dateutil universal parser
            if dt_obj is None:
                try:
                    from dateutil import parser as dt_parser
                    dt_obj = dt_parser.parse(s, dayfirst=dayfirst)
                except Exception:
                    pass

    # Fallback to default if unparsable
    if dt_obj is None:
        dt_obj = datetime(2026, 1, 1, 0, 0, 0)

    # Attach separate time if provided
    if raw_time is not None and not (isinstance(raw_date, datetime) and (dt_obj.hour != 0 or dt_obj.minute != 0)):
        ts = str(raw_time).strip()
        if ts:
            for t_fmt in ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"]:
                try:
                    t_val = datetime.strptime(ts, t_fmt).time()
                    dt_obj = datetime.combine(dt_obj.date(), t_val)
                    break
                except ValueError:
                    continue
            else:
                try:
                    from dateutil import parser as dt_parser
                    t_parsed = dt_parser.parse(ts).time()
                    dt_obj = datetime.combine(dt_obj.date(), t_parsed)
                except Exception:
                    pass

    d_str = dt_obj.strftime("%Y-%m-%d")
    t_str = dt_obj.strftime("%H:%M:%S")
    iso_str = f"{d_str}T{t_str}Z"
    return d_str, t_str, iso_str

def normalize_name(raw: Any) -> Tuple[str, str]:
    """
    Returns (clean_original, normalized_canonical).
    Canonical form: lowercase, stripped honorific titles, collapsed whitespace.
    """
    if raw is None:
        return "", ""
    orig = str(raw).strip()
    # Strip honorifics
    canon = TITLE_PREFIXES.sub("", orig)
    canon = re.sub(r"[^\w\s]", "", canon)
    canon = re.sub(r"\s+", " ", canon).strip().lower()
    return orig, canon

def normalize_vehicle(raw: Any) -> Optional[str]:
    """Normalizes Indian vehicle registration (DL01AB1234)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    cleaned = re.sub(r"[\s\-]", "", s).upper()
    return cleaned if len(cleaned) >= 6 else None

def normalize_email(raw: Any) -> Optional[str]:
    """Normalizes email address."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if "@" in s and "." in s:
        return s
    return None

def normalize_ip(raw: Any) -> Tuple[Optional[str], bool]:
    """Validates IPv4 or IPv6 address."""
    if raw is None:
        return None, False
    s = str(raw).strip()
    try:
        ipaddress.ip_address(s)
        return s, True
    except ValueError:
        return s, False
