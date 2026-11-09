import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.services.ingestion.validators import (
    validate_bank_account,
    validate_ifsc,
    validate_upi_vpa,
)

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

def load_narration_patterns() -> list:
    """Load regex patterns for parsing bank statement narrations."""
    pat_file = CONFIG_DIR / "narration_patterns.yaml"
    if pat_file.exists():
        with open(pat_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("patterns", [])
    return []

COMPILED_PATTERNS = None

def get_compiled_patterns():
    global COMPILED_PATTERNS
    if COMPILED_PATTERNS is None:
        raw_patterns = load_narration_patterns()
        COMPILED_PATTERNS = []
        for p in raw_patterns:
            try:
                rx = re.compile(p["regex"])
                COMPILED_PATTERNS.append({
                    "name": p.get("name", "pattern"),
                    "type": p.get("type", "other"),
                    "regex": rx
                })
            except re.error:
                continue
    return COMPILED_PATTERNS


_ACCT_HEADER_RE = re.compile(
    r"(?:account\s*(?:no|number|#)|a/c\s*(?:no|number|#)?|acct\s*(?:no|number)?)\s*[:\-=#]?\s*([0-9Xx*]{6,20})",
    re.IGNORECASE,
)
_HOLDER_HEADER_RE = re.compile(
    r"(?:account\s*holder(?:\s*name)?|customer\s*name|account\s*name|holder\s*name)\s*[:\-=]\s*([A-Za-z0-9\s.&()/-]{2,80})",
    re.IGNORECASE,
)
_IFSC_TOKEN_RE = re.compile(r"\b([A-Za-z]{4}0[A-Za-z0-9]{6})\b")


def extract_statement_owner_metadata(
    banner_lines: Optional[List[str]] = None,
    headers: Optional[List[str]] = None,
    records: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Parses the statement header/preamble block (account number, account holder, IFSC)
    to identify the primary account owner of a single-account bank statement.
    Never guesses: if no owner account is found, returns needs_owner_confirmation=True.
    """
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None

    for line in (banner_lines or []):
        if not line:
            continue
        s = str(line).strip()

        if not account_number:
            m_acc = _ACCT_HEADER_RE.search(s)
            if m_acc:
                cand = m_acc.group(1).strip()
                v_acc = validate_bank_account(cand)
                if v_acc["ok"]:
                    account_number = v_acc["normalized"]
            elif "account no" in s.lower() or "a/c no" in s.lower():
                for tok in re.split(r"[\s,:;|]+", s):
                    v_acc = validate_bank_account(tok)
                    if v_acc["ok"]:
                        account_number = v_acc["normalized"]
                        break

        if not account_holder:
            m_holder = _HOLDER_HEADER_RE.search(s)
            if m_holder:
                holder_cand = re.split(r"[,|;\t]|(?:\bIFSC\b|\bBranch\b|\bAccount\b)", m_holder.group(1), maxsplit=1)[0].strip()
                if holder_cand:
                    account_holder = holder_cand

        if not ifsc_code:
            for m_ifsc in _IFSC_TOKEN_RE.finditer(s):
                v_ifsc = validate_ifsc(m_ifsc.group(1))
                if v_ifsc["ok"]:
                    ifsc_code = v_ifsc["normalized"]
                    bank_name = v_ifsc["meta"].get("bank_name")
                    break

    # Check if an explicit statement_account column exists with a single uniform account number
    if not account_number and headers and records:
        stmt_cols = [
            h for h in headers
            if re.sub(r"[^\w]+", "_", str(h).strip().lower()).strip("_")
            in {"statement_account", "account_no", "account_number", "own_account"}
        ]
        if stmt_cols:
            col = stmt_cols[0]
            seen_accts = set()
            for r in records[:50]:
                val = r.get(col)
                if val is not None and str(val).strip():
                    v_acc = validate_bank_account(str(val).strip())
                    if v_acc["ok"]:
                        seen_accts.add(v_acc["normalized"])
            if len(seen_accts) == 1:
                account_number = next(iter(seen_accts))

    owner_found = bool(account_number)
    return {
        "owner_found": owner_found,
        "account_number": account_number,
        "account_holder": account_holder,
        "ifsc": ifsc_code,
        "bank_name": bank_name,
        "needs_owner_confirmation": not owner_found,
    }


def parse_statement_narration(narration: str) -> Dict[str, Any]:
    """
    Parses unstructured narration / remark into structured counterparty data.
    Returns: {
        "counterparty_account": str | None,
        "counterparty_vpa": str | None,
        "counterparty_name": str | None,
        "reference": str | None,
        "payment_type": str,
        "is_unlinked": bool
    }
    """
    if not narration:
        return {
            "counterparty_account": None,
            "counterparty_vpa": None,
            "counterparty_name": None,
            "reference": None,
            "payment_type": "unknown",
            "is_unlinked": True
        }

    s = str(narration).strip()
    patterns = get_compiled_patterns()

    for p in patterns:
        m = p["regex"].search(s)
        if m:
            group_dict = m.groupdict()
            acct = group_dict.get("account")
            vpa = group_dict.get("vpa")
            name = group_dict.get("name")
            ref = group_dict.get("ref")

            if vpa:
                v_vpa = validate_upi_vpa(vpa)
                if v_vpa["ok"]:
                    vpa = v_vpa["normalized"]

            is_unlinked = p["type"] == "cash_atm" or (not acct and not vpa)

            return {
                "counterparty_account": acct.strip() if acct else None,
                "counterparty_vpa": vpa.strip() if vpa else None,
                "counterparty_name": name.strip() if name else None,
                "reference": ref.strip() if ref else None,
                "payment_type": p["type"],
                "is_unlinked": is_unlinked
            }

    # Fallback heuristic: check if any 12-digit number (UTR) or VPA is present
    vpa_m = re.search(r"([a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+)", s)
    vpa_val = vpa_m.group(1) if vpa_m else None
    if vpa_val:
        v_vpa = validate_upi_vpa(vpa_val)
        vpa_val = v_vpa["normalized"] if v_vpa["ok"] else vpa_val
    ref_m = re.search(r"\b(\d{12})\b", s)
    ref_val = ref_m.group(1) if ref_m else None

    return {
        "counterparty_account": None,
        "counterparty_vpa": vpa_val,
        "counterparty_name": None,
        "reference": ref_val,
        "payment_type": "unmatched_pattern",
        "is_unlinked": vpa_val is None
    }
