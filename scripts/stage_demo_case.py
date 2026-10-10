import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

def stage_demo_data(case_id: str):
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

    print(f"Logged in. Staging data into case: {case_id}")

    # 2. Upload CDR and Bank files
    samples_dir = Path("data/synthetic/samples/clean")
    files_to_upload = [
        ("cdr.csv", "cdr", samples_dir / "cdr.csv"),
        ("bank_transactions.csv", "bank_transactions", samples_dir / "bank_transactions.csv"),
    ]

    for fname, ftype, fpath in files_to_upload:
        if not fpath.exists():
            print(f"File not found: {fpath}")
            continue

        print(f"\nUploading {fname}...")
        with open(fpath, "rb") as f:
            up_resp = requests.post(
                f"{BASE_URL}/cases/{case_id}/evidence",
                headers=headers,
                files={"files": (fname, f, "text/csv")}
            )
        
        if up_resp.status_code not in (200, 201):
            print(f"Upload error for {fname}:", up_resp.text)
            continue
        
        ev_id = up_resp.json()[0]["id"]
        print(f"Uploaded! Evidence ID: {ev_id}")

        # Preview
        prev_resp = requests.get(f"{BASE_URL}/evidence/{ev_id}/preview", headers=headers)
        if prev_resp.status_code != 200:
            print(f"Preview error:", prev_resp.text)
            continue
        prev_data = prev_resp.json()

        # Build mapping
        mapping = {h: prev_data["suggested_mapping"][h]["canonical"] for h in prev_data["headers"] if h in prev_data["suggested_mapping"]}
        
        # Confirm mapping
        map_resp = requests.post(
            f"{BASE_URL}/evidence/{ev_id}/mapping",
            headers=headers,
            json={"file_type": ftype, "mapping": mapping}
        )
        print(f"Mapping confirmed. Result: {map_resp.status_code}")

        # Ingest
        stage_resp = requests.post(
            f"{BASE_URL}/evidence/{ev_id}/ingest",
            headers=headers
        )
        print(f"Triggered ingestion for {fname}:", stage_resp.status_code, stage_resp.json())

    # Wait for ingestion background jobs to finish
    import time
    print("Waiting 3 seconds for background ingestion jobs to finish...")
    time.sleep(3)

    # 3. Rebuild graph
    rebuild_resp = requests.post(f"{BASE_URL}/cases/{case_id}/graph/rebuild", headers=headers)
    print("\nGraph rebuild status:", rebuild_resp.status_code, rebuild_resp.json() if rebuild_resp.status_code == 200 else rebuild_resp.text)

if __name__ == "__main__":
    stage_demo_data("12dacddb-75ce-4097-aac1-cdb59d5e22b6")
