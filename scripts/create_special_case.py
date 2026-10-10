import time
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def create_and_populate_special_case():
    print("="*60)
    print("CREATING DEDICATED SPECIAL CRIME CASE FOR DEEP ANALYSIS")
    print("="*60)

    # 1. Login
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "investigator1",
        "password": "OfficerPass1234!"
    })
    if login_resp.status_code != 200:
        print("Login failed:", login_resp.text)
        return
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Logged in as investigator1")

    # 2. Create Case
    case_payload = {
        "title": "Operation Cyber Shield — Special Analysis Case (FIR 882/2026)",
        "description": "Inter-state cyber extortion, burner SIM rotation & mule bank accounts syndicate active across Delhi NCR and Haryana. Comprehensive telecom & banking forensic correlation.",
        "priority": "high"
    }
    create_resp = requests.post(f"{BASE_URL}/cases", headers=headers, json=case_payload)
    if create_resp.status_code not in (200, 201):
        print("Case creation failed:", create_resp.text)
        return
    case_data = create_resp.json()
    case_id = case_data["id"]
    print(f"[OK] Created Case: '{case_data['title']}' (ID: {case_id})")

    # 3. Upload and Ingest Evidence Files
    samples_dir = Path("data/synthetic/samples/clean")
    files_to_upload = [
        ("cdr.csv", "cdr", samples_dir / "cdr.csv", "text/csv"),
        ("bank_transactions.csv", "bank_transactions", samples_dir / "bank_transactions.csv", "text/csv"),
        ("FIR-2026-101.txt", "fir", samples_dir / "FIR-2026-101.txt", "text/plain"),
    ]

    for fname, ftype, fpath, mime in files_to_upload:
        if not fpath.exists():
            print(f"[WARN] File not found: {fpath}")
            continue

        print(f"\n[+] Uploading {fname}...")
        with open(fpath, "rb") as f:
            up_resp = requests.post(
                f"{BASE_URL}/cases/{case_id}/evidence",
                headers=headers,
                files={"files": (fname, f, mime)}
            )
        
        if up_resp.status_code not in (200, 201):
            print(f"[ERR] Upload failed for {fname}:", up_resp.text)
            continue
        
        ev_id = up_resp.json()[0]["id"]
        sha = up_resp.json()[0]["sha256"]
        print(f"    Uploaded successfully (ID: {ev_id}, SHA: {sha[:16]}...)")

        if ftype in ("cdr", "bank_transactions"):
            # Preview and map
            prev_resp = requests.get(f"{BASE_URL}/evidence/{ev_id}/preview", headers=headers)
            if prev_resp.status_code == 200:
                prev_data = prev_resp.json()
                mapping = {
                    h: prev_data["suggested_mapping"][h]["canonical"]
                    for h in prev_data.get("headers", [])
                    if h in prev_data.get("suggested_mapping", {})
                }
                requests.post(
                    f"{BASE_URL}/evidence/{ev_id}/mapping",
                    headers=headers,
                    json={"file_type": ftype, "mapping": mapping}
                )
                print(f"    Mapping configured: {len(mapping)} columns mapped")

            # Ingest
            requests.post(f"{BASE_URL}/evidence/{ev_id}/ingest", headers=headers)
            print(f"    Ingestion triggered for {fname}")

        elif ftype == "fir":
            # Document entity extraction
            ext_resp = requests.post(f"{BASE_URL}/evidence/{ev_id}/extract", headers=headers)
            print(f"    FIR entity extraction triggered (Status: {ext_resp.status_code})")

    # 4. Wait for ingestion jobs
    print("\nProcessing analytical models (waiting 3s)...")
    time.sleep(3)

    # 5. Generate Entity Matches / Deduplication
    match_resp = requests.post(f"{BASE_URL}/cases/{case_id}/matches/generate", headers=headers)
    print(f"[OK] Entity Deduplication / Matches generated: {match_resp.status_code}")

    # 6. Rebuild Graph
    rebuild_resp = requests.post(f"{BASE_URL}/cases/{case_id}/graph/rebuild", headers=headers)
    print(f"[OK] Criminal Network Graph compiled: {rebuild_resp.status_code}")

    # 7. Recompute Analytics & Alerts
    recomp_resp = requests.post(f"{BASE_URL}/cases/{case_id}/settings/recompute", headers=headers)
    print(f"[OK] Forensic Analytics & Lead Scoring computed: {recomp_resp.status_code}")

    # 8. Fetch Overview Stats
    stats_resp = requests.get(f"{BASE_URL}/cases/{case_id}/analytics/overview", headers=headers)
    if stats_resp.status_code == 200:
        stats = stats_resp.json()
        print("\n" + "="*60)
        print("CASE FORENSIC SUMMARY READY FOR INSPECTION:")
        print(f"• Total Calls Analyzed:      {stats.get('total_calls', 'N/A')}")
        print(f"• Total Transactions:        {stats.get('total_transactions', 'N/A')}")
        print(f"• Total Siphoned Volume:     INR {stats.get('total_transaction_amount_inr', 'N/A'):,}")
        print(f"• Active Identified Targets: {stats.get('total_entities', 'N/A')}")
        print(f"• Bank Accounts Tracked:     {stats.get('total_accounts', 'N/A')}")
        print("="*60)

    print(f"\nTarget Case ID: {case_id}")
    return case_id

if __name__ == "__main__":
    create_and_populate_special_case()
