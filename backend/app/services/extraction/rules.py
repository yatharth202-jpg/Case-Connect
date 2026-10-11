import re
from decimal import Decimal
from typing import Dict, Any, List, Set, Tuple
from backend.app.services.ingestion.normalize import (
    normalize_phone, normalize_amount, normalize_datetime,
    normalize_account, normalize_vehicle, normalize_ip
)

PHONE_REGEX = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)')
VEHICLE_REGEX = re.compile(r'\b([A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4})\b')
EMAIL_REGEX = re.compile(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b')
IP_REGEX = re.compile(r'\b((?:[0-9]{1,3}\.){3}[0-9]{1,3})\b')
UPI_REGEX = re.compile(r'\b([a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9]{2,})(?!\.[a-zA-Z0-9])\b')
FIR_REGEX = re.compile(
    r'\bFIR\s*(?:No\.?|Number)?\s*[:\-\s]\s*([0-9]{3,6}[\/\-][0-9]{2,4}|[A-Z0-9\/\-]{4,15})\b|\b(FIR[_\-]\d{3,6}[_\-]\d{2,4})\b',
    re.IGNORECASE
)
PS_REGEX = re.compile(
    r'\b(?:Police\s+Station|P\.S\.|PS)\s*[:\-]?\s*([A-Za-z\s]{3,30}?)(?=[,.\n]|\s+dated|\s+district|\s+under|\s+FIR|\s+IO|\s+Date|\s+Entry)',
    re.IGNORECASE
)
PS_SUFFIX_REGEX = re.compile(
    r'\b([A-Z][a-zA-Z]{2,20}(?:\s+[A-Z][a-zA-Z]{2,20}){0,2})\s+(?:P\.S\.|Police\s+Station)\b'
)

# Account keywords trigger for 9-18 digit numbers within 40 characters
ACCOUNT_TRIGGER_REGEX = re.compile(r'(?:account(?:\s*no\.?)?|a/c(?:\s*no\.?)?|acct|beneficiary\s+a/c)\s*[:\-]?\s*([A-Za-z0-9]{9,18})\b', re.IGNORECASE)

# Account suffix / masked patterns (e.g. XXXXXX7890, ending 7890, last digits 6338)
MASKED_ACCOUNT_REGEX = re.compile(
    r'(?:[X*]{4,12}(\d{4})|'
    r'(?:account|a/c|digits)[\w\s]{0,35}?(?:ending(?:\s+in|\s+with)?|last\s+digits(?:\s+are|\s+of)?|digits\s+are)\s*[:\-]?\s*(\d{4,6}))\b',
    re.IGNORECASE
)

# Amount patterns supporting Indian units (lakh, crore, paise, Cash Rs. ...)
AMOUNT_REGEX = re.compile(
    r'\b(?:Cash[^\S\r\n]+)?(?:Rs\.?|INR|₹)[^\S\r\n]*([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)?(?:\s*\/-)?\b|'
    r'\b(?:Cash[^\S\r\n]+)([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)?(?:\s*(?:INR|rupees))?(?:\s*\/-)?\b|'
    r'\b([\d,]+(?:\.\d+)?)\s*(lakh|lac|crore|cr)\s*(?:rupees|INR)?(?:\s*\/-)?\b',
    re.IGNORECASE
)

# Date patterns (dd/mm/yyyy, yyyy-mm-dd, 15th January 2024, etc.)
DATE_REGEX = re.compile(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b|\b(\d{4}-\d{2}-\d{2})\b|\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b', re.IGNORECASE)

EMAIL_EXCLUDE_DOMAINS = {"gmail", "yahoo", "outlook", "hotmail", "icloud", "rediffmail", "protonmail"}

def extract_rule_entities(text: str, page_or_para: str, base_char_offset: int = 0) -> List[Dict[str, Any]]:
    """
    Runs deterministic pattern extraction on text for structured identifiers.
    Returns list of extracted entities with exact character spans and confidences.
    """
    results: List[Dict[str, Any]] = []
    found_phones_raw: Set[str] = set()
    account_spans: List[Tuple[int, int]] = []
    found_account_digits: Set[str] = set()

    # 1. BANK ACCOUNTS (within ~40 chars of account triggers)
    for m in ACCOUNT_TRIGGER_REGEX.finditer(text):
        raw_val = m.group(1).strip()
        cleaned_digits = re.sub(r'\D', '', raw_val)
        if cleaned_digits and len(cleaned_digits) >= 9:
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            account_spans.append((start, end))
            found_account_digits.add(cleaned_digits)
            results.append({
                "entity_type": "BANK_ACCOUNT",
                "raw_value": raw_val,
                "normalized_value": normalize_account(raw_val),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex"
            })

    # 2. PHONE NUMBERS (disambiguate: account keyword within 40 chars takes precedence)
    for m in PHONE_REGEX.finditer(text):
        raw = m.group(0).strip()
        norm_res = normalize_phone(raw)
        if norm_res and norm_res.get("valid_mobile"):
            start = base_char_offset + m.start()
            end = base_char_offset + m.end()

            # If overlapping with an already identified account, skip
            if any(not (end <= s or start >= e) for s, e in account_spans):
                continue

            # Check if preceded by account trigger keywords within 40 characters
            preceding_context = text[max(0, m.start() - 40):m.start()]
            if re.search(r'\b(?:account(?:\s*no\.?)?|a/c(?:\s*no\.?)?|acct|beneficiary)\b', preceding_context, re.IGNORECASE):
                cleaned_digits = re.sub(r'\D', '', raw)[-10:]
                if cleaned_digits not in found_account_digits:
                    found_account_digits.add(cleaned_digits)
                    account_spans.append((start, end))
                    results.append({
                        "entity_type": "BANK_ACCOUNT",
                        "raw_value": raw,
                        "normalized_value": normalize_account(raw),
                        "char_span_start": start,
                        "char_span_end": end,
                        "page_or_paragraph": page_or_para,
                        "confidence": 0.90,
                        "method": "regex"
                    })
                continue

            found_phones_raw.add(re.sub(r'\D', '', raw)[-10:])
            results.append({
                "entity_type": "PHONE",
                "raw_value": raw,
                "normalized_value": norm_res["number"],
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95,
                "method": "regex"
            })

    # 3. ACCOUNT SUFFIX (masked/partial accounts -> BankAccount node)
    for m in MASKED_ACCOUNT_REGEX.finditer(text):
        raw = m.group(0).strip()
        last4 = m.group(1) or m.group(2)
        start = base_char_offset + m.start()
        end = base_char_offset + m.end()
        results.append({
            "entity_type": "ACCOUNT_SUFFIX",
            "raw_value": raw,
            "normalized_value": f"ENDING_{last4}",
            "char_span_start": start,
            "char_span_end": end,
            "page_or_paragraph": page_or_para,
            "confidence": 0.40,
            "method": "regex"
        })

    # 4. VEHICLES
    for m in VEHICLE_REGEX.finditer(text):
        raw = m.group(1).strip()
        norm_v = normalize_vehicle(raw)
        if norm_v:
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            results.append({
                "entity_type": "VEHICLE",
                "raw_value": raw,
                "normalized_value": norm_v,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex"
            })

    # 5. AMOUNTS
    for m in AMOUNT_REGEX.finditer(text):
        raw = m.group(0).strip()
        paise_val = normalize_amount(raw)
        if paise_val is not None and paise_val > 0:
            start = base_char_offset + m.start()
            end = base_char_offset + m.end()
            results.append({
                "entity_type": "AMOUNT",
                "raw_value": raw,
                "normalized_value": str(paise_val),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex"
            })

    # 6. DATES
    for m in DATE_REGEX.finditer(text):
        raw = m.group(0).strip()
        d_str, t_str, iso_str = normalize_datetime(raw)
        if iso_str or d_str:
            start = base_char_offset + m.start()
            end = base_char_offset + m.end()
            results.append({
                "entity_type": "DATE",
                "raw_value": raw,
                "normalized_value": iso_str or d_str,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex"
            })

    # 7. EMAILS
    for m in EMAIL_REGEX.finditer(text):
        raw = m.group(1).strip()
        start = base_char_offset + m.start(1)
        end = base_char_offset + m.end(1)
        results.append({
            "entity_type": "EMAIL",
            "raw_value": raw,
            "normalized_value": raw.lower(),
            "char_span_start": start,
            "char_span_end": end,
            "page_or_paragraph": page_or_para,
            "confidence": 0.95,
            "method": "regex"
        })

    # 8. IP ADDRESSES
    for m in IP_REGEX.finditer(text):
        raw = m.group(1).strip()
        ip_val, is_valid = normalize_ip(raw)
        if is_valid:
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            results.append({
                "entity_type": "IP",
                "raw_value": raw,
                "normalized_value": ip_val,
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex"
            })

    # 9. UPI IDS (exclude standard emails)
    for m in UPI_REGEX.finditer(text):
        raw = m.group(1).strip()
        domain = raw.split("@")[-1].lower()
        if domain not in EMAIL_EXCLUDE_DOMAINS and "." not in domain:
            start = base_char_offset + m.start(1)
            end = base_char_offset + m.end(1)
            results.append({
                "entity_type": "UPI",
                "raw_value": raw,
                "normalized_value": raw.lower(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.90,
                "method": "regex"
            })

    # 10. FIR NUMBER
    for m in FIR_REGEX.finditer(text):
        raw_fir = m.group(1) or m.group(2)
        if raw_fir:
            clean_fir = raw_fir.strip()
            start = base_char_offset + (m.start(1) if m.group(1) else m.start(2))
            end = base_char_offset + (m.end(1) if m.group(1) else m.end(2))
            results.append({
                "entity_type": "FIR",
                "raw_value": clean_fir,
                "normalized_value": clean_fir.upper(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.95,
                "method": "regex"
            })

    # 11. POLICE STATION
    ps_spans: List[Tuple[int, int]] = []
    for m in PS_REGEX.finditer(text):
        ps_name = m.group(1).strip()
        ps_lower = ps_name.lower()
        if ps_name and len(ps_name) >= 3 and not any(ps_lower.startswith(w) or ps_lower == w for w in ["registered", "reported", "informed", "sent to", "about", "near", "under", "dated", "district", "at", "to", "from", "the", "in", "case", "for"]):
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
                "method": "regex"
            })

    for m in PS_SUFFIX_REGEX.finditer(text):
        ps_name = m.group(1).strip()
        ps_lower = ps_name.lower()
        start = base_char_offset + m.start(1)
        end = base_char_offset + m.end(1)
        if any(not (end <= s or start >= e) for s, e in ps_spans):
            continue
        if ps_name and len(ps_name) >= 3 and not any(ps_lower.startswith(w) or ps_lower == w for w in ["registered", "reported", "informed", "sent to", "about", "near", "under", "dated", "district", "at", "to", "from", "the", "in", "case", "for"]):
            ps_spans.append((start, end))
            results.append({
                "entity_type": "POLICE_STATION",
                "raw_value": ps_name,
                "normalized_value": ps_name.title(),
                "char_span_start": start,
                "char_span_end": end,
                "page_or_paragraph": page_or_para,
                "confidence": 0.85,
                "method": "regex"
            })

    return results
