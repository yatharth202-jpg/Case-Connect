import os
import sys
import json
import uuid
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import SessionLocal, Case, User, EvidenceFile, Entity, CallRecord, Transaction, Alert

client = TestClient(app)

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    data = resp.json()
    assert data.get("sqlite") == "ok"
    assert data.get("status") in ("healthy", "sqlite_online_neo4j_offline")
    print(f"[PASS] 1. Backend /health is OK (Status: {data.get('status')}, SQLite: ok)")

def test_authentication():
    # 1. Investigator login
    resp = client.post("/auth/login", json={"username": "investigator1", "password": "OfficerPass1234!"})
    assert resp.status_code == 200, f"Investigator login failed: {resp.text}"
    inv_token = resp.json()["access_token"]
    
    # 2. Admin login
    resp = client.post("/auth/login", json={"username": "admin", "password": "AdminPass1234!"})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    admin_token = resp.json()["access_token"]

    # 3. Viewer login
    resp = client.post("/auth/login", json={"username": "viewer1", "password": "ViewerPass1234!"})
    assert resp.status_code == 200, f"Viewer login failed: {resp.text}"
    viewer_token = resp.json()["access_token"]

    print("[PASS] 2. Authentication & JWT issuing verified for all roles (admin, investigator, viewer)")
    return inv_token, admin_token, viewer_token

def test_cases_and_rbac(inv_token, admin_token, viewer_token):
    headers_inv = {"Authorization": f"Bearer {inv_token}"}
    headers_adm = {"Authorization": f"Bearer {admin_token}"}
    headers_viw = {"Authorization": f"Bearer {viewer_token}"}

    # List cases
    resp = client.get("/cases", headers=headers_inv)
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) > 0, "No cases found in DB!"
    print(f"[PASS] 3. Cases listing OK ({len(cases)} cases available)")

    # Find Operation RedSand
    redsand = next((c for c in cases if "RedSand" in c["title"]), None)
    assert redsand is not None, "Operation RedSand case missing!"
    cid = redsand["id"]

    # Verify Viewer cannot access admin audit verification
    resp_viw_audit = client.get("/audit/verify", headers=headers_viw)
    assert resp_viw_audit.status_code == 403, f"Viewer should receive 403 on /audit/verify, got {resp_viw_audit.status_code}!"
    
    # Verify Admin can access audit
    resp_adm_audit = client.get("/audit/verify", headers=headers_adm)
    assert resp_adm_audit.status_code == 200, f"Admin must access /audit/verify, got {resp_adm_audit.status_code}!"
    print("[PASS] 4. RBAC security enforcement strictly active")
    return cid

def test_forensic_analytics(cid, inv_token):
    headers = {"Authorization": f"Bearer {inv_token}"}

    # 1. Overview analytics
    resp = client.get(f"/cases/{cid}/analytics/overview", headers=headers)
    assert resp.status_code == 200, f"Overview failed: {resp.text}"
    ov = resp.json()
    assert ov["total_entities"] > 0
    print(f"[PASS] 5. Overview analytics: {ov['total_entities']} entities, {ov['total_calls']} calls, {ov['total_txns']} txns, Volume: INR {ov['total_money_volume_rs']:,}")

    # 2. Graph projection
    resp = client.get(f"/cases/{cid}/graph/search", headers=headers)
    assert resp.status_code == 200, f"Graph failed: {resp.text}"
    graph = resp.json()
    assert len(graph.get("nodes", [])) > 0
    print(f"[PASS] 6. NetworkX criminal graph compiled: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

    # 3. Money Trail
    resp = client.get(f"/cases/{cid}/money-trail", headers=headers)
    assert resp.status_code == 200, f"Money trail failed: {resp.text}"
    trail = resp.json()
    print(f"[PASS] 7. Money Trail BFS flow active: {len(trail.get('nodes', []))} accounts in flow")

    # 4. Lead Advisor
    resp = client.get(f"/cases/{cid}/leads", headers=headers)
    assert resp.status_code == 200, f"Leads failed: {resp.text}"
    leads_data = resp.json()
    leads = leads_data.get("leads", [])
    assert len(leads) > 0, "No leads generated!"
    top_lead = leads[0]
    print(f"[PASS] 8. Lead Advisor scored top lead: '{top_lead.get('display_name')}' (Type: {top_lead.get('entity_type')}, Priority: {top_lead.get('level')}, Score: {top_lead.get('score')})")

def test_court_dossier_pdf(cid, inv_token):
    headers = {"Authorization": f"Bearer {inv_token}"}
    req_body = {
        "report_title": "Section 63 BSA 2023 Verification Dossier",
        "format": "pdf",
        "sections": {
            "overview": True,
            "entities": True,
            "cdr": True,
            "financial": True,
            "documents": True,
            "audit": True
        },
        "officer_name": "Inspector Meera Sundaram",
        "officer_rank": "Lead Forensic Investigator",
        "officer_station": "Special Cell, Lodhi Colony",
        "officer_unit": "Organised Crime Syndicate Unit",
        "officer_remarks": "Court dossier integrity verified under Section 63 BSA 2023."
    }
    resp = client.post(f"/cases/{cid}/reports", headers=headers, json=req_body)
    assert resp.status_code in (200, 201), f"Report creation failed: {resp.text}"
    report_data = resp.json()
    assert "id" in report_data
    assert "sha256" in report_data
    print(f"[PASS] 9. Section 63 BSA 2023 PDF Dossier engine generated report (SHA-256: {report_data['sha256'][:16]}...)")

def test_sample_cases_on_disk():
    sample_dir = ROOT_DIR / "docs" / "sample_cases"
    pdf1 = sample_dir / "Operation_RedSand_Hawala_Syndicate_Dossier.pdf"
    pdf2 = sample_dir / "Operation_Cyber_Shield_Syndicate_Dossier.pdf"
    assert pdf1.exists() and pdf1.stat().st_size > 5000, "RedSand dossier PDF missing or truncated!"
    assert pdf2.exists() and pdf2.stat().st_size > 5000, "Cyber Shield dossier PDF missing or truncated!"
    
    evidence_dir = sample_dir / "evidence"
    assert evidence_dir.exists() and len(list(evidence_dir.glob("*"))) >= 5, "Sample evidence files missing!"
    print(f"[PASS] 10. Sample cases documentation & PDFs confirmed: {pdf1.name} ({pdf1.stat().st_size // 1024} KB), {pdf2.name} ({pdf2.stat().st_size // 1024} KB)")

def main():
    print("=" * 60)
    print("  CASE CONNECT AI — 360-DEGREE SYSTEM VERIFICATION")
    print("=" * 60)
    test_health()
    inv_tok, adm_tok, viw_tok = test_authentication()
    cid = test_cases_and_rbac(inv_tok, adm_tok, viw_tok)
    test_forensic_analytics(cid, inv_tok)
    test_court_dossier_pdf(cid, inv_tok)
    test_sample_cases_on_disk()
    print("=" * 60)
    print("  ALL 10 SUBSYSTEM CHECKS PASSED WITH ZERO ERRORS!")
    print("=" * 60)

if __name__ == "__main__":
    main()
