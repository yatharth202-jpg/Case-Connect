import os
import re
import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Forbidden words (Rule 6)
FORBIDDEN_WORDS_REGEX = re.compile(r"\b(criminal|suspect|guilty|mastermind)\b", re.IGNORECASE)

# 10-digit mobile phone literals (Rule 1)
MOBILE_LITERAL_REGEX = re.compile(r"['\"](?:\+?91)?[6-9]\d{9}['\"]")

# 12-18 digit account literals (Rule 1)
ACCOUNT_LITERAL_REGEX = re.compile(r"['\"]\d{12,18}['\"]")

# Date literal 2015-2035 in code outside comments
DATE_LITERAL_REGEX = re.compile(r"['\"]20[123]\d[-/]\d{2}[-/]\d{2}['\"]")

# External CDN or API URLs in frontend/src
EXTERNAL_URL_REGEX = re.compile(r"https?://(?!localhost|127\.0\.0\.1|caseconnect\.internal)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Fixed rupee / paise threshold literals hardcoded in logic (Rule 1 & 4)
# Flags patterns like '> 500000' or '>= 100000' or 'amount == 50000'
FIXED_THRESHOLD_REGEX = re.compile(r"(?:amount|volume|balance|total|transfers?|paise)\s*(?:>=?|<=?|==)\s*[1-9]\d{4,9}\b")

def extract_sample_scenario_literals():
    """Extract all entity names, phone numbers, and account numbers from sample datasets."""
    samples_dir = ROOT_DIR / "data" / "synthetic" / "samples"
    names = set()
    numbers = set()
    if not samples_dir.exists():
        return names, numbers

    for gt_path in samples_dir.glob("**/ground_truth.json"):
        try:
            with open(gt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                planted = data.get("planted", {})
                for category, items in planted.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                if "name" in item and len(item["name"]) > 3:
                                    names.add(item["name"])
                                if "phone" in item:
                                    numbers.add(str(item["phone"]))
                                if "account" in item:
                                    numbers.add(str(item["account"]))
                    elif isinstance(items, dict):
                        if "name" in items and len(items["name"]) > 3:
                            names.add(items["name"])
                        if "phone" in items:
                            numbers.add(str(items["phone"]))
                        if "account" in items:
                            numbers.add(str(items["account"]))
        except Exception:
            continue
    return names, numbers

SAMPLE_NAMES, SAMPLE_NUMBERS = None, None

def load_allowlist():
    allowlist_path = ROOT_DIR / "scripts" / "audit_allowlist.txt"
    allowed = set()
    if allowlist_path.exists():
        with open(allowlist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    allowed.add(line.split("#")[0].strip())
    return allowed

def scan_file(file_path: Path, allowlist: set, sample_names: set = None, sample_numbers: set = None):
    findings = []
    try:
        rel_path = file_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        rel_path = file_path.as_posix()
    
    # Check for forbidden mock data files
    if file_path.suffix.lower() in [".json", ".csv"] and not file_path.name.startswith("package"):
        findings.append((rel_path, 1, f"Mock data file detected: {file_path.name}"))
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith(("//", "#", "/*", "*")):
                    continue

                check_key = f"{rel_path}:{line_no}"
                if check_key in allowlist or rel_path in allowlist:
                    continue

                # 1. Forbidden terms check
                if FORBIDDEN_WORDS_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"Forbidden prejudicial terminology found: {clean_line}"))

                # 2. Hardcoded mobile numbers
                if MOBILE_LITERAL_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"Hardcoded mobile number literal found: {clean_line}"))

                # 3. Hardcoded bank accounts
                if ACCOUNT_LITERAL_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"Hardcoded account number literal found: {clean_line}"))

                # 4. Hardcoded dates
                if DATE_LITERAL_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"Hardcoded date literal found: {clean_line}"))

                # 5. External host calls in frontend
                if "frontend/src" in rel_path and EXTERNAL_URL_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"External network URL found in frontend (offline violation): {clean_line}"))

                # 6. Committed sample scenario entities check (Rule 1 & 14)
                if sample_names:
                    for s_name in sample_names:
                        if s_name.lower() in clean_line.lower() and not clean_line.lower().startswith("import"):
                            findings.append((rel_path, line_no, f"Sample scenario entity name '{s_name}' found: {clean_line}"))
                if sample_numbers:
                    for s_num in sample_numbers:
                        if s_num in clean_line:
                            findings.append((rel_path, line_no, f"Sample scenario entity number '{s_num}' found: {clean_line}"))

                # 7. Fixed rupee / threshold literals in backend application code
                if "backend/app" in rel_path and FIXED_THRESHOLD_REGEX.search(clean_line):
                    findings.append((rel_path, line_no, f"Hardcoded fixed currency threshold found (must use defaults.yaml/case_settings): {clean_line}"))

    except Exception as e:
        findings.append((rel_path, 0, f"Error reading file: {e}"))

    return findings

def audit_directory(base_dir: Path, allowlist: set, sample_names: set = None, sample_numbers: set = None):
    all_findings = []
    if not base_dir.exists():
        return all_findings

    for root, dirs, files in os.walk(base_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in ["node_modules", "dist", "build", "__pycache__", ".venv", ".git", "pack"]]
        for file in files:
            if file.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".json", ".csv")):
                file_path = Path(root) / file
                all_findings.extend(scan_file(file_path, allowlist, sample_names, sample_numbers))

    return all_findings

def run_audit(target_dir=None):
    print("==================================================")
    print("    CASE CONNECT AI — HARDCODE & SECURITY AUDITOR ")
    print("==================================================")
    allowlist = load_allowlist()
    sample_names, sample_numbers = extract_sample_scenario_literals()
    print(f"Loaded {len(sample_names)} sample entity names and {len(sample_numbers)} sample entity numbers for strict anti-overfitting audit.")
    
    scan_targets = []
    if target_dir:
        scan_targets.append(Path(target_dir))
    else:
        scan_targets.append(ROOT_DIR / "backend" / "app")
        scan_targets.append(ROOT_DIR / "frontend" / "src")

    total_findings = []
    for target in scan_targets:
        print(f"Scanning target: {target}...")
        findings = audit_directory(target, allowlist, sample_names, sample_numbers)
        total_findings.extend(findings)

    print("--------------------------------------------------")
    if not total_findings:
        print("[PASS] Audit complete: 0 forbidden literals, mock files or prejudicial terms found.")
        print("==================================================")
        return True
    else:
        print(f"[FAIL] Audit failed: Found {len(total_findings)} violation(s):")
        for file, line, msg in total_findings:
            print(f"  * {file}:{line} -> {msg}")
        print("==================================================")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit codebase for hardcoded literals and mock patterns")
    parser.add_argument("--dir", help="Specific directory to audit")
    args = parser.parse_args()
    success = run_audit(args.dir)
    sys.exit(0 if success else 1)
