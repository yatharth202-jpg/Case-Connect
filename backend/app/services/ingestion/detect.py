import re
from typing import List, Dict, Any, Tuple
from backend.app.services.ingestion.readers import load_column_synonyms

MOBILE_REGEX = re.compile(r"^(?:\+?91|0)?[6-9]\d{9}$")
ACCOUNT_REGEX = re.compile(r"^\d{9,18}$")
IP_REGEX = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
VEHICLE_REGEX = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
UPI_REGEX = re.compile(r"[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+")

def sniff_value_types(records: List[Dict[str, Any]], sample_size: int = 150) -> Dict[str, float]:
    """
    Sniffs data patterns across the first sample_size rows.
    Returns share of values matching core entity patterns.
    """
    sample = records[:sample_size]
    if not sample:
        return {}

    total_cells = 0
    mobiles = 0
    accounts = 0
    ips = 0
    vehicles = 0
    upis = 0
    has_debit_credit_words = 0

    for r in sample:
        for val in r.values():
            if val is None:
                continue
            s = str(val).strip()
            if not s:
                continue
            total_cells += 1

            clean_digits = re.sub(r"\D", "", s)
            if MOBILE_REGEX.match(clean_digits):
                mobiles += 1
            elif ACCOUNT_REGEX.match(clean_digits):
                accounts += 1

            if IP_REGEX.match(s):
                ips += 1
            if VEHICLE_REGEX.match(re.sub(r"[\s\-]", "", s).upper()):
                vehicles += 1
            if UPI_REGEX.search(s):
                upis += 1
            if s.upper() in ["DR", "CR", "DEBIT", "CREDIT", "MOC", "MTC"]:
                has_debit_credit_words += 1

    if total_cells == 0:
        return {}

    return {
        "mobile_ratio": mobiles / total_cells,
        "account_ratio": accounts / total_cells,
        "ip_ratio": ips / total_cells,
        "vehicle_ratio": vehicles / total_cells,
        "upi_ratio": upis / total_cells,
        "indicator_ratio": has_debit_credit_words / total_cells
    }

def score_header_matches(headers: List[str], syn_dict: Dict[str, Dict[str, List[str]]]) -> Dict[str, float]:
    """Scores how well headers match synonyms for each known file type."""
    scores = {}
    norm_headers = [re.sub(r"[^\w]+", "_", str(h).strip().lower()).strip("_") for h in headers]
    compact_headers = [h.replace("_", "") for h in norm_headers]

    for type_name, fields in syn_dict.items():
        matched_fields = 0
        total_fields = len(fields)
        for field, syn_list in fields.items():
            field_matched = False
            for syn in syn_list:
                s_clean = re.sub(r"[^\w]+", "_", str(syn).strip().lower()).strip("_")
                s_compact = s_clean.replace("_", "")
                if s_clean in norm_headers or s_compact in compact_headers or any(s_clean in nh or nh in s_clean for nh in norm_headers if len(s_clean) >= 4):
                    field_matched = True
                    break
            if field_matched:
                matched_fields += 1
        scores[type_name] = matched_fields / max(1, total_fields)

    return scores

def detect_file_type(headers: List[str], records: List[Dict[str, Any]], filename: str = "") -> Dict[str, Any]:
    """
    Composite scoring to detect file type:
    Evaluates header synonyms + data sniffing + filename hints.
    Returns: {detected_type, confidence, alternatives}
    """
    fn_lower = filename.lower()
    if fn_lower.endswith((".pdf", ".docx", ".txt")):
        return {
            "detected_type": "text_document",
            "confidence": 0.95,
            "alternatives": []
        }

    syn_dict = load_column_synonyms()
    header_scores = score_header_matches(headers, syn_dict)
    sniff = sniff_value_types(records)

    scores = {}

    # 1. CDR scoring
    cdr_h = header_scores.get("cdr", 0.0)
    cdr_data = sniff.get("mobile_ratio", 0.0) * 3.0
    scores["cdr"] = min(1.0, cdr_h * 0.7 + cdr_data * 0.3)
    if "cdr" in fn_lower or "call" in fn_lower or "telecom" in fn_lower:
        scores["cdr"] = min(1.0, scores["cdr"] + 0.2)

    # 2. Bank Transactions (from/to)
    bt_h = header_scores.get("bank_transactions", 0.0)
    bt_data = sniff.get("account_ratio", 0.0) * 2.5
    scores["bank_transactions"] = min(1.0, bt_h * 0.7 + bt_data * 0.3)
    if ("bank" in fn_lower or "txn" in fn_lower or "transfer" in fn_lower) and "statement" not in fn_lower:
        scores["bank_transactions"] = min(1.0, scores["bank_transactions"] + 0.2)

    # 3. Bank Statement (single-account passbook with debit/credit/narration)
    bs_h = header_scores.get("bank_statement", 0.0)
    has_narration = any("narr" in h.lower() or "desc" in h.lower() or "ref" in h.lower() for h in headers)
    has_dr_cr = any("debit" in h.lower() or "credit" in h.lower() or "withdrawal" in h.lower() for h in headers)
    bs_bonus = 0.3 if (has_narration and has_dr_cr) else 0.0
    scores["bank_statement"] = min(1.0, bs_h * 0.6 + bs_bonus + sniff.get("upi_ratio", 0.0) * 2.0)
    if "statement" in fn_lower or "passbook" in fn_lower:
        scores["bank_statement"] = min(1.0, scores["bank_statement"] + 0.25)

    # 4. Identity Table (SDR, KYC, persons, vehicles)
    id_h = header_scores.get("identity_table", 0.0)
    has_name = any("name" in h.lower() or "holder" in h.lower() or "subscriber" in h.lower() for h in headers)
    id_bonus = 0.25 if has_name else 0.0
    scores["identity_table"] = min(1.0, id_h * 0.6 + id_bonus + sniff.get("vehicle_ratio", 0.0) * 3.0)
    if "sdr" in fn_lower or "kyc" in fn_lower or "person" in fn_lower or "vehicle" in fn_lower:
        scores["identity_table"] = min(1.0, scores["identity_table"] + 0.25)

    # 5. IP Log
    ip_h = header_scores.get("ip_log", 0.0)
    scores["ip_log"] = min(1.0, ip_h * 0.6 + sniff.get("ip_ratio", 0.0) * 4.0)
    if "ip" in fn_lower or "log" in fn_lower:
        scores["ip_log"] = min(1.0, scores["ip_log"] + 0.2)

    # Sort candidates
    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_conf = sorted_types[0]

    # If top score is very low, fall back to unknown
    if best_conf < 0.25:
        best_type = "unknown"
        best_conf = 0.2

    alternatives = [{"type": t, "score": round(s, 2)} for t, s in sorted_types[1:] if s > 0.15]

    return {
        "detected_type": best_type,
        "confidence": round(best_conf, 2),
        "alternatives": alternatives
    }
