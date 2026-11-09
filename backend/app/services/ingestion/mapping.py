import re
import hashlib
import ipaddress
import json
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.services.ingestion.readers import load_column_synonyms
from backend.app.services.ingestion.validators import (
    validate_phone,
    validate_bank_account,
    validate_amount,
    validate_ifsc,
    validate_imei,
    validate_imsi,
    validate_upi_vpa,
    validate_vehicle,
    parse_forensic_datetime,
)
from backend.app.db.sql import MappingTemplate

CANONICAL_FIELDS_BY_TYPE = {
    "cdr": [
        "caller", "receiver", "datetime", "date", "time", "duration",
        "call_type", "imei", "imsi", "cell_id", "location"
    ],
    "bank_transactions": [
        "txn_id", "datetime", "date", "time", "from_account", "to_account",
        "from_name", "to_name", "amount", "debit", "credit", "reference", "balance"
    ],
    "bank_statement": [
        "date", "narration", "debit", "credit", "amount", "balance",
        "reference", "statement_account"
    ],
    "identity_table": [
        "name", "phone", "account", "vehicle", "email", "ip",
        "imei", "address", "registered_mobile", "activation_date"
    ],
    "ip_log": [
        "identifier", "ip", "datetime", "date", "time"
    ]
}

REQUIRED_FIELDS = {
    "cdr": [["caller"], ["receiver"]],
    "bank_transactions": [["from_account"], ["to_account"], ["amount", "debit"]],
    "bank_statement": [["date"], ["narration"], ["amount", "debit", "credit"]],
    "identity_table": [["name"]],
    "ip_log": [["identifier"], ["ip"]]
}

# Expected content profile keys for each canonical field
FIELD_EXPECTED_CONTENT_TYPES: Dict[str, List[str]] = {
    "caller": ["phone"],
    "receiver": ["phone"],
    "phone": ["phone"],
    "registered_mobile": ["phone"],
    "from_account": ["account"],
    "to_account": ["account"],
    "account": ["account"],
    "statement_account": ["account"],
    "datetime": ["date"],
    "date": ["date"],
    "activation_date": ["date"],
    "time": ["time"],
    "duration": ["duration"],
    "amount": ["amount"],
    "debit": ["amount"],
    "credit": ["amount"],
    "balance": ["amount"],
    "imei": ["imei"],
    "imsi": ["imsi"],
    "vehicle": ["vehicle"],
    "ip": ["ip"],
    "email": ["email"],
    "narration": ["narration", "vpa", "text"],
    "reference": ["narration", "vpa", "text"],
    "name": ["person_name", "text"],
    "from_name": ["person_name", "text"],
    "to_name": ["person_name", "text"],
    "call_type": ["call_type", "text"],
    "identifier": ["phone", "account", "text"],
}

_TIME_ONLY_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?$")
_DURATION_HMS_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def compute_header_signature(headers: List[str]) -> str:
    """Deterministic hash of header column set to identify identical file formats."""
    norm = sorted([h.strip().lower() for h in headers if h.strip()])
    return hashlib.sha256("|".join(norm).encode("utf-8")).hexdigest()


def normalize_header_str(h: str) -> str:
    """Normalizes header string by replacing non-alphanumeric chars with underscores."""
    return re.sub(r"[^\w]+", "_", str(h).strip().lower()).strip("_")


def compute_column_content_profile(values: List[Any], sample_size: int = 100) -> Dict[str, Any]:
    """
    Computes a statistical and validator-backed content profile for a single column:
    phone_ratio, account_ratio, date_ratio, time_ratio, amount_ratio, duration_ratio,
    imei_ratio, imsi_ratio, ifsc_ratio, vpa_ratio, vehicle_ratio, ip_ratio, email_ratio,
    distinct_ratio, non_empty_ratio, and dominant_type.
    """
    sliced = values[:sample_size]
    total = max(1, len(sliced))
    non_empty = [str(v).strip() for v in sliced if v is not None and str(v).strip() != ""]
    n = len(non_empty)
    if n == 0:
        return {
            "non_empty_ratio": 0.0,
            "distinct_ratio": 0.0,
            "phone_ratio": 0.0,
            "account_ratio": 0.0,
            "date_ratio": 0.0,
            "time_ratio": 0.0,
            "amount_ratio": 0.0,
            "duration_ratio": 0.0,
            "imei_ratio": 0.0,
            "imsi_ratio": 0.0,
            "ifsc_ratio": 0.0,
            "vpa_ratio": 0.0,
            "vehicle_ratio": 0.0,
            "ip_ratio": 0.0,
            "email_ratio": 0.0,
            "narration_ratio": 0.0,
            "person_name_ratio": 0.0,
            "call_type_ratio": 0.0,
            "dominant_type": "empty",
        }

    phones = 0
    accounts = 0
    dates = 0
    times = 0
    amounts = 0
    durations = 0
    imeis = 0
    imsis = 0
    ifscs = 0
    vpas = 0
    vehicles = 0
    ips = 0
    emails = 0
    narrations = 0
    person_names = 0
    call_types = 0

    for s in non_empty:
        clean_digits = re.sub(r"\D", "", s)

        if _TIME_ONLY_RE.match(s):
            times += 1
            if _DURATION_HMS_RE.match(s):
                durations += 1
            continue

        if s.upper() in {"IN", "OUT", "MOC", "MTC", "SMS", "VOICE", "INCOMING", "OUTGOING", "DATA"}:
            call_types += 1
            continue

        # Date check (requires date separators '-', '/', or month names)
        if (any(sep in s for sep in ("-", "/")) and len(s) >= 6 and any(ch.isdigit() for ch in s)):
            dt_res = parse_forensic_datetime(s)
            if dt_res["ok"]:
                dates += 1
                continue

        # IP check
        try:
            ipaddress.ip_address(s)
            ips += 1
            continue
        except ValueError:
            pass

        # Email vs UPI VPA
        if "@" in s:
            if _EMAIL_RE.match(s):
                emails += 1
            elif validate_upi_vpa(s)["ok"]:
                vpas += 1
            continue

        # IFSC check
        if len(s) == 11 and validate_ifsc(s)["ok"]:
            ifscs += 1
            continue

        # Vehicle check
        if validate_vehicle(s)["ok"]:
            vehicles += 1
            continue

        # IMEI / IMSI (15 digits)
        if len(clean_digits) == 15 and s.isdigit():
            if validate_imei(clean_digits)["ok"]:
                imeis += 1
            elif validate_imsi(clean_digits)["ok"]:
                imsis += 1
            accounts += 1
            continue

        # Phone vs Account vs Amount vs Duration
        v_phone = validate_phone(s)
        if v_phone["ok"] and v_phone["meta"].get("valid_mobile") and "." not in s and "," not in s:
            phones += 1
            # A 10-digit string can also be a 10-digit bank account
            if len(clean_digits) == 10 and s.isdigit():
                accounts += 0.5
            continue

        if len(clean_digits) >= 9 and "." not in s and "," not in s and validate_bank_account(s)["ok"]:
            accounts += 1
            continue

        # Duration vs Amount
        if s.isdigit() and 0 <= int(s) <= 86400 and len(s) <= 5:
            durations += 1
            amounts += 0.4
            continue

        v_amt = validate_amount(s)
        if v_amt["ok"] and any(ch.isdigit() for ch in s):
            amounts += 1
            continue

        # Text / Name / Narration
        if "UPI/" in s.upper() or "NEFT" in s.upper() or "IMPS" in s.upper() or "RTGS" in s.upper() or len(s) >= 15:
            narrations += 1
        elif all(ch.isalpha() or ch in " .'-" for ch in s) and 2 <= len(s) <= 45:
            person_names += 1

    ratios = {
        "phone": round(phones / n, 3),
        "account": round(min(1.0, accounts / n), 3),
        "date": round(dates / n, 3),
        "time": round(times / n, 3),
        "amount": round(min(1.0, amounts / n), 3),
        "duration": round(durations / n, 3),
        "imei": round(imeis / n, 3),
        "imsi": round(imsis / n, 3),
        "ifsc": round(ifscs / n, 3),
        "vpa": round(vpas / n, 3),
        "vehicle": round(vehicles / n, 3),
        "ip": round(ips / n, 3),
        "email": round(emails / n, 3),
        "narration": round(narrations / n, 3),
        "person_name": round(person_names / n, 3),
        "call_type": round(call_types / n, 3),
    }

    best_type, best_val = max(ratios.items(), key=lambda kv: kv[1])
    dominant_type = best_type if best_val >= 0.35 else "text"

    return {
        "non_empty_ratio": round(n / total, 3),
        "distinct_ratio": round(len(set(non_empty)) / n, 3),
        "phone_ratio": ratios["phone"],
        "account_ratio": ratios["account"],
        "date_ratio": ratios["date"],
        "time_ratio": ratios["time"],
        "amount_ratio": ratios["amount"],
        "duration_ratio": ratios["duration"],
        "imei_ratio": ratios["imei"],
        "imsi_ratio": ratios["imsi"],
        "ifsc_ratio": ratios["ifsc"],
        "vpa_ratio": ratios["vpa"],
        "vehicle_ratio": ratios["vehicle"],
        "ip_ratio": ratios["ip"],
        "email_ratio": ratios["email"],
        "narration_ratio": ratios["narration"],
        "person_name_ratio": ratios["person_name"],
        "call_type_ratio": ratios["call_type"],
        "dominant_type": dominant_type,
    }


def _score_header_for_field(h_norm: str, h_compact: str, canon_field: str, syn_list: List[str]) -> Tuple[float, Optional[str]]:
    """Returns (header_score 0..1, reason) for a single (header, canonical_field) pair."""
    from rapidfuzz import fuzz

    canon_compact = canon_field.replace("_", "")
    if h_norm == canon_field or h_compact == canon_compact:
        return 1.0, f"Exact header match with '{canon_field}'"

    best_score = 0.0
    best_reason = None
    for s in syn_list:
        s_norm = normalize_header_str(s)
        s_compact = s_norm.replace("_", "")
        if h_norm == s_norm or h_compact == s_compact:
            return 0.95, f"Exact synonym match ('{s}')"
        elif (s_norm in h_norm or h_norm in s_norm) and len(min(s_norm, h_norm, key=len)) >= 3:
            if best_score < 0.80:
                best_score = 0.80
                best_reason = f"Header substring match ('{s}')"
        else:
            fz = max(fuzz.token_set_ratio(h_norm, s_norm), fuzz.ratio(h_norm, s_norm))
            if fz >= 88 and best_score < 0.85:
                best_score = 0.85
                best_reason = f"High fuzzy header similarity with '{s}' ({fz:.0f}%)"
            elif fz >= 75 and best_score < 0.70:
                best_score = 0.70
                best_reason = f"Moderate fuzzy header similarity with '{s}' ({fz:.0f}%)"

    return best_score, best_reason


def _score_content_for_field(profile: Dict[str, Any], canon_field: str) -> Tuple[float, Optional[str]]:
    """Scores how well a column's content profile matches a canonical field."""
    if not profile or profile.get("non_empty_ratio", 0.0) == 0.0:
        return 0.0, None

    expected_types = FIELD_EXPECTED_CONTENT_TYPES.get(canon_field, [])
    best_ratio = 0.0
    best_type = None
    for et in expected_types:
        r_val = float(profile.get(f"{et}_ratio", 0.0))
        if r_val > best_ratio:
            best_ratio = r_val
            best_type = et

    if best_ratio >= 0.4:
        return best_ratio, f"Column values match {best_type} pattern ({best_ratio:.0%})"
    return 0.0, None


def suggest_column_mappings(
    file_type: str,
    headers: List[str],
    records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Suggests canonical field mappings for each header column by combining:
    1. Header-name similarity (exact, synonym, fuzzy)
    2. Content profile score (phone/account/date/amount/IMEI/IFSC/VPA/vehicle ratios)
    Returns for each header:
      {
        "canonical": str,
        "confidence": float,
        "reasons": List[str],
        "candidates": List[{"canonical": str, "confidence": float, "reasons": List[str]}],  # top-3
        "content_profile": Dict[str, Any],
      }
    """
    syn_dict = load_column_synonyms()
    type_syns = syn_dict.get(file_type, {})
    canonical_candidates = CANONICAL_FIELDS_BY_TYPE.get(file_type, [])

    suggestions: Dict[str, Dict[str, Any]] = {}
    assigned_canonicals = set()

    for col_idx, h in enumerate(headers):
        h_norm = normalize_header_str(h)
        h_compact = h_norm.replace("_", "")

        col_values = [r.get(h) for r in records[:100]] if records else []
        profile = compute_column_content_profile(col_values) if records else {}

        field_scores: List[Dict[str, Any]] = []
        for canon_field in canonical_candidates:
            syn_list = type_syns.get(canon_field, [])
            h_score, h_reason = _score_header_for_field(h_norm, h_compact, canon_field, syn_list)
            c_score, c_reason = _score_content_for_field(profile, canon_field)

            reasons: List[str] = []
            if h_reason:
                reasons.append(h_reason)
            if c_reason:
                reasons.append(c_reason)

            if records and profile.get("non_empty_ratio", 0.0) > 0:
                if h_score >= 0.90:
                    # High header confidence; boost or slightly penalize if content strongly disagrees
                    if c_score >= 0.5:
                        combined = min(1.0, h_score * 0.75 + c_score * 0.25 + 0.05)
                    elif FIELD_EXPECTED_CONTENT_TYPES.get(canon_field) and c_score == 0.0 and profile.get("dominant_type") not in ("empty", "text"):
                        combined = round(h_score * 0.75, 2)
                        reasons.append(f"Content dominant type is '{profile.get('dominant_type')}'")
                    else:
                        combined = h_score
                elif h_score > 0:
                    combined = round(min(0.95, h_score * 0.65 + c_score * 0.35), 2)
                else:
                    # Obfuscated/generic header (e.g. col_1, FieldA): rely on content profile
                    # Disambiguate 1st vs 2nd phone/account column by column order
                    if c_score >= 0.6:
                        order_bonus = 0.02 if (canon_field in ("caller", "from_account") and canon_field not in assigned_canonicals) else 0.0
                        combined = round(min(0.85, c_score * 0.80 + order_bonus), 2)
                    else:
                        combined = 0.0
            else:
                combined = h_score

            if combined > 0.0:
                field_scores.append({
                    "canonical": canon_field,
                    "confidence": round(combined, 2),
                    "reasons": reasons or ["Matched by header/content heuristics"],
                })

        field_scores.sort(key=lambda x: x["confidence"], reverse=True)
        top_3 = field_scores[:3]

        best_canonical = "ignore"
        best_conf = 0.0
        best_reasons: List[str] = []

        for cand in field_scores:
            c_field = cand["canonical"]
            c_conf = cand["confidence"]
            if c_field in assigned_canonicals and c_conf < 0.92:
                continue
            best_canonical = c_field
            best_conf = c_conf
            best_reasons = cand["reasons"]
            assigned_canonicals.add(c_field)
            break

        if not top_3:
            top_3 = [{"canonical": "ignore", "confidence": 0.0, "reasons": ["No matching header or content pattern"]}]

        suggestions[h] = {
            "canonical": best_canonical,
            "confidence": round(best_conf, 2),
            "reasons": best_reasons,
            "candidates": top_3,
            "content_profile": profile,
        }

    return suggestions


def get_mapping_template_envelope(db: Session, signature: str) -> Optional[Dict[str, Any]]:
    """Retrieves full saved template envelope (mapping + headers + column_profiles)."""
    tpl = db.query(MappingTemplate).filter(MappingTemplate.header_signature == signature).first()
    if not tpl:
        return None
    try:
        raw = json.loads(tpl.mapping_json)
        if isinstance(raw, dict) and "_template_meta" in raw:
            return {
                "file_type": tpl.file_type,
                "mapping": raw.get("mapping", {}),
                "headers": raw["_template_meta"].get("headers", list(raw.get("mapping", {}).keys())),
                "column_profiles": raw["_template_meta"].get("column_profiles", {}),
            }
        elif isinstance(raw, dict):
            return {
                "file_type": tpl.file_type,
                "mapping": raw,
                "headers": list(raw.keys()),
                "column_profiles": {},
            }
    except Exception:
        return None
    return None


def get_mapping_template(db: Session, signature: str) -> Dict[str, Any] | None:
    """Retrieve saved mapping dictionary {header: canonical_field} by header signature."""
    env = get_mapping_template_envelope(db, signature)
    if env:
        return env["mapping"]
    return None


def save_mapping_template(
    db: Session,
    signature: str,
    file_type: str,
    mapping: Dict[str, str],
    headers: Optional[List[str]] = None,
    column_profiles: Optional[Dict[str, Any]] = None,
):
    """Save or update mapping template by header signature, including column profiles for drift checks."""
    payload: Dict[str, Any]
    if headers is not None or column_profiles is not None:
        payload = {
            **mapping,
            "_template_meta": {
                "headers": headers or list(mapping.keys()),
                "column_profiles": column_profiles or {},
            },
            "mapping": mapping,
        }
    else:
        payload = mapping

    existing = db.query(MappingTemplate).filter(MappingTemplate.header_signature == signature).first()
    if existing:
        existing.mapping_json = json.dumps(payload)
    else:
        new_tpl = MappingTemplate(
            header_signature=signature,
            file_type=file_type,
            mapping_json=json.dumps(payload)
        )
        db.add(new_tpl)
    db.commit()


def check_mapping_template_drift(
    db: Session,
    file_type: str,
    headers: List[str],
    records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Compares an incoming file's headers and column content types against saved templates.
    Detects:
      - added_columns (present in file but missing in closest template for file_type)
      - removed_columns (present in template but missing in file)
      - type_changed_columns (column mapped to field X now has incompatible content type)
    Requires officer confirmation whenever drift != none.
    """
    sig = compute_header_signature(headers)
    exact_env = get_mapping_template_envelope(db, sig)

    # If no exact signature match, look for the most recent template of the same file_type to report structural drift
    target_env = exact_env
    if target_env is None and file_type and file_type != "unknown":
        same_type_tpl = (
            db.query(MappingTemplate)
            .filter(MappingTemplate.file_type == file_type)
            .order_by(MappingTemplate.created_at.desc())
            .first()
        )
        if same_type_tpl:
            target_env = get_mapping_template_envelope(db, same_type_tpl.header_signature)

    if target_env is None:
        return {
            "template_found": False,
            "exact_signature_match": False,
            "has_drift": False,
            "drift_status": "no_template",
            "added_columns": [],
            "removed_columns": [],
            "type_changed_columns": [],
            "requires_confirmation": True,
            "reasons": ["No saved mapping template found; officer confirmation required"],
        }

    tpl_mapping: Dict[str, str] = {
        k: v for k, v in target_env["mapping"].items() if k != "_template_meta" and isinstance(v, str)
    }
    tpl_headers = [h for h in target_env.get("headers", list(tpl_mapping.keys())) if h != "_template_meta"]
    tpl_profiles = target_env.get("column_profiles", {})

    curr_norm_map = {h.strip().lower(): h for h in headers if h.strip()}
    tpl_norm_map = {h.strip().lower(): h for h in tpl_headers if h.strip()}

    added_columns = [curr_norm_map[k] for k in curr_norm_map if k not in tpl_norm_map]
    removed_columns = [tpl_norm_map[k] for k in tpl_norm_map if k not in curr_norm_map]
    type_changed_columns: List[Dict[str, Any]] = []
    reasons: List[str] = []

    if added_columns:
        reasons.append(f"Columns added vs template: {', '.join(added_columns)}")
    if removed_columns:
        reasons.append(f"Columns removed vs template: {', '.join(removed_columns)}")

    if records:
        for h in headers:
            canon_field = tpl_mapping.get(h)
            if not canon_field or canon_field == "ignore":
                continue
            col_vals = [r.get(h) for r in records[:100]]
            curr_prof = compute_column_content_profile(col_vals)
            if curr_prof.get("non_empty_ratio", 0.0) == 0.0:
                continue

            expected_types = FIELD_EXPECTED_CONTENT_TYPES.get(canon_field, [])
            curr_dom = curr_prof.get("dominant_type", "text")
            prev_dom = tpl_profiles.get(h, {}).get("dominant_type")

            # Check if content violates expected type of the mapped canonical field
            if expected_types and "text" not in expected_types:
                c_score, _ = _score_content_for_field(curr_prof, canon_field)
                if c_score < 0.25:
                    type_changed_columns.append({
                        "column": h,
                        "mapped_to": canon_field,
                        "expected_types": expected_types,
                        "observed_dominant_type": curr_dom,
                        "previous_dominant_type": prev_dom,
                    })
                    reasons.append(
                        f"Column '{h}' mapped to '{canon_field}' has incompatible content type '{curr_dom}'"
                    )

    has_drift = bool(added_columns or removed_columns or type_changed_columns)
    return {
        "template_found": True,
        "exact_signature_match": exact_env is not None,
        "has_drift": has_drift,
        "drift_status": "drift_detected" if has_drift else "none",
        "added_columns": added_columns,
        "removed_columns": removed_columns,
        "type_changed_columns": type_changed_columns,
        "requires_confirmation": has_drift,
        "reasons": reasons or ["Template matches headers and column content types"],
    }
