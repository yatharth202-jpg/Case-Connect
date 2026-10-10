import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

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
