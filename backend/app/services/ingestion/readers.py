import re
import csv
import json
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
import openpyxl
from backend.app.config import settings

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
if not CONFIG_DIR.exists():
    CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

def load_column_synonyms() -> Dict[str, Dict[str, List[str]]]:
    """Load column synonyms dictionary from yaml."""
    syn_file = CONFIG_DIR / "column_synonyms.yaml"
    if syn_file.exists():
        with open(syn_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

def get_all_synonyms_flat() -> set:
    """Return flat set of all known synonym tokens for fast header scanning."""
    syn_dict = load_column_synonyms()
    flat = set()
    for category in syn_dict.values():
        if isinstance(category, dict):
            for synonyms in category.values():
                if isinstance(synonyms, list):
                    for s in synonyms:
                        flat.add(re.sub(r"[^\w]+", "_", str(s).strip().lower()).strip("_"))
    return flat

def detect_header_row(rows: List[List[Any]]) -> Tuple[int, List[str], List[str]]:
    """
    Scans the first 40 rows.
    Finds the row whose cells have the highest count of matches with known synonyms.
    Rows before it are returned as banner lines.
    Returns: (header_index, header_columns, banner_rows)
    """
    import re
    known_syns = get_all_synonyms_flat()
    max_score = -1
    best_idx = 0
    banner_rows = []

    scan_limit = min(40, len(rows))
    for i in range(scan_limit):
        row = rows[i]
        score = 0
        cleaned_cells = [re.sub(r"[^\w]+", "_", str(c).strip().lower()).strip("_") for c in row if c is not None and str(c).strip()]
        for cell in cleaned_cells:
            if cell in known_syns:
                score += 1
            # Partial substring match
            elif any(syn in cell or cell in syn for syn in known_syns if len(syn) > 3):
                score += 0.5
        
        if score > max_score and len(cleaned_cells) >= 2:
            max_score = score
            best_idx = i

    for b in range(best_idx):
        b_str = " ".join([str(c) for c in rows[b] if c is not None and str(c).strip()])
        if b_str:
            banner_rows.append(b_str)

    header_cols = [str(c).strip() if c is not None else f"col_{c_i}" for c_i, c in enumerate(rows[best_idx])]
    return best_idx, header_cols, banner_rows

def is_trailing_total_row(row_cells: List[Any]) -> bool:
    """Detect trailing summary or total row (e.g. TOTAL,,,500000)."""
    if not row_cells:
        return True
    first_few = [str(c).strip().upper() for c in row_cells[:2] if c is not None and str(c).strip()]
    if any("TOTAL" in f or "SUMMARY" in f or "GRAND TOTAL" in f for f in first_few):
        return True
    return False

def read_tabular_file(file_path: Path, sheet_name: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """
    Universal tabular reader for CSV, XLSX, and JSON/JSONL.
    Returns: (records_list, header_columns, banner_lines)
    """
    ext = file_path.suffix.lower()

    if ext == ".csv":
        return read_csv_file(file_path)
    elif ext == ".xlsx":
        return read_xlsx_file(file_path, sheet_name)
    elif ext in [".json", ".jsonl"]:
        return read_json_file(file_path)
    else:
        raise ValueError(f"Unsupported tabular extension: {ext}")

def read_csv_file(file_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads CSV with encoding auto-detection (UTF-8, UTF-8-BOM, CP1252, Latin-1)."""
    raw_bytes = file_path.read_bytes()
    
    # Try decodings
    text_content = None
    for enc in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            text_content = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text_content is None:
        text_content = raw_bytes.decode("utf-8", errors="ignore")

    lines = [line for line in text_content.splitlines() if line.strip()]
    if not lines:
        return [], [], []

    # Sniff delimiter
    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    raw_rows = []
    reader = csv.reader(lines, delimiter=delimiter)
    for r in reader:
        if r and any(c.strip() for c in r):
            raw_rows.append(r)

    if not raw_rows:
        return [], [], []

    header_idx, headers, banners = detect_header_row(raw_rows)

    records = []
    for r in raw_rows[header_idx + 1:]:
        if is_trailing_total_row(r):
            continue
        record = {}
        for idx, h in enumerate(headers):
            val = r[idx].strip() if idx < len(r) else None
            record[h] = val
        records.append(record)

    return records, headers, banners

def read_xlsx_file(file_path: Path, target_sheet: Optional[str] = None) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads XLSX using openpyxl, listing sheets and extracting largest sheet by default."""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet_names = wb.sheetnames
    
    selected_name = target_sheet if target_sheet and target_sheet in sheet_names else sheet_names[0]
    ws = wb[selected_name]

    raw_rows = []
    for row in ws.iter_rows(values_only=True):
        if row and any(c is not None and str(c).strip() for c in row):
            raw_rows.append(list(row))

    if not raw_rows:
        return [], [], []

    header_idx, headers, banners = detect_header_row(raw_rows)

    records = []
    for r in raw_rows[header_idx + 1:]:
        if is_trailing_total_row(r):
            continue
        record = {}
        for idx, h in enumerate(headers):
            val = str(r[idx]).strip() if idx < len(r) and r[idx] is not None else None
            record[h] = val
        records.append(record)

    return records, headers, banners

def read_json_file(file_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Reads JSON list or JSONL lines."""
    content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
    records = []

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

    if not records:
        return [], [], []

    headers = list(records[0].keys()) if records else []
    return records, headers, []
