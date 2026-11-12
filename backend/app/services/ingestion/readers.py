import re
import csv
import io
import json
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional, Iterator
import openpyxl
from charset_normalizer import from_bytes as cn_from_bytes
from backend.app.config import settings, get_extraction_config
from backend.app.services.ingestion.validators import validate_amount
from backend.app.services.ingestion.statement import extract_statement_owner_metadata

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

_SYNONYMS_CACHE: Optional[Dict[str, Dict[str, List[str]]]] = None
_FLAT_SYNONYMS_CACHE: Optional[set] = None


class TabularReadError(ValueError):
    """Structured, officer-readable error raised when a tabular file cannot be parsed."""
    def __init__(self, message: str, reason_code: str = "UNREADABLE_TABULAR_FILE"):
        super().__init__(message)
        self.message = message
        self.reason_code = reason_code


def load_column_synonyms() -> Dict[str, Dict[str, List[str]]]:
    """Load column synonyms dictionary from yaml and extend with seed_graph_config (cached in-memory)."""
    global _SYNONYMS_CACHE
    if _SYNONYMS_CACHE is not None:
        return _SYNONYMS_CACHE
    syn_file = CONFIG_DIR / "column_synonyms.yaml"
    base_synonyms: Dict[str, Any] = {}
    if syn_file.exists():
        with open(syn_file, "r", encoding="utf-8") as f:
            base_synonyms = yaml.safe_load(f) or {}

    # Merge extended synonyms from seed_graph_config.yaml if present
    seed_file = CONFIG_DIR / "seed_graph_config.yaml"
    if seed_file.exists():
        with open(seed_file, "r", encoding="utf-8") as f:
            seed_cfg = yaml.safe_load(f) or {}
            exts = seed_cfg.get("synonym_extensions", {})
            for canon_field, syn_list in exts.items():
                for cat in ["cdr", "bank_transactions", "bank_statement", "identity_table", "ip_log"]:
                    cat_dict = base_synonyms.setdefault(cat, {})
                    cur_list = cat_dict.setdefault(canon_field, [])
                    for s in syn_list:
                        if s not in cur_list:
                            cur_list.append(s)

    _SYNONYMS_CACHE = base_synonyms
    return _SYNONYMS_CACHE


def get_all_synonyms_flat() -> set:
    """Return flat set of all known synonym tokens for fast header scanning (cached)."""
    global _FLAT_SYNONYMS_CACHE
    if _FLAT_SYNONYMS_CACHE is not None:
        return _FLAT_SYNONYMS_CACHE
    syn_dict = load_column_synonyms()
    flat = set()
    for category in syn_dict.values():
        if isinstance(category, dict):
            for synonyms in category.values():
                if isinstance(synonyms, list):
                    for s in synonyms:
                        flat.add(re.sub(r"[^\w]+", "_", str(s).strip().lower()).strip("_"))
    _FLAT_SYNONYMS_CACHE = flat
    return _FLAT_SYNONYMS_CACHE


def _norm_cell_token(val: Any) -> str:
    if val is None:
        return ""
    return re.sub(r"[^\w]+", "_", str(val).strip().lower()).strip("_")


def score_candidate_header_row(row: List[Any], known_syns: Optional[set] = None) -> Dict[str, float]:
    """
    Scores a candidate row for likelihood of being a table header row using:
    1. Synonym match count against known vocabulary
    2. Non-empty cell ratio
    3. Text-ness ratio (alphabetic header labels vs numeric/date data values)
    """
    if known_syns is None:
        known_syns = get_all_synonyms_flat()

    total_cols = max(1, len(row))
    non_empty_raw = [str(c).strip() for c in row if c is not None and str(c).strip()]
    if len(non_empty_raw) < 2:
        return {"total_score": -1.0, "syn_score": 0.0, "non_empty_ratio": 0.0, "text_ratio": 0.0}

    cleaned_cells = [_norm_cell_token(c) for c in non_empty_raw if _norm_cell_token(c)]
    if len(cleaned_cells) < 2:
        return {"total_score": -1.0, "syn_score": 0.0, "non_empty_ratio": 0.0, "text_ratio": 0.0}

    syn_score = 0.0
    text_like_count = 0
    for raw_c, cell in zip(non_empty_raw, cleaned_cells):
        has_alpha = any(ch.isalpha() for ch in raw_c)
        digit_count = sum(1 for ch in raw_c if ch.isdigit())
        is_mostly_numeric = digit_count > len(raw_c) * 0.5
        is_key_value_banner = ":" in raw_c and len(raw_c) > 20
        if has_alpha and not is_mostly_numeric and not is_key_value_banner and len(raw_c) <= 45:
            text_like_count += 1

        if cell in known_syns:
            syn_score += 1.0
        elif any(syn in cell or cell in syn for syn in known_syns if len(syn) > 3):
            syn_score += 0.5

    non_empty_ratio = len(non_empty_raw) / total_cols
    text_ratio = text_like_count / len(non_empty_raw)

    if syn_score > 0:
        total_score = syn_score + (non_empty_ratio * 0.6) + (text_ratio * 0.8)
    else:
        total_score = (non_empty_ratio * 0.2) + (text_ratio * 0.3) - 0.5

    return {
        "total_score": round(total_score, 4),
        "syn_score": syn_score,
        "non_empty_ratio": round(non_empty_ratio, 4),
        "text_ratio": round(text_ratio, 4),
    }


def _looks_like_multiline_header_companion(parent_row: List[Any], child_row: List[Any], known_syns: set) -> bool:
    """
    Checks whether two adjacent rows form a 2-line header (e.g., Row 0: ['Transaction', 'Transaction', 'Amount', 'Amount'],
    Row 1: ['Date', 'Narration', 'Debit', 'Credit']).
    Excludes preamble banner lines (which have fewer than 2 short cells or contain ':' key-value pairs).
    """
    if not parent_row or not child_row:
        return False
    p_non_empty = [str(c).strip() for c in parent_row if c is not None and str(c).strip()]
    c_non_empty = [str(c).strip() for c in child_row if c is not None and str(c).strip()]
    if len(p_non_empty) < 2 or len(c_non_empty) < 2:
        return False
    if any(":" in s or len(s) > 32 for s in p_non_empty):
        return False
    if any(":" in s or len(s) > 32 for s in c_non_empty):
        return False
    if any(sum(1 for ch in s if ch.isdigit()) > 3 for s in p_non_empty):
        return False
    if any(sum(1 for ch in s if ch.isdigit()) > 3 for s in c_non_empty):
        return False

    p_info = score_candidate_header_row(parent_row, known_syns)
    c_info = score_candidate_header_row(child_row, known_syns)
    return p_info["text_ratio"] >= 0.8 and c_info["text_ratio"] >= 0.8 and (p_info["syn_score"] >= 0.5 and c_info["syn_score"] >= 1.5)


def _merge_two_header_rows(top_row: List[Any], bottom_row: List[Any]) -> List[str]:
    """Combines a 2-line header into single descriptive column headers."""
    max_len = max(len(top_row), len(bottom_row))
    merged: List[str] = []
    last_top = ""
    for i in range(max_len):
        t_val = str(top_row[i]).strip() if i < len(top_row) and top_row[i] is not None else ""
        b_val = str(bottom_row[i]).strip() if i < len(bottom_row) and bottom_row[i] is not None else ""
        if t_val:
            last_top = t_val
        effective_top = t_val or last_top
        if b_val and effective_top:
            if _norm_cell_token(b_val) == _norm_cell_token(effective_top) or _norm_cell_token(effective_top) in _norm_cell_token(b_val):
                merged.append(b_val)
            elif _norm_cell_token(b_val) in get_all_synonyms_flat():
                # Keep child header canonical-friendly if it is already a known synonym (e.g. 'Debit', 'Credit', 'Date')
                merged.append(b_val)
            else:
                merged.append(f"{effective_top} {b_val}".strip())
        elif b_val:
            merged.append(b_val)
        elif t_val:
            merged.append(t_val)
        else:
            merged.append(f"col_{i}")
    return merged


def detect_header_row(rows: List[List[Any]]) -> Tuple[int, List[str], List[str]]:
    """
    Scans up to configured header_scan_max_rows.
    Scores candidate rows using synonym vocabulary, non-empty ratio, and text-ness.
    Supports multi-line headers. Rows before the header are returned as banner lines.
    Returns: (last_header_index, header_columns, banner_rows)
    """
    if not rows:
        return 0, [], []

    known_syns = get_all_synonyms_flat()
    cfg = get_extraction_config()
    scan_max = int(cfg.get("table", {}).get("header_scan_max_rows", 40))
    scan_limit = min(scan_max, len(rows))

    max_score = -999.0
    best_idx = 0
    banner_rows: List[str] = []

    for i in range(scan_limit):
        row = rows[i]
        info = score_candidate_header_row(row, known_syns)
        if info["total_score"] > max_score:
            max_score = info["total_score"]
            best_idx = i

    header_start_idx = best_idx
    header_end_idx = best_idx
    header_cols: List[str] = []

    # Check if best_idx and best_idx - 1 form a 2-line header
    if best_idx > 0 and _looks_like_multiline_header_companion(rows[best_idx - 1], rows[best_idx], known_syns):
        header_start_idx = best_idx - 1
        header_end_idx = best_idx
        header_cols = _merge_two_header_rows(rows[best_idx - 1], rows[best_idx])
    elif best_idx + 1 < scan_limit and _looks_like_multiline_header_companion(rows[best_idx], rows[best_idx + 1], known_syns):
        header_start_idx = best_idx
        header_end_idx = best_idx + 1
        header_cols = _merge_two_header_rows(rows[best_idx], rows[best_idx + 1])
    else:
        header_cols = [
            str(c).strip() if c is not None and str(c).strip() else f"col_{c_i}"
            for c_i, c in enumerate(rows[best_idx])
        ]

    # Deduplicate identical header names by suffixing index if needed
    seen_headers: Dict[str, int] = {}
    unique_headers: List[str] = []
    for h in header_cols:
        if h not in seen_headers:
            seen_headers[h] = 1
            unique_headers.append(h)
        else:
            seen_headers[h] += 1
            unique_headers.append(f"{h}_{seen_headers[h]}")

    for b in range(header_start_idx):
        b_str = " ".join([str(c).strip() for c in rows[b] if c is not None and str(c).strip()])
        if b_str:
            banner_rows.append(b_str)

    return header_end_idx, unique_headers, banner_rows


def is_repeated_header_row(row_cells: List[Any], headers: List[str]) -> bool:
    """Returns True if row_cells repeats the column header row (e.g., on page 2 of a statement)."""
    if not row_cells or not headers:
        return False
    norm_headers = [_norm_cell_token(h) for h in headers if _norm_cell_token(h) and not _norm_cell_token(h).startswith("col_")]
    if len(norm_headers) < 2:
        return False
    norm_cells = [_norm_cell_token(c) for c in row_cells[:len(headers)] if c is not None and _norm_cell_token(c)]
    if len(norm_cells) < 2:
        return False
    matches = sum(1 for c in norm_cells if c in norm_headers)
    return (matches / max(1, len(norm_headers))) >= 0.7


def classify_special_row(row_cells: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Classifies non-transaction summary rows:
    - 'opening_balance': Opening Balance / B/F / Brought Forward
    - 'closing_balance': Closing Balance / C/F / Carried Forward
    - 'total': Total / Grand Total / Summary
    Extracts any balance/total amount in integer paise.
    """
    if not row_cells:
        return {"kind": "empty", "amount_paise": None}

    non_empty = [str(c).strip() for c in row_cells if c is not None and str(c).strip()]
    if not non_empty:
        return {"kind": "empty", "amount_paise": None}

    joined_upper = " ".join(non_empty[:4]).upper()
    first_few_upper = [str(c).strip().upper() for c in row_cells[:3] if c is not None and str(c).strip()]

    kind = None
    if any(k in joined_upper for k in ["OPENING BALANCE", "BALANCE B/F", "BROUGHT FORWARD", "OPENING BAL", "BAL B/F"]):
        kind = "opening_balance"
    elif any(k in joined_upper for k in ["CLOSING BALANCE", "BALANCE C/F", "CARRIED FORWARD", "CLOSING BAL", "BAL C/F"]):
        kind = "closing_balance"
    elif any(
        f in {"TOTAL", "GRAND TOTAL", "SUMMARY", "SUB TOTAL", "SUBTOTAL"}
        or f.startswith("TOTAL ")
        or f.endswith(" TOTAL")
        or "GRAND TOTAL" in f
        for f in first_few_upper
    ):
        kind = "total"

    if not kind:
        return None

    # Extract last valid monetary amount in the row
    extracted_paise: Optional[int] = None
    for cell_str in reversed(non_empty):
        # Skip pure label cells
        if any(lbl in cell_str.upper() for lbl in ["OPENING", "CLOSING", "TOTAL", "SUMMARY", "FORWARD", "B/F", "C/F"]):
            # Check if label and amount are in the same cell e.g. "Opening Balance: 10,000.00"
            m_inline = re.search(r"[:\-]\s*([₹Rs.INR\s(0-9,.\-)+CrDr]+)$", cell_str, re.IGNORECASE)
            if m_inline:
                v_amt = validate_amount(m_inline.group(1))
                if v_amt["ok"]:
                    extracted_paise = v_amt["normalized"]
                    break
            continue
        v_amt = validate_amount(cell_str)
        if v_amt["ok"] and v_amt["normalized"] is not None:
            extracted_paise = v_amt["normalized"]
            break

    return {"kind": kind, "amount_paise": extracted_paise, "raw_text": " | ".join(non_empty)}


def is_trailing_total_row(row_cells: List[Any]) -> bool:
    """Detect trailing summary, total, or opening/closing balance row."""
    spec = classify_special_row(row_cells)
    return spec is not None


def sniff_encoding_and_decode(raw_bytes: bytes) -> Tuple[str, str]:
    """
    Detects character encoding using charset-normalizer with safe fallbacks.
    Strips leading UTF-8 BOM if present.
    Returns: (decoded_text, detected_encoding)
    """
    if not raw_bytes:
        return "", "utf-8"

    # Reject obvious binary formats (ZIP/XLSX, PDF, PNG, JPEG, EXE) passed to text reader
    if raw_bytes.startswith((b"PK\x03\x04", b"%PDF-", b"\x89PNG", b"\xff\xd8\xff", b"MZ")):
        raise TabularReadError(
            "Binary file signature detected while reading text/CSV file.",
            reason_code="BINARY_FILE_IN_TEXT_READER",
        )

    if b"\x00" in raw_bytes[:1024]:
        # Check UTF-16 BOM
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                txt = raw_bytes.decode(enc).lstrip("\ufeff")
                return txt, enc
            except UnicodeDecodeError:
                continue
        raise TabularReadError(
            "File contains null bytes and cannot be decoded as text.",
            reason_code="CORRUPT_BINARY_CONTENT",
        )

    # 1. Try UTF-8 with BOM / strict UTF-8 first (fastest and exact for ASCII/UTF-8)
    try:
        txt = raw_bytes.decode("utf-8-sig")
        return txt.lstrip("\ufeff"), "utf-8"
    except UnicodeDecodeError:
        pass

    # 2. Use charset-normalizer
    try:
        best = cn_from_bytes(raw_bytes).best()
        if best is not None and best.encoding:
            enc = best.encoding
            txt = str(best).lstrip("\ufeff")
            return txt, enc
    except Exception:
        pass

    # 3. Fallback encodings common in Indian banking/telecom exports
    for enc in ("cp1252", "latin-1"):
        try:
            txt = raw_bytes.decode(enc)
            return txt.lstrip("\ufeff"), enc
        except UnicodeDecodeError:
            continue

    return raw_bytes.decode("utf-8", errors="replace").lstrip("\ufeff"), "utf-8-replace"


def sniff_csv_delimiter(lines: List[str]) -> str:
    """Sniffs CSV delimiter across [, ; \\t |] using csv.Sniffer + column-count consistency."""
    sample_lines = [ln for ln in lines[:15] if ln.strip()]
    if not sample_lines:
        return ","

    # Prefer line that looks like a multi-column row rather than a 1-column banner
    multi_col_lines = [ln for ln in sample_lines if sum(ln.count(d) for d in (",", ";", "\t", "|")) >= 2]
    sniff_target = "\n".join(multi_col_lines[:10] if multi_col_lines else sample_lines[:10])

    try:
        dialect = csv.Sniffer().sniff(sniff_target, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        pass

    # Fallback: pick delimiter with highest consistent count >= 1 across multi_col_lines
    target_rows = multi_col_lines or sample_lines
    best_delim = ","
    best_score = -1
    for delim in (",", ";", "\t", "|"):
        counts = [len(next(csv.reader([ln], delimiter=delim), [])) for ln in target_rows]
        valid_counts = [c for c in counts if c >= 2]
        if valid_counts:
            # Score by mode frequency * column count
            most_common = max(set(valid_counts), key=valid_counts.count)
            freq = valid_counts.count(most_common)
            score = freq * most_common
            if score > best_score:
                best_score = score
                best_delim = delim
    return best_delim


def _rows_to_records_and_metadata(
    raw_rows: List[List[Any]],
    page_numbers: Optional[List[int]] = None,
    join_wrapped_narrations: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str], List[str], Dict[str, Any]]:
    """
    Core row processor:
    - Detects header row (including multi-line headers) and banner preamble
    - Detects mid-file section switches (mixed-type files)
    - Drops repeated header rows
    - Captures opening_balance_paise, closing_balance_paise, and summary total rows into file_metadata
    - Optionally joins wrapped narration continuation lines (for PDF/multi-line bank statements)
    """
    if not raw_rows:
        return [], [], [], {
            "opening_balance_paise": None,
            "closing_balance_paise": None,
            "total_rows_dropped": 0,
            "repeated_headers_dropped": 0,
            "is_mixed_file": False,
            "sections": [],
            "statement_owner": extract_statement_owner_metadata([], [], []),
        }

    header_idx, headers, banners = detect_header_row(raw_rows)
    known_syns = get_all_synonyms_flat()

    records: List[Dict[str, Any]] = []
    opening_balance_paise: Optional[int] = None
    closing_balance_paise: Optional[int] = None
    total_rows_dropped = 0
    repeated_headers_dropped = 0
    sections: List[Dict[str, Any]] = []

    # Check banner lines for opening/closing balance mentions
    for b_line in banners:
        spec_b = classify_special_row([b_line])
        if spec_b:
            if spec_b["kind"] == "opening_balance" and opening_balance_paise is None and spec_b["amount_paise"] is not None:
                opening_balance_paise = spec_b["amount_paise"]
            elif spec_b["kind"] == "closing_balance" and spec_b["amount_paise"] is not None:
                closing_balance_paise = spec_b["amount_paise"]

    # Identify narration/description column and key transaction columns for wrapped line stitching
    narration_col: Optional[str] = None
    date_cols: List[str] = []
    amount_cols: List[str] = []
    for h in headers:
        hn = _norm_cell_token(h)
        if any(k in hn for k in ("narr", "particular", "desc", "remark", "detail")):
            if narration_col is None:
                narration_col = h
        elif any(k in hn for k in ("date", "dt", "time")):
            date_cols.append(h)
        elif any(k in hn for k in ("debit", "credit", "withdrawal", "deposit", "amount", "balance", "dr", "cr")):
            amount_cols.append(h)

    current_headers = headers
    current_records = records
    current_banners = banners

    for rel_idx, r in enumerate(raw_rows[header_idx + 1:], start=header_idx + 1):
        page_no = page_numbers[rel_idx] if page_numbers and rel_idx < len(page_numbers) else None

        # 1. Check if this row is a repeated header row
        if is_repeated_header_row(r, current_headers):
            repeated_headers_dropped += 1
            continue

        # 2. Check if this row is a brand new table header for a mixed-type file section
        row_score = score_candidate_header_row(r, known_syns)
        if (
            len(current_records) >= 1
            and row_score["syn_score"] >= 2.5
            and row_score["text_ratio"] >= 0.85
            and not is_repeated_header_row(r, current_headers)
        ):
            # Save completed section and switch to new section headers
            sections.append({
                "section_index": len(sections),
                "headers": current_headers,
                "records": list(current_records),
                "banner_rows": list(current_banners),
            })
            current_headers = [
                str(c).strip() if c is not None and str(c).strip() else f"col_{c_i}"
                for c_i, c in enumerate(r)
            ]
            current_records = []
            current_banners = []
            continue

        # 3. Check if this row is an opening balance, closing balance, or total summary row
        spec = classify_special_row(r)
        if spec is not None:
            if spec["kind"] == "opening_balance" and spec["amount_paise"] is not None and opening_balance_paise is None:
                opening_balance_paise = spec["amount_paise"]
            elif spec["kind"] == "closing_balance" and spec["amount_paise"] is not None:
                closing_balance_paise = spec["amount_paise"]
            if spec["kind"] in ("opening_balance", "closing_balance", "total"):
                total_rows_dropped += 1
            continue

        # 4. Build row dictionary
        record: Dict[str, Any] = {}
        for idx, h in enumerate(current_headers):
            val = str(r[idx]).strip() if idx < len(r) and r[idx] is not None and str(r[idx]).strip() != "" else None
            record[h] = val

        # 5. Wrapped narration continuation line check (for PDF / multi-line bank statements)
        if join_wrapped_narrations and current_records and narration_col and narration_col in record:
            has_date = any(record.get(dc) for dc in date_cols)
            has_amt = any(record.get(ac) for ac in amount_cols)
            narr_piece = record.get(narration_col)
            other_non_empty = [
                k for k, v in record.items()
                if v is not None and k not in ([narration_col] + date_cols + amount_cols)
            ]
            if not has_date and not has_amt and narr_piece and not other_non_empty:
                prev_rec = current_records[-1]
                prev_narr = prev_rec.get(narration_col) or ""
                prev_rec[narration_col] = f"{prev_narr} {narr_piece}".strip()
                continue

        if page_no is not None:
            record["_page_no"] = page_no

        current_records.append(record)

    if sections:
        sections.append({
            "section_index": len(sections),
            "headers": current_headers,
            "records": list(current_records),
            "banner_rows": list(current_banners),
        })
        # Primary return keeps first section's headers & records for backward compatibility
        primary_headers = sections[0]["headers"]
        primary_records = sections[0]["records"]
    else:
        primary_headers = headers
        primary_records = records

    owner_meta = extract_statement_owner_metadata(banners, primary_headers, primary_records)

    file_metadata = {
        "opening_balance_paise": opening_balance_paise,
        "closing_balance_paise": closing_balance_paise,
        "total_rows_dropped": total_rows_dropped,
        "repeated_headers_dropped": repeated_headers_dropped,
        "is_mixed_file": len(sections) > 1,
        "sections": sections,
        "statement_owner": owner_meta,
    }
    return primary_records, primary_headers, banners, file_metadata


def read_tabular_file_detailed(file_path: Path, sheet_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Enhanced tabular reader returning records, headers, banner_lines, and rich file_metadata
    (encoding, delimiter, opening/closing balance, statement_owner, sheets, sections).
    Supports CSV, XLSX, JSON/JSONL, and tabular PDF statements.
    """
    if not file_path.exists():
        raise TabularReadError(f"Evidence file not found on disk: {file_path.name}", reason_code="FILE_NOT_FOUND")

    ext = file_path.suffix.lower()
    if ext in [".csv", ".tsv", ".txt"]:
        return read_csv_file_detailed(file_path)
    elif ext == ".xlsx":
        return read_xlsx_file_detailed(file_path, target_sheet=sheet_name)
    elif ext in [".json", ".jsonl"]:
        return read_json_file_detailed(file_path)
    elif ext == ".pdf":
        return read_pdf_table_file_detailed(file_path)
    else:
        raise TabularReadError(f"Unsupported tabular extension: {ext}", reason_code="UNSUPPORTED_FILE_EXTENSION")


def read_tabular_file(file_path: Path, sheet_name: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Universal tabular reader for CSV, XLSX, JSON/JSONL, and PDF tables.
    Returns: (records_list, header_columns, banner_lines)
    """
    detailed = read_tabular_file_detailed(file_path, sheet_name=sheet_name)
    return detailed["records"], detailed["headers"], detailed["banner_rows"]


def read_csv_file_detailed(file_path: Path) -> Dict[str, Any]:
    """Reads CSV with charset-normalizer encoding detection, BOM stripping, delimiter sniffing, and metadata capture."""
    raw_bytes = file_path.read_bytes()
    text_content, detected_encoding = sniff_encoding_and_decode(raw_bytes)

    lines = [line for line in text_content.splitlines() if line.strip()]
    if not lines:
        return {
            "records": [],
            "headers": [],
            "banner_rows": [],
            "file_metadata": {
                "encoding": detected_encoding,
                "delimiter": ",",
                "opening_balance_paise": None,
                "closing_balance_paise": None,
                "total_rows_dropped": 0,
                "repeated_headers_dropped": 0,
                "is_mixed_file": False,
                "sections": [],
                "statement_owner": extract_statement_owner_metadata([], [], []),
            },
        }

    delimiter = sniff_csv_delimiter(lines)
    raw_rows: List[List[Any]] = []
    reader = csv.reader(lines, delimiter=delimiter)
    for r in reader:
        if r and any(c.strip() for c in r):
            raw_rows.append(r)

    records, headers, banners, meta = _rows_to_records_and_metadata(
        raw_rows, join_wrapped_narrations=True
    )
    meta["encoding"] = detected_encoding
    meta["delimiter"] = delimiter
    return {
        "records": records,
        "headers": headers,
        "banner_rows": banners,
        "file_metadata": meta,
    }


def read_csv_file(file_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads CSV with encoding auto-detection (UTF-8, UTF-8-BOM, CP1252, Latin-1)."""
    res = read_csv_file_detailed(file_path)
    return res["records"], res["headers"], res["banner_rows"]


def _extract_unmerged_rows_from_worksheet(ws) -> List[List[Any]]:
    """
    Reads an openpyxl Worksheet:
    - Unmerges merged cells in the header scan region by filling all cells in the range with the top-left value
    - Skips hidden rows (`ws.row_dimensions[row_idx].hidden == True`)
    - Skips completely empty rows
    """
    cfg = get_extraction_config()
    scan_max = int(cfg.get("table", {}).get("header_scan_max_rows", 40))

    # Map (row_1based, col_1based) -> top_left_value for merged ranges in the header region
    merged_fill: Dict[Tuple[int, int], Any] = {}
    try:
        for m_range in ws.merged_cells.ranges:
            if m_range.min_row <= scan_max:
                top_val = ws.cell(row=m_range.min_row, column=m_range.min_col).value
                for r_idx in range(m_range.min_row, min(m_range.max_row, scan_max) + 1):
                    for c_idx in range(m_range.min_col, m_range.max_col + 1):
                        merged_fill[(r_idx, c_idx)] = top_val
    except Exception:
        pass

    raw_rows: List[List[Any]] = []
    for r_idx, row in enumerate(ws.iter_rows(values_only=False), start=1):
        # Skip hidden rows
        row_dim = ws.row_dimensions.get(r_idx)
        if row_dim is not None and getattr(row_dim, "hidden", False):
            continue

        row_vals: List[Any] = []
        for c_idx, cell in enumerate(row, start=1):
            val = cell.value
            if val is None and (r_idx, c_idx) in merged_fill:
                val = merged_fill[(r_idx, c_idx)]
            row_vals.append(val)

        if row_vals and any(c is not None and str(c).strip() for c in row_vals):
            raw_rows.append(row_vals)

    return raw_rows


def read_xlsx_file_detailed(file_path: Path, target_sheet: Optional[str] = None) -> Dict[str, Any]:
    """
    Reads ALL sheets in an Excel workbook, unmerging merged header cells, skipping hidden rows,
    and capturing per-sheet records, headers, and metadata.
    """
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as exc:
        raise TabularReadError(f"Unable to open Excel workbook: {exc}", reason_code="CORRUPT_EXCEL_WORKBOOK") from exc

    sheet_names = wb.sheetnames
    if not sheet_names:
        return {
            "records": [],
            "headers": [],
            "banner_rows": [],
            "file_metadata": {"sheets": [], "opening_balance_paise": None, "closing_balance_paise": None},
        }

    sheets_summary: List[Dict[str, Any]] = []
    selected_sheet_data: Optional[Dict[str, Any]] = None

    for s_name in sheet_names:
        ws = wb[s_name]
        # Skip hidden sheets unless explicitly requested
        if getattr(ws, "sheet_state", "visible") != "visible" and target_sheet != s_name:
            continue

        raw_rows = _extract_unmerged_rows_from_worksheet(ws)
        if not raw_rows:
            continue

        records, headers, banners, meta = _rows_to_records_and_metadata(
            raw_rows, join_wrapped_narrations=True
        )
        sheet_entry = {
            "sheet_name": s_name,
            "headers": headers,
            "records": records,
            "banner_rows": banners,
            "row_count": len(records),
            "file_metadata": meta,
        }
        sheets_summary.append(sheet_entry)
        if target_sheet and s_name == target_sheet:
            selected_sheet_data = sheet_entry

    if not sheets_summary:
        return {
            "records": [],
            "headers": [],
            "banner_rows": [],
            "file_metadata": {"sheets": [], "opening_balance_paise": None, "closing_balance_paise": None},
        }

    if selected_sheet_data is None:
        selected_sheet_data = sheets_summary[0]

    primary_meta = dict(selected_sheet_data["file_metadata"])
    primary_meta["sheets"] = sheets_summary
    primary_meta["selected_sheet"] = selected_sheet_data["sheet_name"]
    primary_meta["multi_sheet"] = len(sheets_summary) > 1

    return {
        "records": selected_sheet_data["records"],
        "headers": selected_sheet_data["headers"],
        "banner_rows": selected_sheet_data["banner_rows"],
        "file_metadata": primary_meta,
    }


def read_xlsx_file(file_path: Path, target_sheet: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads XLSX using openpyxl, unmerging merged headers and ignoring hidden rows."""
    res = read_xlsx_file_detailed(file_path, target_sheet=target_sheet)
    return res["records"], res["headers"], res["banner_rows"]


def read_pdf_table_file_detailed(file_path: Path) -> Dict[str, Any]:
    """
    Extracts multi-page tables from PDF bank statements / tabular reports using pdfplumber:
    - Extracts tables page by page
    - Captures preamble text lines above the first table as banner_rows (account number, holder, IFSC, opening balance)
    - Stitches tables continuing across pages, dropping repeated headers
    - Joins wrapped multi-line narrations into the preceding row
    - Attaches _page_no provenance to each row
    """
    import pdfplumber

    raw_rows: List[List[Any]] = []
    page_numbers: List[int] = []
    preamble_lines: List[str] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                tables = page.extract_tables() or []

                # Capture text lines on page 1 before the table header (or lines containing Account/IFSC/Balance)
                for ln in page_text.splitlines():
                    ln_s = ln.strip()
                    if not ln_s:
                        continue
                    if page_idx == 1 and not raw_rows:
                        if any(
                            kw in ln_s.lower()
                            for kw in ("account", "a/c", "ifsc", "branch", "statement", "holder", "customer", "opening balance")
                        ):
                            preamble_lines.append(ln_s)
                    elif any(kw in ln_s.lower() for kw in ("opening balance", "closing balance")):
                        raw_rows.append([ln_s])
                        page_numbers.append(page_idx)

                if tables:
                    for tbl in tables:
                        for row in tbl:
                            if not row:
                                continue
                            cleaned_row = [
                                re.sub(r"\s+", " ", str(c).strip()) if c is not None else ""
                                for c in row
                            ]
                            if any(cleaned_row):
                                raw_rows.append(cleaned_row)
                                page_numbers.append(page_idx)
                else:
                    # Fallback for borderless PDF tables: split lines that have 2+ whitespace gaps or pipe delimiters
                    for ln in page_text.splitlines():
                        ln_s = ln.strip()
                        if not ln_s:
                            continue
                        if "|" in ln_s:
                            parts = [p.strip() for p in ln_s.split("|") if p.strip()]
                        else:
                            parts = [p.strip() for p in re.split(r"\s{2,}", ln_s) if p.strip()]
                        if len(parts) >= 2:
                            raw_rows.append(parts)
                            page_numbers.append(page_idx)
    except Exception as exc:
        raise TabularReadError(f"Unable to parse PDF table: {exc}", reason_code="CORRUPT_PDF_FILE") from exc

    # Prepend preamble banner rows as single-cell rows before table rows so detect_header_row includes them
    combined_rows: List[List[Any]] = []
    combined_pages: List[int] = []
    for p_ln in preamble_lines:
        combined_rows.append([p_ln])
        combined_pages.append(1)
    combined_rows.extend(raw_rows)
    combined_pages.extend(page_numbers)

    records, headers, banners, meta = _rows_to_records_and_metadata(
        combined_rows, page_numbers=combined_pages, join_wrapped_narrations=True
    )
    return {
        "records": records,
        "headers": headers,
        "banner_rows": banners,
        "file_metadata": meta,
    }


def read_pdf_table_file(file_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    res = read_pdf_table_file_detailed(file_path)
    return res["records"], res["headers"], res["banner_rows"]


def read_json_file_detailed(file_path: Path) -> Dict[str, Any]:
    """Reads JSON list or JSONL lines with encoding detection."""
    raw_bytes = file_path.read_bytes()
    content, detected_encoding = sniff_encoding_and_decode(raw_bytes)
    content = content.strip()
    records: List[Dict[str, Any]] = []

    if file_path.suffix.lower() == ".jsonl" or (content.startswith("{") and "\n{" in content):
        for line in content.splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    else:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                records = parsed
            elif isinstance(parsed, dict):
                if "records" in parsed and isinstance(parsed["records"], list):
                    records = parsed["records"]
                else:
                    records = [parsed]
        except Exception:
            records = []

    headers = list(records[0].keys()) if records else []
    return {
        "records": records,
        "headers": headers,
        "banner_rows": [],
        "file_metadata": {
            "encoding": detected_encoding,
            "opening_balance_paise": None,
            "closing_balance_paise": None,
            "total_rows_dropped": 0,
            "repeated_headers_dropped": 0,
            "is_mixed_file": False,
            "sections": [],
            "statement_owner": extract_statement_owner_metadata([], headers, records),
        },
    }


def read_json_file(file_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads JSON list or JSONL lines."""
    res = read_json_file_detailed(file_path)
    return res["records"], res["headers"], res["banner_rows"]


def iter_tabular_chunks(
    file_path: Path,
    chunk_size: Optional[int] = None,
    sheet_name: Optional[str] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Streams a large CSV, XLSX, or JSONL file in bounded-memory chunks.
    Yields: {
        "chunk_index": int,
        "records": List[Dict[str, Any]],
        "headers": List[str],
        "banner_rows": List[str],
        "file_metadata": Dict[str, Any],
        "rows_seen_so_far": int,
    }
    """
    cfg = get_extraction_config()
    if chunk_size is None or chunk_size <= 0:
        chunk_size = int(cfg.get("table", {}).get("chunk_size_rows", 5000))
    max_rows = int(cfg.get("jobs", {}).get("max_rows_per_file", 500000))
    scan_max = int(cfg.get("table", {}).get("header_scan_max_rows", 40))

    ext = file_path.suffix.lower()
    if ext == ".csv":
        # Sniff encoding from first 64KB
        with open(file_path, "rb") as bf:
            head_bytes = bf.read(65536)
        _, enc = sniff_encoding_and_decode(head_bytes)
        if enc == "utf-8":
            enc = "utf-8-sig"

        with open(file_path, "r", encoding=enc, errors="replace", newline="") as tf:
            head_lines = []
            for _ in range(max(scan_max + 5, 25)):
                ln = tf.readline()
                if not ln:
                    break
                if ln.strip():
                    head_lines.append(ln)
            delimiter = sniff_csv_delimiter(head_lines)

        with open(file_path, "r", encoding=enc, errors="replace", newline="") as tf:
            reader = csv.reader(tf, delimiter=delimiter)
            initial_rows: List[List[Any]] = []
            for r in reader:
                if r and any(c.strip() for c in r):
                    initial_rows.append(r)
                    if len(initial_rows) >= scan_max:
                        break

            if not initial_rows:
                return

            header_idx, headers, banners = detect_header_row(initial_rows)
            file_meta: Dict[str, Any] = {
                "encoding": enc,
                "delimiter": delimiter,
                "opening_balance_paise": None,
                "closing_balance_paise": None,
                "total_rows_dropped": 0,
                "repeated_headers_dropped": 0,
            }

            def _process_row(r: List[Any]) -> Optional[Dict[str, Any]]:
                if is_repeated_header_row(r, headers):
                    file_meta["repeated_headers_dropped"] += 1
                    return None
                spec = classify_special_row(r)
                if spec is not None:
                    if spec["kind"] == "opening_balance" and spec["amount_paise"] is not None and file_meta["opening_balance_paise"] is None:
                        file_meta["opening_balance_paise"] = spec["amount_paise"]
                    elif spec["kind"] == "closing_balance" and spec["amount_paise"] is not None:
                        file_meta["closing_balance_paise"] = spec["amount_paise"]
                    file_meta["total_rows_dropped"] += 1
                    return None
                rec = {}
                for idx, h in enumerate(headers):
                    rec[h] = r[idx].strip() if idx < len(r) and r[idx] is not None and r[idx].strip() != "" else None
                return rec

            chunk_buf: List[Dict[str, Any]] = []
            rows_seen = 0
            chunk_idx = 0

            for r in initial_rows[header_idx + 1:]:
                rec = _process_row(r)
                if rec is not None:
                    chunk_buf.append(rec)
                    rows_seen += 1
                    if len(chunk_buf) >= chunk_size:
                        yield {
                            "chunk_index": chunk_idx,
                            "records": chunk_buf,
                            "headers": headers,
                            "banner_rows": banners,
                            "file_metadata": file_meta,
                            "rows_seen_so_far": rows_seen,
                        }
                        chunk_buf = []
                        chunk_idx += 1

            for r in reader:
                if rows_seen >= max_rows:
                    break
                if not r or not any(c.strip() for c in r):
                    continue
                rec = _process_row(r)
                if rec is not None:
                    chunk_buf.append(rec)
                    rows_seen += 1
                    if len(chunk_buf) >= chunk_size:
                        yield {
                            "chunk_index": chunk_idx,
                            "records": chunk_buf,
                            "headers": headers,
                            "banner_rows": banners,
                            "file_metadata": file_meta,
                            "rows_seen_so_far": rows_seen,
                        }
                        chunk_buf = []
                        chunk_idx += 1

            if chunk_buf or chunk_idx == 0:
                file_meta["statement_owner"] = extract_statement_owner_metadata(banners, headers, chunk_buf[:50])
                yield {
                    "chunk_index": chunk_idx,
                    "records": chunk_buf,
                    "headers": headers,
                    "banner_rows": banners,
                    "file_metadata": file_meta,
                    "rows_seen_so_far": rows_seen,
                }
    else:
        # For XLSX / JSON / PDF, slice detailed records into chunks
        detailed = read_tabular_file_detailed(file_path, sheet_name=sheet_name)
        all_recs = detailed["records"][:max_rows]
        headers = detailed["headers"]
        banners = detailed["banner_rows"]
        meta = detailed["file_metadata"]
        if not all_recs:
            yield {
                "chunk_index": 0,
                "records": [],
                "headers": headers,
                "banner_rows": banners,
                "file_metadata": meta,
                "rows_seen_so_far": 0,
            }
            return
        for c_idx, start in enumerate(range(0, len(all_recs), chunk_size)):
            batch = all_recs[start : start + chunk_size]
            yield {
                "chunk_index": c_idx,
                "records": batch,
                "headers": headers,
                "banner_rows": banners,
                "file_metadata": meta,
                "rows_seen_so_far": start + len(batch),
            }
