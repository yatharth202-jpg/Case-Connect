import hashlib
import json
from typing import Dict, Any, List, Tuple, Optional
from backend.app.config import get_merge_config

KNOWN_FIELDS_BY_RECORD_TYPE: Dict[str, set] = {
    "transaction": {
        "txn_id", "account", "from_account", "to_account", "from_name", "to_name",
        "amount_paise", "date_iso", "datetime_iso", "tz_source", "direction",
        "balance_after_paise", "reference", "reference_hash", "narration",
    },
    "call": {
        "caller", "receiver", "call_date", "call_time", "datetime_iso", "tz_source",
        "duration_seconds", "call_type", "imei", "imsi", "cell_id", "location",
    },
    "ip_event": {
        "identifier", "ip_address", "datetime_iso", "tz_source",
    },
    "entity": {
        "label", "canonical_id", "display_name", "entity_type", "normalized_value",
        "raw_value", "phone", "account", "vehicle", "email", "address", "ifsc", "vpa",
    },
    "document_fact": {
        "fact_type", "fact_key", "fact_value", "raw_value", "date_iso", "place",
        "section_code", "char_span_start", "char_span_end", "page_or_paragraph",
    },
}

INTERNAL_META_KEYS = {
    "_page_no", "_bbox", "_timestamp_sec", "_raw", "_source_ref", "_confidence", "_method", "_source_kind"
}


def split_known_and_extra_fields(
    record_type: str,
    record_dict: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Splits an incoming record dictionary into:
      - known_fields (stored in data_json)
      - extra_fields (unknown/new dynamic columns, stored in extra_json and registered in schema_registry)
    Never drops any non-empty field.
    """
    known_set = KNOWN_FIELDS_BY_RECORD_TYPE.get(record_type, set())
    known_out: Dict[str, Any] = {}
    extra_out: Dict[str, Any] = {}

    for k, v in record_dict.items():
        if k in INTERNAL_META_KEYS or v is None or (isinstance(v, str) and v.strip() == ""):
            continue
        if k in known_set:
            known_out[k] = v
        else:
            extra_out[k] = v

    return known_out, extra_out


def _prepare_key_lookup_dict(record_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Enriches data dictionary with derived helper fields needed by configured natural keys."""
    enriched = dict(data)
    if record_type == "transaction":
        # Map account alias if needed
        if "account" not in enriched or enriched.get("account") in (None, ""):
            if enriched.get("from_account") and enriched.get("to_account"):
                enriched["account"] = f"{enriched['from_account']}->{enriched['to_account']}"
            elif enriched.get("from_account"):
                enriched["account"] = enriched["from_account"]
            elif enriched.get("to_account"):
                enriched["account"] = enriched["to_account"]

        if "balance_after_paise" not in enriched or enriched.get("balance_after_paise") is None:
            enriched["balance_after_paise"] = enriched.get("balance_paise", 0)

        if "direction" not in enriched or not enriched.get("direction"):
            enriched["direction"] = "transfer"

        if "reference_hash" not in enriched or not enriched.get("reference_hash"):
            ref_src = str(enriched.get("reference") or enriched.get("narration") or "")
            enriched["reference_hash"] = hashlib.sha256(ref_src.strip().lower().encode("utf-8")).hexdigest()[:16]

    return enriched


def compute_natural_key(
    case_id: str,
    record_type: str,
    data: Dict[str, Any],
    evidence_id: str = "",
    source_ref: str = "",
    natural_keys_config: Optional[Dict[str, List[List[str]]]] = None,
) -> Tuple[str, List[str]]:
    """
    Computes a deterministic SHA-256 natural_key for a record using the first configured
    natural key alternative in defaults.yaml (`merge.natural_keys[record_type]`) whose fields are all present.
    
    Governance Invariant:
      PERSON entities are NEVER merged by name here. Each Person entity observation is keyed
      with its source_ref and evidence_id so identity resolution stays exclusively in
      services/matching with explicit officer confirmation.
    """
    if record_type == "entity":
        label = str(data.get("label") or data.get("entity_type") or "Entity").strip()
        canon_id = str(data.get("canonical_id") or data.get("normalized_value") or data.get("display_name") or "").strip()
        if label.lower() == "person":
            raw_key = f"{case_id}|entity|Person|{evidence_id}|{source_ref}|{canon_id.lower()}"
            return hashlib.sha256(raw_key.encode("utf-8")).hexdigest(), ["label", "evidence_id", "source_ref", "canonical_id"]
        else:
            raw_key = f"{case_id}|entity|{label}|{canon_id.upper()}"
            return hashlib.sha256(raw_key.encode("utf-8")).hexdigest(), ["label", "canonical_id"]

    if record_type == "document_fact":
        f_key = str(data.get("fact_key") or data.get("fact_type") or "fact").strip().lower()
        f_val = str(data.get("fact_value") or "").strip()
        raw_key = f"{case_id}|document_fact|{evidence_id}|{f_key}|{f_val}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest(), ["evidence_id", "fact_key", "fact_value"]

    if natural_keys_config is None:
        natural_keys_config = get_merge_config().get("natural_keys", {})

    alternatives: List[List[str]] = natural_keys_config.get(record_type, [])
    enriched = _prepare_key_lookup_dict(record_type, data)

    for key_fields in alternatives:
        if all(
            f in enriched and enriched[f] is not None and str(enriched[f]).strip() != ""
            for f in key_fields
        ):
            parts = [f"{f}={str(enriched[f]).strip()}" for f in key_fields]
            payload = f"{case_id}|{record_type}|" + "|".join(parts)
            return hashlib.sha256(payload.encode("utf-8")).hexdigest(), list(key_fields)

    # Fallback: deterministic hash over sorted non-empty fields
    sorted_items = [
        f"{k}={str(v).strip()}"
        for k, v in sorted(enriched.items())
        if k not in INTERNAL_META_KEYS and v is not None and str(v).strip() != ""
    ]
    fallback_payload = f"{case_id}|{record_type}|fallback|" + "|".join(sorted_items)
    return hashlib.sha256(fallback_payload.encode("utf-8")).hexdigest(), ["_fallback_all_fields"]


def assign_occurrence_indices(
    case_id: str,
    record_type: str,
    records: List[Dict[str, Any]],
    evidence_id: str = "",
    natural_keys_config: Optional[Dict[str, List[List[str]]]] = None,
) -> List[Dict[str, Any]]:
    """
    For a batch of records from the SAME evidence file, computes (natural_key, occurrence_idx)
    where occurrence_idx = 1, 2, ... for the Nth identical natural_key within that file.
    This preserves legitimate repeated rows within one file while deduplicating overlapping
    re-uploads (mapping k-th to k-th).
    """
    counts_by_key: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records, start=1):
        src_ref = str(rec.get("_source_ref") or idx)
        nat_key, used_fields = compute_natural_key(
            case_id=case_id,
            record_type=record_type,
            data=rec,
            evidence_id=evidence_id,
            source_ref=src_ref,
            natural_keys_config=natural_keys_config,
        )
        occ_idx = counts_by_key.get(nat_key, 0) + 1
        counts_by_key[nat_key] = occ_idx
        out.append({
            "record": rec,
            "natural_key": nat_key,
            "occurrence_idx": occ_idx,
            "key_fields_used": used_fields,
            "source_ref": src_ref,
        })

    return out

