import ipaddress
import re
from typing import List, Dict, Any, Optional
from backend.app.services.ingestion.readers import load_column_synonyms
from backend.app.services.ingestion.validators import (
    validate_phone,
    validate_bank_account,
    validate_vehicle,
    validate_upi_vpa,
    validate_ifsc,
    validate_imei,
    validate_amount,
    parse_forensic_datetime,
)


def _is_valid_ip_str(val: str) -> bool:
    try:
        ipaddress.ip_address(val.strip())
        return True
    except ValueError:
        return False


def sniff_value_types(records: List[Dict[str, Any]], sample_size: int = 150) -> Dict[str, float]:
    """
    Sniffs data patterns across the first sample_size rows using shared validators.
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
    ifscs = 0
    imeis = 0
    dates = 0
    amounts = 0
    has_debit_credit_words = 0

    for r in sample:
        for k, val in r.items():
            if k == "_page_no" or val is None:
                continue
            s = str(val).strip()
            if not s:
                continue
            total_cells += 1

            clean_digits = re.sub(r"\D", "", s)
            v_phone = validate_phone(s)
            if v_phone["ok"] and v_phone["meta"].get("valid_mobile"):
                mobiles += 1
            elif len(clean_digits) >= 9 and validate_bank_account(s)["ok"]:
                accounts += 1

            if len(clean_digits) == 15 and validate_imei(clean_digits)["ok"]:
                imeis += 1
            if _is_valid_ip_str(s):
                ips += 1
            if validate_vehicle(s)["ok"]:
                vehicles += 1
            if "@" in s and validate_upi_vpa(s)["ok"] or "UPI/" in s.upper():
                upis += 1
            if len(s) == 11 and validate_ifsc(s)["ok"]:
                ifscs += 1
            if any(sep in s for sep in ("-", "/")) and len(s) >= 8 and parse_forensic_datetime(s)["ok"]:
                dates += 1
            elif ("." in s or "," in s) and validate_amount(s)["ok"]:
                amounts += 1

            if s.upper() in ["DR", "CR", "DEBIT", "CREDIT", "MOC", "MTC"]:
                has_debit_credit_words += 1

    if total_cells == 0:
        return {}

    return {
        "mobile_ratio": mobiles / total_cells,
        "account_ratio": accounts / total_cells,
        "imei_ratio": imeis / total_cells,
        "ip_ratio": ips / total_cells,
        "vehicle_ratio": vehicles / total_cells,
        "upi_ratio": upis / total_cells,
        "ifsc_ratio": ifscs / total_cells,
        "date_ratio": dates / total_cells,
        "amount_ratio": amounts / total_cells,
        "indicator_ratio": has_debit_credit_words / total_cells,
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
                if (
                    s_clean in norm_headers
                    or s_compact in compact_headers
                    or any(s_clean in nh or nh in s_clean for nh in norm_headers if len(s_clean) >= 4)
                ):
                    field_matched = True
                    break
            if field_matched:
                matched_fields += 1
        scores[type_name] = matched_fields / max(1, total_fields)

    return scores


def detect_file_type(
    headers: List[str],
    records: List[Dict[str, Any]],
    filename: str = "",
    banners: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Composite scoring to detect file type:
    Evaluates header synonyms + validator-backed content profile + banner/filename hints.
    Returns: {detected_type, confidence, alternatives, reasons}
    """
    fn_lower = filename.lower()
    if fn_lower.endswith((".docx", ".txt")):
        return {
            "detected_type": "text_document",
            "confidence": 0.95,
            "alternatives": [],
            "reasons": ["Unstructured text/document extension detected"],
        }

    syn_dict = load_column_synonyms()
    header_scores = score_header_matches(headers, syn_dict)
    sniff = sniff_value_types(records)
    banner_text = " ".join(banners or []).lower()

    scores: Dict[str, float] = {}
    reasons_by_type: Dict[str, List[str]] = {
        "cdr": [],
        "bank_transactions": [],
        "bank_statement": [],
        "identity_table": [],
        "ip_log": [],
    }

    # 1. CDR scoring
    cdr_h = header_scores.get("cdr", 0.0)
    cdr_data = sniff.get("mobile_ratio", 0.0) * 3.0 + sniff.get("imei_ratio", 0.0) * 2.0
    scores["cdr"] = min(1.0, cdr_h * 0.65 + min(1.0, cdr_data) * 0.35)
    if cdr_h > 0.2:
        reasons_by_type["cdr"].append(f"Header synonym match for CDR ({cdr_h:.0%})")
    if sniff.get("mobile_ratio", 0.0) > 0.15:
        reasons_by_type["cdr"].append(f"High valid mobile ratio in content ({sniff['mobile_ratio']:.0%})")
    if "cdr" in fn_lower or "call" in fn_lower or "telecom" in fn_lower:
        scores["cdr"] = min(1.0, scores["cdr"] + 0.2)
        reasons_by_type["cdr"].append("Filename indicates telecom/CDR export")

    # 2. Bank Transactions (dual-account from/to transfer log)
    bt_h = header_scores.get("bank_transactions", 0.0)
    bt_data = sniff.get("account_ratio", 0.0) * 2.5 + sniff.get("amount_ratio", 0.0) * 1.5
    scores["bank_transactions"] = min(1.0, bt_h * 0.65 + min(1.0, bt_data) * 0.35)
    if bt_h > 0.2:
        reasons_by_type["bank_transactions"].append(f"Header synonym match for bank transfers ({bt_h:.0%})")
    if sniff.get("account_ratio", 0.0) > 0.15:
        reasons_by_type["bank_transactions"].append(f"Account number columns detected ({sniff['account_ratio']:.0%})")
    if ("bank" in fn_lower or "txn" in fn_lower or "transfer" in fn_lower) and "statement" not in fn_lower:
        scores["bank_transactions"] = min(1.0, scores["bank_transactions"] + 0.2)
        reasons_by_type["bank_transactions"].append("Filename indicates bank transfer log")

    # 3. Bank Statement (single-account passbook with debit/credit/narration/balance)
    bs_h = header_scores.get("bank_statement", 0.0)
    has_narration = any(
        any(k in h.lower() for k in ("narr", "desc", "particular", "remark"))
        for h in headers
    )
    has_dr_cr = any(
        any(k in h.lower() for k in ("debit", "credit", "withdrawal", "deposit", "balance"))
        for h in headers
    )
    bs_bonus = 0.3 if (has_narration and has_dr_cr) else 0.0
    if "account no" in banner_text or "a/c no" in banner_text or "opening balance" in banner_text:
        bs_bonus += 0.15
        reasons_by_type["bank_statement"].append("Preamble contains account/opening balance metadata")
    scores["bank_statement"] = min(1.0, bs_h * 0.6 + bs_bonus + sniff.get("upi_ratio", 0.0) * 1.5 + sniff.get("amount_ratio", 0.0) * 0.8)
    if bs_h > 0.2:
        reasons_by_type["bank_statement"].append(f"Header synonym match for bank statement ({bs_h:.0%})")
    if has_narration and has_dr_cr:
        reasons_by_type["bank_statement"].append("Narration + Debit/Credit/Balance columns present")
    if "statement" in fn_lower or "passbook" in fn_lower:
        scores["bank_statement"] = min(1.0, scores["bank_statement"] + 0.25)
        reasons_by_type["bank_statement"].append("Filename indicates account statement/passbook")

    # 4. Identity Table (SDR, KYC, persons, vehicles)
    id_h = header_scores.get("identity_table", 0.0)
    has_name = any("name" in h.lower() or "holder" in h.lower() or "subscriber" in h.lower() for h in headers)
    id_bonus = 0.25 if has_name else 0.0
    scores["identity_table"] = min(1.0, id_h * 0.6 + id_bonus + sniff.get("vehicle_ratio", 0.0) * 3.0)
    if id_h > 0.2:
        reasons_by_type["identity_table"].append(f"Header synonym match for identity/KYC table ({id_h:.0%})")
    if "sdr" in fn_lower or "kyc" in fn_lower or "person" in fn_lower or "vehicle" in fn_lower:
        scores["identity_table"] = min(1.0, scores["identity_table"] + 0.25)
        reasons_by_type["identity_table"].append("Filename indicates SDR/KYC identity table")

    # 5. IP Log
    ip_h = header_scores.get("ip_log", 0.0)
    scores["ip_log"] = min(1.0, ip_h * 0.6 + sniff.get("ip_ratio", 0.0) * 4.0)
    if ip_h > 0.2 or sniff.get("ip_ratio", 0.0) > 0.1:
        reasons_by_type["ip_log"].append("IP address column and access log headers detected")
    if "ip" in fn_lower or "log" in fn_lower:
        scores["ip_log"] = min(1.0, scores["ip_log"] + 0.2)

    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_conf = sorted_types[0]

    # For PDF files: if no structured table columns matched strongly, treat as unstructured text_document (e.g. FIR PDF)
    if fn_lower.endswith(".pdf") and (not records or best_conf < 0.40):
        return {
            "detected_type": "text_document",
            "confidence": 0.95,
            "alternatives": [{"type": t, "score": round(s, 2)} for t, s in sorted_types if s > 0.15],
            "reasons": ["PDF lacks high-confidence tabular structure; routed as text document"],
        }

    if best_conf < 0.25:
        best_type = "unknown"
        best_conf = 0.2
        reasons = ["Insufficient header or content pattern matches"]
    else:
        reasons = reasons_by_type.get(best_type, []) or [f"Matched {best_type} via composite header/content profile"]

    alternatives = [{"type": t, "score": round(s, 2)} for t, s in sorted_types[1:] if s > 0.15]

    return {
        "detected_type": best_type,
        "confidence": round(best_conf, 2),
        "alternatives": alternatives,
        "reasons": reasons,
    }


def detect_file_sections(
    file_metadata: Dict[str, Any],
    primary_headers: List[str],
    primary_records: List[Dict[str, Any]],
    filename: str = "",
    banners: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Analyzes multi-section files or multi-sheet Excel workbooks to classify each separable section/sheet.
    """
    typed_sections: List[Dict[str, Any]] = []

    if file_metadata.get("is_mixed_file") and file_metadata.get("sections"):
        for sec in file_metadata["sections"]:
            det = detect_file_type(sec["headers"], sec["records"], filename="", banners=sec.get("banner_rows"))
            typed_sections.append({
                "section_index": sec["section_index"],
                "headers": sec["headers"],
                "row_count": len(sec["records"]),
                "detected_type": det["detected_type"],
                "confidence": det["confidence"],
                "reasons": det["reasons"],
            })
    elif file_metadata.get("sheets") and len(file_metadata["sheets"]) > 1:
        for idx, sh in enumerate(file_metadata["sheets"]):
            det = detect_file_type(sh["headers"], sh["records"], filename="", banners=sh.get("banner_rows"))
            typed_sections.append({
                "section_index": idx,
                "sheet_name": sh["sheet_name"],
                "headers": sh["headers"],
                "row_count": sh["row_count"],
                "detected_type": det["detected_type"],
                "confidence": det["confidence"],
                "reasons": det["reasons"],
            })

    distinct_types = {s["detected_type"] for s in typed_sections if s["detected_type"] != "unknown"}
    return {
        "has_multiple_sections": len(typed_sections) > 1,
        "has_multiple_record_types": len(distinct_types) > 1,
        "sections": typed_sections,
    }
