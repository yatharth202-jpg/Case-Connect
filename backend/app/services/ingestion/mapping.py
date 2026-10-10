import re
import hashlib
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.services.ingestion.readers import load_column_synonyms
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

def compute_header_signature(headers: List[str]) -> str:
    """Deterministic hash of header column set to identify identical file formats."""
    norm = sorted([h.strip().lower() for h in headers if h.strip()])
    return hashlib.sha256("|".join(norm).encode("utf-8")).hexdigest()

def normalize_header_str(h: str) -> str:
    """Normalizes header string by replacing non-alphanumeric chars with underscores."""
    return re.sub(r"[^\w]+", "_", str(h).strip().lower()).strip("_")

def suggest_column_mappings(file_type: str, headers: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Suggests canonical field mappings for each header column with confidence.
    Supports exact, substring, and RapidFuzz fuzzy matching across synonyms.
    Returns: { header: { "canonical": "field_name", "confidence": float } }
    """
    from rapidfuzz import fuzz
    syn_dict = load_column_synonyms()
    type_syns = syn_dict.get(file_type, {})
    canonical_candidates = CANONICAL_FIELDS_BY_TYPE.get(file_type, [])

    suggestions = {}
    assigned_canonicals = set()

    for h in headers:
        h_norm = normalize_header_str(h)
        h_compact = h_norm.replace("_", "")
        best_canonical = "ignore"
        best_conf = 0.0

        for canon_field in canonical_candidates:
            canon_compact = canon_field.replace("_", "")
            syn_list = type_syns.get(canon_field, [])

            # 1. Exact match with canonical field
            if h_norm == canon_field or h_compact == canon_compact:
                best_canonical = canon_field
                best_conf = 1.0
                break

            # 2. Synonym match
            for s in syn_list:
                s_norm = normalize_header_str(s)
                s_compact = s_norm.replace("_", "")
                if h_norm == s_norm or h_compact == s_compact:
                    if best_conf < 0.95:
                        best_canonical = canon_field
                        best_conf = 0.95
                    break
                elif s_norm in h_norm or h_norm in s_norm:
                    if best_conf < 0.80:
                        best_canonical = canon_field
                        best_conf = 0.80
                else:
                    score = max(fuzz.token_set_ratio(h_norm, s_norm), fuzz.ratio(h_norm, s_norm))
                    if score >= 88:
                        if best_conf < 0.85:
                            best_canonical = canon_field
                            best_conf = 0.85
                    elif score >= 75:
                        if best_conf < 0.70:
                            best_canonical = canon_field
                            best_conf = 0.70

        # Avoid duplicate assignment of single-instance fields unless high confidence
        if best_canonical != "ignore" and best_canonical in assigned_canonicals and best_conf < 0.9:
            best_canonical = "ignore"
            best_conf = 0.0
        elif best_canonical != "ignore":
            assigned_canonicals.add(best_canonical)

        suggestions[h] = {
            "canonical": best_canonical,
            "confidence": round(best_conf, 2)
        }

    return suggestions

def get_mapping_template(db: Session, signature: str) -> Dict[str, Any] | None:
    """Retrieve saved mapping template by header signature."""
    tpl = db.query(MappingTemplate).filter(MappingTemplate.header_signature == signature).first()
    if tpl:
        try:
            return json.loads(tpl.mapping_json)
        except Exception:
            return None
    return None

def save_mapping_template(db: Session, signature: str, file_type: str, mapping: Dict[str, str]):
    """Save or update mapping template by header signature."""
    existing = db.query(MappingTemplate).filter(MappingTemplate.header_signature == signature).first()
    if existing:
        existing.mapping_json = json.dumps(mapping)
    else:
        new_tpl = MappingTemplate(
            header_signature=signature,
            file_type=file_type,
            mapping_json=json.dumps(mapping)
        )
        db.add(new_tpl)
    db.commit()
