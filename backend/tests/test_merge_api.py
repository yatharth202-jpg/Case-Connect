import csv
import hashlib
import io
import openpyxl
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal,
    User,
    CaseMember,
    EvidenceFile,
    ExtractionRecord,
    Annotation,
    AuditLog,
    Job,
)
from backend.app.auth.security import hash_password
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _get_user_and_token(username: str, role: str) -> tuple[str, str]:
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(
            username=username,
            password_hash=hash_password("Pass1234!"),
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    uid = u.id
    db.close()

    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    assert res.status_code == 200
    return uid, res.json()["access_token"]


def _setup_case_with_members():
    inv_id, inv_token = _get_user_and_token("p4_inv_owner", "investigator")
    viewer_id, viewer_token = _get_user_and_token("p4_viewer_mem", "viewer")
    outsider_id, outsider_token = _get_user_and_token("p4_outsider", "investigator")

    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {inv_token}"},
        json={"title": "Phase 4 Merge API Suite", "description": "Testing Phase 4 endpoints", "priority": "high"},
    )
    assert res.status_code == 200
    case_id = res.json()["id"]

    db = SessionLocal()
    exists = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == case_id, CaseMember.user_id == viewer_id)
        .first()
    )
    if not exists:
        db.add(CaseMember(case_id=case_id, user_id=viewer_id, role="viewer"))
        db.commit()
    db.close()

    return {
        "case_id": case_id,
        "inv_id": inv_id,
        "inv_headers": {"Authorization": f"Bearer {inv_token}"},
        "viewer_id": viewer_id,
        "viewer_headers": {"Authorization": f"Bearer {viewer_token}"},
        "outsider_headers": {"Authorization": f"Bearer {outsider_token}"},
    }


def _create_evidence_record(case_id: str, user_id: str, filename: str, ev_type: str = "bank_transactions") -> str:
    db = SessionLocal()
    ev = EvidenceFile(
        case_id=case_id,
        original_name=filename,
        stored_path="",
        file_size=128,
        sha256=hashlib.sha256(filename.encode("utf-8")).hexdigest(),
        detected_type=ev_type,
        uploader_id=user_id,
        status="ingested",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    ev_id = ev.id
    db.close()
    return ev_id


def test_empty_case_returns_clean_empty_collections():
    ctx = _setup_case_with_members()
    cid = ctx["case_id"]
    headers = ctx["inv_headers"]

    r_rec = client.get(f"/cases/{cid}/records", headers=headers)
    assert r_rec.status_code == 200
    assert r_rec.json()["items"] == []
    assert r_rec.json()["total"] == 0

    r_conf = client.get(f"/cases/{cid}/conflicts", headers=headers)
    assert r_conf.status_code == 200
    assert r_conf.json() == []

    r_runs = client.get(f"/cases/{cid}/ingest-runs", headers=headers)
    assert r_runs.status_code == 200
    assert r_runs.json() == []

    r_ann = client.get(f"/cases/{cid}/annotations", headers=headers)
    assert r_ann.status_code == 200
    assert r_ann.json() == []

    r_ms = client.get(f"/cases/{cid}/master-sheet?format=json&view=wide", headers=headers)
    assert r_ms.status_code == 200
    assert r_ms.json()["rows"] == []


def test_merge_preview_apply_history_conflict_and_rollback_endpoints():
    gen = SyntheticDataGenerator(seed=401)
    acc1 = gen.generate_account()
    acc2 = gen.generate_account()
    ctx = _setup_case_with_members()
    cid = ctx["case_id"]
    headers = ctx["inv_headers"]

    ev1 = _create_evidence_record(cid, ctx["inv_id"], "stmt_part1.csv", "bank_transactions")
    ev2 = _create_evidence_record(cid, ctx["inv_id"], "stmt_part2.csv", "bank_transactions")

    payload1 = {
        "record_type": "transaction",
        "source_kind": "structured_file",
        "method": "structured",
        "default_confidence": 0.90,
        "records": [
            {
                "txn_id": "UTR-P4-1001",
                "from_account": acc1,
                "to_account": acc2,
                "amount_paise": 250000,
                "date_iso": "2026-09-01",
                "narration": "IMPS Transfer Batch A",
                "channel": "IMPS",
                "utr_sub_code": "SUB-889",
            }
        ],
    }

    # 1. Preview does not write to DB
    r_prev = client.post(f"/cases/{cid}/evidence/{ev1}/merge/preview", headers=headers, json=payload1)
    assert r_prev.status_code == 200
    prev_data = r_prev.json()
    assert prev_data["mode"] == "preview"
    assert prev_data["counts"]["new"] == 1

    db = SessionLocal()
    assert db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid).count() == 0
    db.close()

    # 2. Apply File 1 (creates job and runs background merge)
    r_app1 = client.post(f"/cases/{cid}/evidence/{ev1}/merge/apply", headers=headers, json=payload1)
    assert r_app1.status_code == 200
    app1_data = r_app1.json()
    assert app1_data["job_id"] is not None
    assert app1_data["evidence_id"] == ev1

    db = SessionLocal()
    j1 = db.query(Job).filter(Job.id == app1_data["job_id"]).first()
    db.close()
    assert j1 is not None
    assert j1.status == "done"

    # 3. Verify GET /cases/{id}/records returns the record + extra_json field
    r_recs = client.get(f"/cases/{cid}/records?type=transaction&q=SUB-889", headers=headers)
    assert r_recs.status_code == 200
    recs_json = r_recs.json()
    assert recs_json["total"] == 1
    record_id = recs_json["items"][0]["id"]
    assert recs_json["items"][0]["extra"]["utr_sub_code"] == "SUB-889"
    source_ev_ids = [s["evidence_id"] for s in recs_json["items"][0]["sources"]]
    assert ev1 in source_ev_ids

    # 4. Apply File 2 with same natural key, conflicting narration (same trust & confidence), and another extra column
    payload2 = {
        "record_type": "transaction",
        "source_kind": "structured_file",
        "method": "structured",
        "default_confidence": 0.90,
        "records": [
            {
                "txn_id": "UTR-P4-1001",
                "from_account": acc1,
                "to_account": acc2,
                "amount_paise": 250000,
                "date_iso": "2026-09-01",
                "narration": "NEFT Adjustment Entry",
                "branch_terminal_id": "TERM-42",
            }
        ],
    }
    r_app2 = client.post(f"/cases/{cid}/evidence/{ev2}/merge/apply", headers=headers, json=payload2)
    assert r_app2.status_code == 200

    # 5. Check open conflicts via GET /cases/{id}/conflicts
    r_conf = client.get(f"/cases/{cid}/conflicts?status=open", headers=headers)
    assert r_conf.status_code == 200
    conflicts = r_conf.json()
    assert len(conflicts) >= 1
    narr_conflict = next(c for c in conflicts if c["field_name"] == "narration")
    conflict_id = narr_conflict["id"]
    assert len(narr_conflict["candidates"]) == 2

    # 6. Resolve conflict via POST /conflicts/{cid}/resolve
    chosen_claim_id = narr_conflict["candidates"][1]["claim_id"]
    r_res = client.post(
        f"/conflicts/{conflict_id}/resolve",
        headers=headers,
        json={"claim_id": chosen_claim_id, "note": "Verified against bank scroll"},
    )
    assert r_res.status_code == 200
    assert r_res.json()["locked"] is True

    # 7. Verify claim & golden history via GET /cases/{id}/entities/{eid}/history and /records/{rid}/history
    r_hist = client.get(f"/cases/{cid}/entities/{record_id}/history", headers=headers)
    assert r_hist.status_code == 200
    hist_data = r_hist.json()
    assert hist_data["fields"]["narration"]["locked"] is True
    assert hist_data["fields"]["narration"]["selected_by"] == "officer"
    assert len(hist_data["fields"]["narration"]["claims"]) >= 2

    r_hist_rec = client.get(f"/cases/{cid}/records/{record_id}/history", headers=headers)
    assert r_hist_rec.status_code == 200
    assert r_hist_rec.json()["record_id"] == record_id

    # 8. Check ingest runs via GET /cases/{id}/ingest-runs
    r_runs = client.get(f"/cases/{cid}/ingest-runs", headers=headers)
    assert r_runs.status_code == 200
    runs = r_runs.json()
    assert len(runs) >= 2

    # 9. Rollback File 2 via POST /cases/{id}/evidence/{ev2}/rollback
    r_rb2 = client.post(f"/cases/{cid}/evidence/{ev2}/rollback", headers=headers)
    assert r_rb2.status_code == 200
    rb2_data = r_rb2.json()
    assert rb2_data["job_id"] is not None

    # Verify rollback run was recorded in ingest-runs
    r_runs_after = client.get(f"/cases/{cid}/ingest-runs", headers=headers)
    modes = [r["mode"] for r in r_runs_after.json()]
    assert "rollback" in modes


def test_master_sheet_export_formats_sha256_and_audit():
    gen = SyntheticDataGenerator(seed=402)
    acc1 = gen.generate_account()
    acc2 = gen.generate_account()
    ctx = _setup_case_with_members()
    cid = ctx["case_id"]
    headers = ctx["inv_headers"]

    ev1 = _create_evidence_record(cid, ctx["inv_id"], "export_test.csv", "bank_transactions")
    payload = {
        "record_type": "transaction",
        "source_kind": "structured_file",
        "method": "structured",
        "default_confidence": 0.95,
        "records": [
            {
                "txn_id": "UTR-EXP-01",
                "from_account": acc1,
                "to_account": acc2,
                "amount_paise": 500000,
                "date_iso": "2026-09-05",
                "custom_gateway_tag": "GW-ALPHA",
                "device_fingerprint_tag": "DFP-99",
            }
        ],
    }
    r_app = client.post(f"/cases/{cid}/evidence/{ev1}/merge/apply", headers=headers, json=payload)
    assert r_app.status_code == 200

    # 1. JSON wide export
    r_json = client.get(f"/cases/{cid}/master-sheet?format=json&view=wide", headers=headers)
    assert r_json.status_code == 200
    assert r_json.headers.get("X-Export-SHA256") == hashlib.sha256(r_json.content).hexdigest()
    jdata = r_json.json()
    assert "custom_gateway_tag" in jdata["columns"]
    assert "device_fingerprint_tag" in jdata["columns"]
    assert "custom_gateway_tag" in jdata["extra_columns"]
    assert jdata["rows"][0]["custom_gateway_tag"] == "GW-ALPHA"
    assert jdata["rows"][0]["record_type"] == "transaction"

    # 2. CSV wide export
    r_csv = client.get(f"/cases/{cid}/master-sheet?format=csv&view=wide", headers=headers)
    assert r_csv.status_code == 200
    assert r_csv.headers.get("X-Export-SHA256") == hashlib.sha256(r_csv.content).hexdigest()
    reader = list(csv.DictReader(io.StringIO(r_csv.content.decode("utf-8"))))
    assert len(reader) == 1
    assert reader[0]["custom_gateway_tag"] == "GW-ALPHA"
    assert reader[0]["device_fingerprint_tag"] == "DFP-99"

    # 3. XLSX per_type export
    r_xlsx = client.get(f"/cases/{cid}/master-sheet?format=xlsx&view=per_type", headers=headers)
    assert r_xlsx.status_code == 200
    assert r_xlsx.headers.get("X-Export-SHA256") == hashlib.sha256(r_xlsx.content).hexdigest()
    wb = openpyxl.load_workbook(io.BytesIO(r_xlsx.content))
    assert "transaction" in wb.sheetnames
    ws = wb["transaction"]
    sheet_headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    assert "custom_gateway_tag" in sheet_headers
    assert "record_id" in sheet_headers

    # Verify EXPORT was written to audit_log
    db = SessionLocal()
    export_logs = (
        db.query(AuditLog)
        .filter(AuditLog.case_id == cid, AuditLog.action == "EXPORT")
        .all()
    )
    db.close()
    assert len(export_logs) == 3


def test_annotations_crud_soft_delete_and_permissions():
    ctx = _setup_case_with_members()
    cid = ctx["case_id"]
    inv_headers = ctx["inv_headers"]
    viewer_headers = ctx["viewer_headers"]
    outsider_headers = ctx["outsider_headers"]

    # 1. Create annotation as investigator
    r_create = client.post(
        f"/cases/{cid}/annotations",
        headers=inv_headers,
        json={
            "subject_type": "record",
            "subject_id": "rec-sample-1",
            "note_text": "Verified transaction narration against branch ledger.",
            "tags": ["verified-ledger", "priority-review"],
        },
    )
    assert r_create.status_code == 200
    ann_id = r_create.json()["id"]
    assert r_create.json()["tags"] == ["verified-ledger", "priority-review"]

    # 2. Viewer can list annotations
    r_list = client.get(f"/cases/{cid}/annotations", headers=viewer_headers)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    # 3. Viewer CANNOT create or delete annotations (403)
    r_v_create = client.post(
        f"/cases/{cid}/annotations",
        headers=viewer_headers,
        json={"subject_type": "record", "subject_id": "rec-sample-1", "note_text": "Viewer note"},
    )
    assert r_v_create.status_code == 403

    r_v_del = client.delete(f"/cases/{cid}/annotations/{ann_id}", headers=viewer_headers)
    assert r_v_del.status_code == 403

    # 4. Outsider receives 403 on case-scoped endpoints (BOLA defense)
    assert client.get(f"/cases/{cid}/records", headers=outsider_headers).status_code == 403
    assert client.get(f"/cases/{cid}/master-sheet", headers=outsider_headers).status_code == 403
    assert client.get(f"/cases/{cid}/annotations", headers=outsider_headers).status_code == 403

    # 5. Viewer receives 403 on apply and rollback
    ev1 = _create_evidence_record(cid, ctx["inv_id"], "perm_test.csv", "bank_transactions")
    assert (
        client.post(f"/cases/{cid}/evidence/{ev1}/merge/apply", headers=viewer_headers, json={}).status_code
        == 403
    )
    assert client.post(f"/cases/{cid}/evidence/{ev1}/rollback", headers=viewer_headers).status_code == 403

    # 6. Soft-delete annotation as investigator
    r_del = client.delete(f"/cases/{cid}/annotations/{ann_id}", headers=inv_headers)
    assert r_del.status_code == 200
    assert r_del.json()["is_deleted"] is True

    # Active list is now empty, but row still exists in SQLite with is_deleted=True
    r_list_after = client.get(f"/cases/{cid}/annotations", headers=inv_headers)
    assert r_list_after.json() == []

    db = SessionLocal()
    ann_row = db.query(Annotation).filter(Annotation.id == ann_id).first()
    db.close()
    assert ann_row is not None
    assert ann_row.is_deleted is True
    assert ann_row.deleted_at is not None
