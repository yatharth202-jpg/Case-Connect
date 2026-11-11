"""
Forensic PII Masking & Serializer Engine for CaseConnect AI (Extraction V2 Phase 8).
Complies with Section 63 BSA 2023 privacy mandates.

Masking is strictly a response-layer concern. SQLite and Neo4j retain 100% normalized,
unmasked forensic data. Unprivileged users (e.g. viewers) or default API views see
masked PII (showing only the last 4 characters). Authorized officers (investigators/admins)
can request an audited reveal via POST /cases/{case_id}/reveal.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from backend.app.config import get_extraction_config

RE_ALL_DIGITS = re.compile(r"\D")


def get_masking_config() -> Dict[str, Any]:
    """Returns masking configuration from defaults.yaml."""
    cfg = get_extraction_config()
    return cfg.get("masking", {
        "fields": ["aadhaar", "account", "pan", "phone"],
        "reveal_roles": ["admin", "investigator"],
        "mask_style": "last4",
    })


def can_user_reveal_pii(user_role: str) -> bool:
    """Verifies whether the officer role has statutory authority to request unmasked PII."""
    allowed = get_masking_config().get("reveal_roles", ["admin", "investigator"])
    return str(user_role).lower().strip() in [r.lower().strip() for r in allowed]


def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Masks phone number, displaying only the final 4 digits."""
    if not phone:
        return phone
    s = str(phone).strip()
    digits = RE_ALL_DIGITS.sub("", s)
    if len(digits) >= 4:
        last4 = digits[-4:]
        prefix_len = max(2, len(digits) - 4)
        return ("X" * prefix_len) + last4
    return "XXXX"


def mask_account(acct: Optional[str]) -> Optional[str]:
    """Masks bank account number, displaying only the final 4 digits."""
    if not acct:
        return acct
    s = str(acct).strip()
    if len(s) >= 4:
        last4 = s[-4:]
        prefix_len = max(4, len(s) - 4)
        return ("X" * prefix_len) + last4
    return "XXXX"


def mask_aadhaar(aadhaar: Optional[str]) -> Optional[str]:
    """Masks 12-digit Aadhaar number as XXXX-XXXX-1234."""
    if not aadhaar:
        return aadhaar
    digits = RE_ALL_DIGITS.sub("", str(aadhaar))
    if len(digits) >= 4:
        last4 = digits[-4:]
        return f"XXXX-XXXX-{last4}"
    return "XXXX-XXXX-XXXX"


def mask_pan(pan: Optional[str]) -> Optional[str]:
    """Masks 10-character PAN, showing last 4 characters (e.g. XXXXXX123F)."""
    if not pan:
        return pan
    s = str(pan).strip().upper()
    if len(s) >= 4:
        last4 = s[-4:]
        prefix_len = max(2, len(s) - 4)
        return ("X" * prefix_len) + last4
    return "XXXX"


def mask_pii_value(field_or_type: str, value: Any) -> Any:
    """
    Masks a single value based on field name or entity type identifier.
    Returns original value if string is empty or field is not in masked fields.
    """
    if value is None:
        return None
    val_str = str(value)
    if not val_str:
        return value

    key = str(field_or_type).lower().strip()
    cfg_fields = [f.lower().strip() for f in get_masking_config().get("fields", [])]

    if "aadhaar" in key or "uidai" in key:
        return mask_aadhaar(val_str)
    elif "pan" in key:
        return mask_pan(val_str)
    elif any(f in key for f in ["phone", "caller", "receiver", "mobile", "msisdn"]):
        return mask_phone(val_str)
    elif any(f in key for f in ["account", "acc_no", "bank_account", "acct"]):
        return mask_account(val_str)

    return value


def mask_extracted_entity_dict(entity_dict: Dict[str, Any], reveal: bool = False) -> Dict[str, Any]:
    """
    Applies PII masking to an ExtractedEntity representation for API delivery.
    """
    if reveal:
        return dict(entity_dict)

    out = dict(entity_dict)
    etype = str(out.get("entity_type") or "").upper().strip()

    if etype in ("PHONE", "MOBILE", "CALLER", "RECEIVER"):
        out["normalized_value"] = mask_phone(out.get("normalized_value"))
        out["raw_value"] = mask_phone(out.get("raw_value"))
        out["is_masked"] = True
    elif etype in ("BANK_ACCOUNT", "ACCOUNT"):
        out["normalized_value"] = mask_account(out.get("normalized_value"))
        out["raw_value"] = mask_account(out.get("raw_value"))
        out["is_masked"] = True
    elif etype in ("AADHAAR", "UIDAI"):
        out["normalized_value"] = mask_aadhaar(out.get("normalized_value"))
        out["raw_value"] = mask_aadhaar(out.get("raw_value"))
        out["is_masked"] = True
    elif etype in ("PAN", "PAN_CARD"):
        out["normalized_value"] = mask_pan(out.get("normalized_value"))
        out["raw_value"] = mask_pan(out.get("raw_value"))
        out["is_masked"] = True

    return out


def mask_record_dict(record_dict: Dict[str, Any], reveal: bool = False) -> Dict[str, Any]:
    """
    Applies PII masking to an ExtractionRecord representation for API delivery.
    """
    if reveal:
        return dict(record_dict)

    out = dict(record_dict)
    rtype = str(out.get("record_type") or "").lower().strip()

    # Mask natural key if it contains sensitive identifiers
    nat_key = out.get("natural_key")
    if nat_key:
        if rtype in ("phone", "caller", "receiver", "cdr"):
            out["natural_key"] = mask_phone(nat_key)
        elif rtype in ("bank_account", "account", "transaction"):
            out["natural_key"] = mask_account(nat_key)
        elif rtype in ("aadhaar", "pan"):
            out["natural_key"] = mask_pii_value(rtype, nat_key)

    # Mask data_json fields
    data_payload = out.get("data") or out.get("data_json")
    if isinstance(data_payload, str):
        try:
            data_dict = json.loads(data_payload)
            for k in list(data_dict.keys()):
                data_dict[k] = mask_pii_value(k, data_dict[k])
            out["data_json"] = json.dumps(data_dict)
            if "data" in out:
                out["data"] = data_dict
        except Exception:
            pass
    elif isinstance(data_payload, dict):
        masked_d = {}
        for k, v in data_payload.items():
            masked_d[k] = mask_pii_value(k, v)
        out["data"] = masked_d
        if "data_json" in out:
            out["data_json"] = json.dumps(masked_d)

    out["is_masked"] = True
    return out

