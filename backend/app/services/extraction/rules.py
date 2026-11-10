import json
import re
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.app.config import get_extraction_config, get_fir_patterns, get_ipc_bns_map
from backend.app.services.ingestion.normalize import (
    normalize_phone,
    normalize_amount,
    normalize_datetime,
    normalize_account,
    normalize_vehicle,
    normalize_ip,
    to_ascii_digits,
    validate_aadhaar,
    validate_pan,
    validate_ifsc,
    validate_imei,
    validate_upi_vpa,
    validate_vehicle,
    classify_numeric_identifier,
)

PHONE_REGEX = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")
VEHICLE_REGEX = re.compile(r"\b([A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4}|\d{2}[ -]?BH[ -]?\d{4}[ -]?[A-Z]{1,2})\b")
EMAIL_REGEX = re.compile(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
IP_REGEX = re.compile(r"\b((?:[0-9]{1,3}\.){3}[0-9]{1,3})\b")
UPI_REGEX = re.compile(r"\b([a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9]{2,})(?!\.[a-zA-Z0-9])\b")
PAN_DOC_REGEX = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
IFSC_DOC_REGEX = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
AADHAAR_DOC_REGEX = re.compile(r"(?<!\d)([2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4})(?!\d)")
IMEI_TRIGGER_REGEX = re.compile(r"\b(?:IMEI(?:\s*No\.?)?|device\s*id)\s*[:\-]?\s*(\d{15})\b", re.IGNORECASE)

FIR_REGEX = re.compile(
    r"\bFIR\s*(?:No\.?|Number)?\s*[:\-\s]\s*([0-9]{3,6}[\/\-][0-9]{2,4}|[A-Z0-9\/\-]{4,15})\b|\b(FIR[_\-]\d{3,6}[_\-]\d{2,4})\b",
    re.IGNORECASE,
)
PS_REGEX = re.compile(
    r"\b(?:Police\s+Station|P\.S\.|PS)\s*[:\-]?\s*([A-Za-z\s]{3,30}?)(?=[,.\n]|\s+dated|\s+district|\s+under|\s+FIR|\s+IO|\s+Date|\s+Entry)",
    re.IGNORECASE,
)
PS_SUFFIX_REGEX = re.compile(
    r"\b([A-Z][a-zA-Z]{2,20}(?:\s+[A-Z][a-zA-Z]{2,20}){0,2})\s+(?:P\.S\.|Police\s+Station)\b"
)

# Account keywords trigger for 9-18 digit numbers within 40 characters
ACCOUNT_TRIGGER_REGEX = re.compile(
    r"(?:account(?:\s*no\.?)?|a/c(?:\s*no\.?)?|acct|beneficiary(?:\s+a/c)?|remitter(?:\s+a/c)?)\s*[:\-]?\s*([A-Za-z0-9]{9,18})\b",
    re.IGNORECASE,
)

# Account suffix / masked patterns (e.g. XXXXXX7890, ending 7890, last digits 6338)
MASKED_ACCOUNT_REGEX = re.compile(
    r"(?:[X*]{4,12}(\d{4})|"
    r"(?:account|a/c|digits)[\w\s]{0,35}?(?:ending(?:\s+in|\s+with)?|last\s+digits(?:\s+are|\s+of)?|digits\s+are)\s*[:\-]?\s*(\d{4,6}))\b",
    re.IGNORECASE,
)

# Masked phone pattern in narrative text (e.g., mobile XXXXXX3210 or +91-98XXXX3210)
MASKED_PHONE_DOC_REGEX = re.compile(
    r"(?:\b(?:mobile|phone|contact|number|no\.?)\s*[:\-]?\s*)((?:\+?91[\s\-]?)?(?:\d{0,4}[X*]{2,8}\d{2,5}))\b",
    re.IGNORECASE,
)

# Amount patterns supporting Indian units (lakh, crore, paise, Cash Rs. ...) and bracket negatives
AMOUNT_REGEX = re.compile(
    r"\(\s*(?:Rs\.?|INR|₹)?\s*[\d,]+(?:\.\d+)?\s*\)|"
    r"\b(?:Cash[^\S\r\n]+)?(?:Rs\.?|INR|₹)[^\S\r\n]*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)?(?:\s*\/-)?\b|"
    r"\b(?:Cash[^\S\r\n]+)([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)?(?:\s*(?:INR|rupees))?(?:\s*\/-)?\b|"
    r"\b([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)\s*(?:rupees|INR)?(?:\s*\/-)?\b",
    re.IGNORECASE,
)

# Date patterns (dd/mm/yyyy, yyyy-mm-dd, 15th January 2024, etc.)
DATE_REGEX = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?)\b|"
    r"\b(\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)\b|"
    r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
    re.IGNORECASE,
)


def extract_rule_entities(text: str, page_or_para: str, base_char_offset: int = 0) -> List[Dict[str, Any]]:
    """
    Runs deterministic pattern extraction on text for structured identifiers,
    delegating validation, Unicode numeral normalization, and context-aware
    disambiguation to `backend.app.services.ingestion.validators`.
    Returns list of extracted entities with exact character spans and confidences.
    """
    if not text:
        return []

    # 1:1 length-preserving conversion of Devanagari/Indic digits to ASCII '0'-'9'
    ascii_text = to_ascii_digits(text)

    results: List[Dict[str, Any]] = []
    found_phones_raw: Set[str] = set()
    claimed_spans: List[Tuple[int, int]] = []
    found_account_digits: Set[str] = set()

    def _overlaps_claimed(s_idx: int, e_idx: int) -> bool:
        return any(not (e_idx <= s or s_idx >= e) for s, e in claimed_spans)

    # 1. BANK ACCOUNTS (within ~40 chars of account triggers)
    for m in ACCOUNT_TRIGGER_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw_val = text[s_local:e_local].strip()
        ascii_val = m.group(1).strip()
        cleaned_digits = re.sub(r"\D", "", ascii_val)
        if cleaned_digits and len(cleaned_digits) >= 9:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            claimed_spans.append((start, end))
            found_account_digits.add(cleaned_digits)
            results.append({
                "entity_type": "BANK_ACCOUNT",
                "raw_value": raw_val,
                "normalized_value": normalize_account(raw_val),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex",
            })

    # 2. AADHAAR NUMBERS (12 digits with Verhoeff checksum or UID context)
    for m in AADHAAR_DOC_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        start = base_char_offset + s_local
        end = base_char_offset + e_local
        if _overlaps_claimed(start, end):
            continue
        raw_val = text[s_local:e_local].strip()
        window_ctx = ascii_text[max(0, s_local - 45) : min(len(ascii_text), e_local + 25)]
        cls_res = classify_numeric_identifier(raw_val, context=window_ctx)
        if cls_res["ok"] and cls_res["entity_type"] == "AADHAAR":
            uid_check = validate_aadhaar(raw_val)
            if uid_check["ok"]:
                claimed_spans.append((start, end))
                results.append({
                    "entity_type": "AADHAAR",
                    "raw_value": raw_val,
                    "normalized_value": uid_check["normalized"],
                    "char_span_start": start,
                    "char_span_end": end,
                    "page_or_paragraph": page_or_para,
                    "confidence": cls_res["confidence"],
                    "method": "regex",
                    "needs_review": cls_res.get("needs_review", False),
                    "candidate_types": cls_res.get("candidate_types", []),
                    "meta": uid_check["meta"],
                })
        elif cls_res["ok"] and cls_res["entity_type"] == "BANK_ACCOUNT" and re.search(
            r"\b(?:account|a/c|acct|beneficiary|remitter)\b", window_ctx, re.IGNORECASE
        ):
            digits = cls_res["normalized"]
            if digits not in found_account_digits:
                found_account_digits.add(digits)
                claimed_spans.append((start, end))
                results.append({
                    "entity_type": "BANK_ACCOUNT",
                    "raw_value": raw_val,
                    "normalized_value": digits,
                    "char_span_start": start,
                    "char_span_end": end,
                    "page_or_paragraph": page_or_para,
                    "confidence": 0.90,
                    "method": "regex",
                })

    # 3. PHONE NUMBERS (context-aware disambiguation against BANK_ACCOUNT)
    for m in PHONE_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(), m.end()
        start = base_char_offset + s_local
        end = base_char_offset + e_local
        if _overlaps_claimed(start, end):
            continue

        raw = text[s_local:e_local].strip()
        preceding_context = ascii_text[max(0, s_local - 45) : s_local]
        cls_res = classify_numeric_identifier(raw, context=preceding_context)

        if cls_res["ok"] and cls_res["entity_type"] == "BANK_ACCOUNT":
            cleaned_digits = cls_res["normalized"]
            if cleaned_digits not in found_account_digits:
                found_account_digits.add(cleaned_digits)
                claimed_spans.append((start, end))
                results.append({
                    "entity_type": "BANK_ACCOUNT",
                    "raw_value": raw,
                    "normalized_value": normalize_account(raw),
                    "char_span_start": start,
                    "char_span_end": end,
                    "page_or_paragraph": page_or_para,
                    "confidence": 0.90,
                    "method": "regex",
                })
            continue

        norm_res = normalize_phone(raw)
        if norm_res and norm_res.get("valid_mobile"):
            claimed_spans.append((start, end))
            found_phones_raw.add(norm_res["number"])
            results.append({
                "entity_type": "PHONE",
                "raw_value": raw,
                "normalized_value": norm_res["number"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95,
                "method": "regex",
                "meta": norm_res,
            })

    # 3b. MASKED PHONE NUMBERS (e.g. mobile XXXXXX3210)
    for m in MASKED_PHONE_DOC_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        start = base_char_offset + s_local
        end = base_char_offset + e_local
        if _overlaps_claimed(start, end):
            continue
        raw = text[s_local:e_local].strip()
        norm_res = normalize_phone(raw)
        if norm_res and norm_res.get("is_masked"):
            claimed_spans.append((start, end))
            results.append({
                "entity_type": "PHONE",
                "raw_value": raw,
                "normalized_value": norm_res["number"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.50,
                "method": "regex",
                "needs_review": True,
                "meta": norm_res,
            })

    # 4. ACCOUNT SUFFIX (masked/partial accounts -> BankAccount node)
    for m in MASKED_ACCOUNT_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(), m.end()
        start = base_char_offset + s_local
        end = base_char_offset + e_local
        if _overlaps_claimed(start, end):
            continue
        raw = text[s_local:e_local].strip()
        last4 = m.group(1) or m.group(2)
        claimed_spans.append((start, end))
        results.append({
            "entity_type": "ACCOUNT_SUFFIX",
            "raw_value": raw,
            "normalized_value": f"ENDING_{last4}",
            "char_span_start": start,
            "char_span_end": end,
            "page_or_paragraph": page_or_para,
            "confidence": 0.40,
            "method": "regex",
        })

    # 5. VEHICLES (via validate_vehicle with state_code metadata)
    for m in VEHICLE_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        veh_res = validate_vehicle(raw)
        norm_v = veh_res["normalized"] or normalize_vehicle(raw)
        if norm_v:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "VEHICLE",
                "raw_value": raw,
                "normalized_value": norm_v,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex",
                "meta": veh_res.get("meta", {}),
            })

    # 6. AMOUNTS (via normalize_amount / validate_amount)
    for m in AMOUNT_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(), m.end()
        raw = text[s_local:e_local].strip()
        paise_val = normalize_amount(raw)
        if paise_val is not None and paise_val != 0:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "AMOUNT",
                "raw_value": raw,
                "normalized_value": str(paise_val),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex",
            })

    # 7. DATES (via timezone-safe normalize_datetime)
    date_matches = list(DATE_REGEX.finditer(ascii_text))
    date_samples = [m.group(0).strip() for m in date_matches]
    from backend.app.services.ingestion.validators import infer_column_dayfirst
    inferred_df, _ = infer_column_dayfirst(date_samples)

    for m in date_matches:
        s_local, e_local = m.start(), m.end()
        raw = text[s_local:e_local].strip()
        d_str, t_str, iso_str = normalize_datetime(raw, dayfirst=inferred_df)
        if iso_str or d_str:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "DATE",
                "raw_value": raw,
                "normalized_value": iso_str or d_str,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex",
            })

    # 8. EMAILS
    for m in EMAIL_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        start = base_char_offset + s_local
        end = base_char_offset + e_local
        results.append({
            "entity_type": "EMAIL",
            "raw_value": raw,
            "normalized_value": to_ascii_digits(raw).lower(),
            "char_span_start": start,
            "char_span_end": end,
            "page_or_paragraph": page_or_para,
            "confidence": 0.95,
            "method": "regex",
        })

    # 9. IP ADDRESSES
    for m in IP_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        ip_val, is_valid = normalize_ip(raw)
        if is_valid:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "IP",
                "raw_value": raw,
                "normalized_value": ip_val,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex",
            })

    # 10. UPI IDS (via validate_upi_vpa)
    for m in UPI_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        vpa_res = validate_upi_vpa(raw)
        if vpa_res["ok"]:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "UPI",
                "raw_value": raw,
                "normalized_value": vpa_res["normalized"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex",
                "meta": vpa_res["meta"],
            })

    # 11. PAN, IFSC & IMEI
    for m in PAN_DOC_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        pan_res = validate_pan(raw)
        if pan_res["ok"]:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "PAN",
                "raw_value": raw,
                "normalized_value": pan_res["normalized"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.92,
                "method": "regex",
                "meta": pan_res["meta"],
            })

    for m in IFSC_DOC_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        ifsc_res = validate_ifsc(raw)
        if ifsc_res["ok"]:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "IFSC",
                "raw_value": raw,
                "normalized_value": ifsc_res["normalized"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95 if ifsc_res["meta"].get("known_bank") else 0.85,
                "method": "regex",
                "meta": ifsc_res["meta"],
            })

    for m in IMEI_TRIGGER_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(1), m.end(1)
        raw = text[s_local:e_local].strip()
        imei_res = validate_imei(raw)
        if imei_res["ok"]:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "IMEI",
                "raw_value": raw,
                "normalized_value": imei_res["normalized"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95,
                "method": "regex",
                "meta": imei_res["meta"],
            })

    # 12. FIR NUMBER
    for m in FIR_REGEX.finditer(ascii_text):
        grp_idx = 1 if m.group(1) else 2
        s_local, e_local = m.start(grp_idx), m.end(grp_idx)
        raw_fir = text[s_local:e_local].strip()
        ascii_fir = m.group(grp_idx).strip()
        if raw_fir:
            start = base_char_offset + s_local
            end = base_char_offset + e_local
            results.append({
                "entity_type": "FIR",
                "raw_value": raw_fir,
                "normalized_value": ascii_fir.upper(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95,
                "method": "regex",
            })

    # 13. POLICE STATION
    ps_spans: List[Tuple[int, int]] = []
    excluded_ps_words = [
        "registered", "reported", "informed", "sent to", "about", "near",
        "under", "dated", "district", "at", "to", "from", "the", "in", "case", "for",
    ]
    for m in PS_REGEX.finditer(ascii_text):
        ps_name = m.group(1).strip()
        ps_lower = ps_name.lower()
        if ps_name and len(ps_name) >= 3 and not any(
            ps_lower.startswith(w) or ps_lower == w for w in excluded_ps_words
        ):
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            ps_spans.append((start, end))
            results.append({
                "entity_type": "POLICE_STATION",
                "raw_value": ps_name,
                "normalized_value": ps_name.title(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex",
            })

    for m in PS_SUFFIX_REGEX.finditer(ascii_text):
        ps_name = m.group(1).strip()
        ps_lower = ps_name.lower()
        start = base_char_offset + m.start(1)
        end = base_char_offset + m.end(1)
        if any(not (end <= s or start >= e) for s, e in ps_spans):
            continue
        if ps_name and len(ps_name) >= 3 and not any(
            ps_lower.startswith(w) or ps_lower == w for w in excluded_ps_words
        ):
            ps_spans.append((start, end))
            results.append({
                "entity_type": "POLICE_STATION",
                "raw_value": ps_name,
                "normalized_value": ps_name.title(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex",
            })

    # 14. LEGAL SECTIONS (IPC / BNS / BNSS / CrPC / IT Act with reference mapping)
    for sec_item in extract_legal_sections(text, page_or_para, base_char_offset=base_char_offset):
        results.append(sec_item)

    return results


# Legal section regexes supporting English and Hinglish (e.g. u/s 420, 406 IPC, Section 318(4) BNS, dhara 420 IPC, 66D IT Act)
_SECTION_LIST_BEFORE_ACT_REGEX = re.compile(
    r"\b(?:u/s|under\s+sections?|sections?|sec\.?|dhara)\s*[:\-]?\s*"
    r"([0-9]{1,3}[A-Z]?(?:\([0-9A-Za-z]+\))?(?:\s*(?:,|/|\band\b|\br/w\b)\s*[0-9]{1,3}[A-Z]?(?:\([0-9A-Za-z]+\))?)*)"
    r"\s*(?:of\s+(?:the\s+)?)?\b(IPC|I\.P\.C\.|BNS(?:\s*2023)?|BNSS(?:\s*2023)?|CrPC|Cr\.P\.C\.|IT\s*Act(?:\s*2000)?)\b",
    re.IGNORECASE,
)

_ACT_BEFORE_SECTION_REGEX = re.compile(
    r"\b(IPC|I\.P\.C\.|BNS(?:\s*2023)?|BNSS(?:\s*2023)?|CrPC|Cr\.P\.C\.|IT\s*Act(?:\s*2000)?)\s*"
    r"(?:sections?|sec\.?|dhara|u/s)?\s*[:\-]?\s*"
    r"([0-9]{1,3}[A-Z]?(?:\([0-9A-Za-z]+\))?(?:\s*(?:,|/|\band\b)\s*[0-9]{1,3}[A-Z]?(?:\([0-9A-Za-z]+\))?)*)\b",
    re.IGNORECASE,
)

_INDIVIDUAL_SECTION_TOKEN_REGEX = re.compile(r"([0-9]{1,3}[A-Z]?(?:\([0-9A-Za-z]+\))?)", re.IGNORECASE)


def _canonical_act_name(raw_act: str) -> str:
    up = re.sub(r"[\s.]+", "", raw_act.upper())
    if up.startswith("IPC"):
        return "IPC"
    if up.startswith("BNSS"):
        return "BNSS"
    if up.startswith("BNS"):
        return "BNS"
    if up.startswith("CRPC"):
        return "CrPC"
    if "ITACT" in up:
        return "IT Act"
    return raw_act.strip().upper()


def resolve_legal_section_mapping(act: str, section_code: str) -> Dict[str, Any]:
    """
    Looks up `act` + `section_code` in `backend/config/reference/ipc_bns_map.json`.
    - Returns both the original and mapped section when a mapping exists.
    - Returns `mapping_status="mapping unavailable"` when no mapping exists in the reference file.
    - Never invents mappings. Always carries the official gazette verification disclaimer.
    """
    ref = get_ipc_bns_map() or {}
    meta = ref.get("_meta", {}) or {}
    disclaimer = str(meta.get("disclaimer") or "reference — verify against the official gazette")
    canon_act = _canonical_act_name(act)
    sec_norm = section_code.strip().upper()
    # Normalize parenthetical suffixes like 318(4) vs 120B
    sec_norm = re.sub(r"\s+", "", sec_norm)

    if canon_act == "IPC":
        ipc_map = ref.get("ipc_to_bns", {}) or {}
        entry = ipc_map.get(sec_norm)
        if entry:
            bns_sec = entry.get("bns_section")
            return {
                "act": "IPC",
                "section": sec_norm,
                "mapped_act": "BNS",
                "mapped_section": bns_sec,
                "title": entry.get("title"),
                "mapping_status": "mapped",
                "display_label": f"IPC {sec_norm} <-> BNS {bns_sec}",
                "disclaimer": disclaimer,
            }
    elif canon_act == "BNS":
        bns_map = ref.get("bns_to_ipc", {}) or {}
        entry = bns_map.get(sec_norm)
        if entry:
            ipc_sec = entry.get("ipc_section")
            return {
                "act": "BNS",
                "section": sec_norm,
                "mapped_act": "IPC",
                "mapped_section": ipc_sec,
                "title": entry.get("title"),
                "mapping_status": "mapped",
                "display_label": f"BNS {sec_norm} <-> IPC {ipc_sec}",
                "disclaimer": disclaimer,
            }
    elif canon_act == "CrPC":
        crpc_map = ref.get("crpc_to_bnss", {}) or {}
        entry = crpc_map.get(sec_norm)
        if entry:
            bnss_sec = entry.get("bnss_section")
            return {
                "act": "CrPC",
                "section": sec_norm,
                "mapped_act": "BNSS",
                "mapped_section": bnss_sec,
                "title": entry.get("title"),
                "mapping_status": "mapped",
                "display_label": f"CrPC {sec_norm} <-> BNSS {bnss_sec}",
                "disclaimer": disclaimer,
            }
    elif canon_act == "BNSS":
        bnss_map = ref.get("bnss_to_crpc", {}) or {}
        entry = bnss_map.get(sec_norm)
        if entry:
            crpc_sec = entry.get("crpc_section")
            return {
                "act": "BNSS",
                "section": sec_norm,
                "mapped_act": "CrPC",
                "mapped_section": crpc_sec,
                "title": entry.get("title"),
                "mapping_status": "mapped",
                "display_label": f"BNSS {sec_norm} <-> CrPC {crpc_sec}",
                "disclaimer": disclaimer,
            }
    elif canon_act == "IT Act":
        it_map = ref.get("it_act", {}) or {}
        entry = it_map.get(sec_norm)
        if entry:
            return {
                "act": "IT Act",
                "section": sec_norm,
                "mapped_act": None,
                "mapped_section": None,
                "title": entry.get("title"),
                "mapping_status": "known_statute",
                "display_label": f"IT Act {sec_norm}",
                "disclaimer": disclaimer,
            }

    return {
        "act": canon_act,
        "section": sec_norm,
        "mapped_act": None,
        "mapped_section": None,
        "title": None,
        "mapping_status": "mapping unavailable",
        "display_label": f"{canon_act} {sec_norm} (mapping unavailable)",
        "disclaimer": disclaimer,
    }


def extract_legal_sections(
    text: str,
    page_or_para: str = "Page 1",
    base_char_offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Extracts IPC, BNS, BNSS, CrPC, and IT Act section mentions from text
    (supporting Devanagari digits and Hinglish `dhara` / `u/s` phrasing)
    and attaches the reference mapping from `ipc_bns_map.json`.
    """
    if not text:
        return []

    ascii_text = to_ascii_digits(text)
    sections_out: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str]] = set()

    def _process_match(sec_blob: str, raw_act: str, match_start: int, match_end: int):
        canon_act = _canonical_act_name(raw_act)
        for tok_m in _INDIVIDUAL_SECTION_TOKEN_REGEX.finditer(sec_blob):
            sec_code = tok_m.group(1).strip().upper()
            if not sec_code or sec_code in ("2023", "2000", "1860", "1973"):
                continue
            key = (canon_act, sec_code)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            mapping_info = resolve_legal_section_mapping(canon_act, sec_code)
            s_idx = base_char_offset + match_start
            e_idx = base_char_offset + match_end
            raw_slice = text[match_start:match_end].strip()

            sections_out.append({
                "entity_type": "LEGAL_SECTION",
                "raw_value": raw_slice,
                "normalized_value": f"{canon_act} {sec_code}",
                "char_span_start": s_idx,
                "char_span_end": e_idx,
                "page_or_paragraph": page_or_para,
                "confidence": 0.94,
                "method": "regex",
                "meta": mapping_info,
            })

    for m in _SECTION_LIST_BEFORE_ACT_REGEX.finditer(ascii_text):
        _process_match(m.group(1), m.group(2), m.start(), m.end())

    for m in _ACT_BEFORE_SECTION_REGEX.finditer(ascii_text):
        _process_match(m.group(2), m.group(1), m.start(), m.end())

    return sections_out


def extract_incident_facts(
    text: str,
    page_or_para: str = "Page 1",
    base_char_offset: int = 0,
    extracted_entities: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Extracts structured FIR `document_fact` records and an incident timeline with exact character spans:
    - `fir_no`, `police_station`, `incident_date` (parsed with Phase 1 dayfirst + IST rules),
      `incident_time`, `incident_place`, `complainant`, `accused`, `witnesses`, `sections`.
    - Returns both a `facts` list (ready for the Phase 3 Merge Engine as `document_fact` records)
      and a chronological `timeline` list.
    """
    if not text:
        return {"facts": [], "by_key": {}, "timeline": [], "sections": []}

    ascii_text = to_ascii_digits(text)
    fir_cfg = get_fir_patterns() or {}
    fact_patterns = fir_cfg.get("incident_fact_patterns", {}) or {}

    entities = extracted_entities if extracted_entities is not None else extract_rule_entities(text, page_or_para, base_char_offset)
    from backend.app.services.ingestion.validators import infer_column_dayfirst

    all_date_matches = [m.group(0).strip() for m in DATE_REGEX.finditer(ascii_text)]
    inferred_df, _ = infer_column_dayfirst(all_date_matches)

    facts: List[Dict[str, Any]] = []
    by_key: Dict[str, Any] = {}

    def _add_fact(
        fact_key: str,
        raw_val: str,
        norm_val: Any,
        span_start: int,
        span_end: int,
        conf: float = 0.90,
        extra_meta: Optional[Dict[str, Any]] = None,
    ):
        fact_obj = {
            "fact_key": fact_key,
            "raw_value": raw_val,
            "normalized_value": norm_val,
            "char_span_start": span_start,
            "char_span_end": span_end,
            "page_or_paragraph": page_or_para,
            "confidence": conf,
            "method": "regex",
            "meta": extra_meta or {},
        }
        facts.append(fact_obj)
        if fact_key not in by_key:
            by_key[fact_key] = fact_obj

    # 1. FIR Number
    fir_ents = [e for e in entities if e.get("entity_type") == "FIR"]
    if fir_ents:
        fe = fir_ents[0]
        _add_fact("fir_no", fe["raw_value"], fe["normalized_value"], fe["char_span_start"], fe["char_span_end"], fe.get("confidence", 0.95))

    # 2. Police Station
    ps_ents = [e for e in entities if e.get("entity_type") == "POLICE_STATION"]
    if ps_ents:
        pe = ps_ents[0]
        _add_fact("police_station", pe["raw_value"], pe["normalized_value"], pe["char_span_start"], pe["char_span_end"], pe.get("confidence", 0.88))

    # 3. Incident Date (prefer contextual incident date pattern, fallback to first DATE entity)
    incident_date_found = False
    for pat in fact_patterns.get("incident_date_context", []) or []:
        m = re.search(pat, ascii_text, re.IGNORECASE)
        if m:
            raw_dt = text[m.start(1) : m.end(1)].strip()
            d_str, t_str, iso_str = normalize_datetime(raw_dt, dayfirst=inferred_df)
            if iso_str or d_str:
                _add_fact(
                    "incident_date",
                    raw_dt,
                    iso_str or d_str,
                    base_char_offset + m.start(1),
                    base_char_offset + m.end(1),
                    conf=0.92,
                    extra_meta={"date_only": d_str, "time_only": t_str, "dayfirst": inferred_df},
                )
                incident_date_found = True
                if t_str:
                    _add_fact(
                        "incident_time",
                        raw_dt,
                        t_str,
                        base_char_offset + m.start(1),
                        base_char_offset + m.end(1),
                        conf=0.90,
                    )
                break

    if not incident_date_found:
        date_ents = [e for e in entities if e.get("entity_type") == "DATE"]
        if date_ents:
            de = date_ents[0]
            _add_fact("incident_date", de["raw_value"], de["normalized_value"], de["char_span_start"], de["char_span_end"], de.get("confidence", 0.85))

    # 4. Incident Time (if not already extracted with incident_date)
    if "incident_time" not in by_key:
        for pat in fact_patterns.get("incident_time", []) or []:
            m = re.search(pat, ascii_text, re.IGNORECASE)
            if m:
                raw_tm = text[m.start(1) : m.end(1)].strip()
                _add_fact(
                    "incident_time",
                    raw_tm,
                    to_ascii_digits(raw_tm),
                    base_char_offset + m.start(1),
                    base_char_offset + m.end(1),
                    conf=0.86,
                )
                break

    # 5. Incident Place
    for pat in fact_patterns.get("incident_place", []) or []:
        m = re.search(pat, ascii_text, re.IGNORECASE)
        if m:
            raw_pl = text[m.start(1) : m.end(1)].strip(" ,.;")
            if len(raw_pl) >= 3:
                _add_fact(
                    "incident_place",
                    raw_pl,
                    raw_pl,
                    base_char_offset + m.start(1),
                    base_char_offset + m.end(1),
                    conf=0.88,
                )
                break

    # 6. Complainant / Accused / Witness from extracted person entities (or role rules fallback)
    person_ents = [e for e in entities if e.get("entity_type") == "PERSON"]
    complainants = [
        p
        for p in person_ents
        if (p.get("role") or (p.get("meta") or {}).get("role")) in ("complainant", "victim")
    ]
    if complainants:
        cp = complainants[0]
        _add_fact("complainant", cp["raw_value"], cp["normalized_value"], cp["char_span_start"], cp["char_span_end"], cp.get("confidence", 0.92))
    else:
        for rule in fir_cfg.get("role_rules", []) or []:
            if str(rule.get("role")) == "complainant" and rule.get("pattern"):
                m_cp = re.search(rule["pattern"], text, re.IGNORECASE)
                if m_cp:
                    from backend.app.services.extraction.ner import clean_person_name

                    raw_cp = clean_person_name(m_cp.group(1))
                    if raw_cp:
                        _add_fact(
                            "complainant",
                            raw_cp,
                            raw_cp.lower(),
                            base_char_offset + m_cp.start(1),
                            base_char_offset + m_cp.end(1),
                            conf=float(rule.get("confidence", 0.92)),
                        )
                        break

    # 7. Legal Sections (IPC / BNS / BNSS / CrPC / IT Act)
    sec_ents = [e for e in entities if e.get("entity_type") == "LEGAL_SECTION"]
    if not sec_ents:
        sec_ents = extract_legal_sections(text, page_or_para, base_char_offset=base_char_offset)
    if sec_ents:
        sec_labels = [s["normalized_value"] for s in sec_ents]
        sec_mappings = [s.get("meta", {}) for s in sec_ents]
        _add_fact(
            "sections",
            ", ".join(s["raw_value"] for s in sec_ents),
            ", ".join(sec_labels),
            sec_ents[0]["char_span_start"],
            sec_ents[-1]["char_span_end"],
            conf=0.94,
            extra_meta={"sections": sec_mappings},
        )

    # 8. Build Chronological Incident Timeline from sentence-level dated events
    timeline: List[Dict[str, Any]] = []
    for m in DATE_REGEX.finditer(ascii_text):
        s_local, e_local = m.start(), m.end()
        raw_dt = text[s_local:e_local].strip()
        d_str, t_str, iso_str = normalize_datetime(raw_dt, dayfirst=inferred_df)
        if not (iso_str or d_str):
            continue

        # Grab enclosing sentence around the date mention
        sent_start = max(0, ascii_text.rfind(".", 0, s_local) + 1, ascii_text.rfind("\n", 0, s_local) + 1)
        next_dot = ascii_text.find(".", e_local)
        next_nl = ascii_text.find("\n", e_local)
        candidates_end = [x for x in (next_dot, next_nl) if x != -1]
        sent_end = min(candidates_end) if candidates_end else len(ascii_text)
        sentence_txt = text[sent_start:sent_end].strip()
        low_sent = sentence_txt.lower()

        event_type = "narrative_event"
        if any(w in low_sent for w in ["fir", "registered", "reported at police station", "lodged"]):
            event_type = "fir_registration"
        elif any(w in low_sent for w in ["transfer", "sent", "paid", "debited", "credited", "rs", "inr", "upi", "rtgs", "neft"]):
            event_type = "financial_transfer"
        elif any(w in low_sent for w in ["call", "contacted", "mobile", "phone", "whatsapp", "sms"]):
            event_type = "communication_event"
        elif any(w in low_sent for w in ["occurred", "incident", "took place", "cheated", "stolen", "seized"]):
            event_type = "incident_occurrence"

        timeline.append({
            "timestamp_iso": iso_str or d_str,
            "date_only": d_str,
            "time_only": t_str,
            "raw_date": raw_dt,
            "event_type": event_type,
            "description": sentence_txt[:240],
            "char_span_start": base_char_offset + sent_start,
            "char_span_end": base_char_offset + sent_end,
            "page_or_paragraph": page_or_para,
        })

    timeline.sort(key=lambda x: str(x.get("timestamp_iso") or ""))

    return {
        "facts": facts,
        "by_key": by_key,
        "timeline": timeline,
        "sections": [s.get("meta", {}) for s in sec_ents],
    }


def compute_fir_completeness(
    facts_result: Dict[str, Any],
    extracted_entities: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluates per-FIR completeness against `extraction.completeness.required_fields.fir` in `defaults.yaml`
    (complainant, incident_date, incident_place, sections, fir_no, police_station, and at least one identifier).
    Returns what is present, what is missing, and a completeness score in [0.0, 1.0].
    """
    ext_cfg = get_extraction_config() or {}
    req_fields: List[str] = (
        ext_cfg.get("completeness", {})
        .get("required_fields", {})
        .get(
            "fir",
            [
                "fir_no",
                "police_station",
                "incident_date",
                "incident_place",
                "complainant",
                "sections",
                "identifier",
            ],
        )
    )

    by_key = facts_result.get("by_key", {}) or {}
    identifier_types = {
        "PHONE",
        "BANK_ACCOUNT",
        "ACCOUNT_SUFFIX",
        "VEHICLE",
        "UPI",
        "AADHAAR",
        "PAN",
        "IFSC",
        "IMEI",
        "EMAIL",
        "IP",
    }
    has_identifier = any(e.get("entity_type") in identifier_types for e in extracted_entities)
    has_complainant = bool(by_key.get("complainant")) or any(
        e.get("entity_type") == "PERSON" and e.get("role") in ("complainant", "victim")
        for e in extracted_entities
    )
    has_sections = bool(by_key.get("sections")) or any(
        e.get("entity_type") == "LEGAL_SECTION" for e in extracted_entities
    )
    has_date = bool(by_key.get("incident_date")) or any(
        e.get("entity_type") == "DATE" for e in extracted_entities
    )
    has_fir_no = bool(by_key.get("fir_no")) or any(
        e.get("entity_type") == "FIR" for e in extracted_entities
    )
    has_ps = bool(by_key.get("police_station")) or any(
        e.get("entity_type") == "POLICE_STATION" for e in extracted_entities
    )
    has_place = bool(by_key.get("incident_place"))

    availability_map = {
        "fir_no": has_fir_no,
        "police_station": has_ps,
        "incident_date": has_date,
        "date": has_date,
        "incident_place": has_place,
        "place": has_place,
        "complainant": has_complainant,
        "sections": has_sections,
        "identifier": has_identifier,
    }

    present: List[str] = []
    missing: List[str] = []
    for field_name in req_fields:
        is_ok = bool(availability_map.get(field_name, bool(by_key.get(field_name))))
        if is_ok:
            present.append(field_name)
        else:
            missing.append(field_name)

    total_req = max(1, len(req_fields))
    score = round(len(present) / total_req, 4)
    return {
        "required_fields": req_fields,
        "present_fields": present,
        "missing_fields": missing,
        "is_complete": len(missing) == 0,
        "completeness_score": score,
    }

