import os
import sys
import argparse
from pathlib import Path

# Add project root
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.ingestion.readers import read_tabular_file
from backend.app.services.ingestion.detect import detect_file_type
from backend.app.services.ingestion.mapping import suggest_column_mappings, compute_header_signature
from backend.app.services.ingestion.normalize import normalize_phone, normalize_amount, normalize_datetime

def mask_value(val: any) -> str:
    """Masks sensitive values (phones, accounts) for safe terminal and report printing."""
    if val is None:
        return "NULL"
    s = str(val).strip()
    if not s:
        return ""
    if len(s) > 6 and s.isdigit():
        return f"{s[:2]}******{s[-2:]}"
    elif len(s) > 10:
        return f"{s[:3]}...{s[-3:]}"
    return s

def probe_single_file(file_path: Path, show_rows: bool = False):
    print("=" * 60)
    print(f"PROBING FILE: {file_path.name}")
    print(f"Path: {file_path.resolve()} | Size: {file_path.stat().st_size} bytes")
    print("=" * 60)

    try:
        records, headers, banners = read_tabular_file(file_path)
    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        return

    print(f"[*] Total Raw Rows: {len(records)}")
    if banners:
        print(f"[*] Detected Banner Rows ({len(banners)}):")
        for b in banners:
            print(f"    - {b}")

    print(f"[*] Detected Header Columns ({len(headers)}):")
    print(f"    {', '.join(headers)}")

    # 1. Type Detection
    detection = detect_file_type(headers, records, filename=file_path.name)
    print(f"\n[+] Detected File Type: {detection['detected_type']} (Confidence: {detection['confidence'] * 100:.1f}%)")
    if detection["alternatives"]:
        alt_str = ", ".join([f"{a['type']} ({a['score']*100:.0f}%)" for a in detection["alternatives"]])
        print(f"    Alternatives: {alt_str}")

    # 2. Suggested Mapping
    sig = compute_header_signature(headers)
    mappings = suggest_column_mappings(detection["detected_type"] if detection["detected_type"] != "unknown" else "cdr", headers)
    print(f"\n[+] Header Signature: {sig[:16]}...")
    print("[+] Suggested Column Mappings:")
    for h, m in mappings.items():
        conf_marker = "[OK]" if m["confidence"] >= 0.8 else "[?]"
        print(f"    {conf_marker} {h:<25} -> {m['canonical']:<20} (Conf: {m['confidence']})")

    # 3. Sample Preview
    print(f"\n[+] Sample Values (First 3 Rows, {'Raw' if show_rows else 'Masked'}):")
    for idx, r in enumerate(records[:3], 1):
        if show_rows:
            print(f"    Row {idx}: {r}")
        else:
            masked = {k: mask_value(v) for k, v in r.items()}
            print(f"    Row {idx}: {masked}")

    # 4. Diagnostics & Recommendations
    print("\n[+] Health Diagnostics:")
    unmapped = [h for h, m in mappings.items() if m["canonical"] == "ignore"]
    if unmapped:
        print(f"    - {len(unmapped)} column(s) left unmapped: {', '.join(unmapped)}")
    else:
        print("    - All columns mapped to canonical fields successfully.")

    print("=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Offline universal file prober for Case Connect AI")
    parser.add_argument("path", help="Path to file or directory to probe")
    parser.add_argument("--show-rows", action="store_true", help="Print unmasked raw row values")
    args = parser.parse_args()

    target = Path(args.path)
    if not target.exists():
        print(f"Error: Target path {target} does not exist.")
        sys.exit(1)

    if target.is_file():
        probe_single_file(target, show_rows=args.show_rows)
    else:
        for f in sorted(target.iterdir()):
            if f.is_file() and f.suffix.lower() in [".csv", ".xlsx", ".json", ".jsonl"]:
                probe_single_file(f, show_rows=args.show_rows)

if __name__ == "__main__":
    main()
