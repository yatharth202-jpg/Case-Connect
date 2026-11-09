import re
from typing import Dict, Any, List, Set, Tuple
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

    return results
