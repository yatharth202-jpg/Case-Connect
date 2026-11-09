import json
import pytest
from backend.app.db.sql import (
    SessionLocal,
    User,
    Case,
    ExtractionRecord,
    RecordSource,
    FieldClaim,
    GoldenField,
    MergeConflict,
    IngestRun,
    SchemaRegistry,
    Transaction,
    CallRecord,
    Entity,
    AuditLog,
)
from backend.app.auth.security import hash_password
from backend.app.services.merge.engine import (
    apply_evidence_merge,
    resolve_conflict_by_officer,
    rollback_evidence_merge,
    MergeConcurrencyError,
    _get_case_lock,
)
from backend.app.services.graph.builder import build_detail_graph
from scripts.generate_data import SyntheticDataGenerator


def _make_user_and_case(username: str, title: str):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(username=username, password_hash=hash_password("Pass1234!"), role="investigator", is_active=True)
        db.add(u)
        db.commit()
        db.refresh(u)
    c = Case(title=title, description="Phase 3 Merge Engine Test", status="active", created_by=u.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    uid, cid = u.id, c.id
    db.close()
    return uid, cid


def test_new_same_new_field_and_unknown_extra_fields():
    gen = SyntheticDataGenerator(seed=301)
    acc1 = gen.generate_account()
    acc2 = gen.generate_account()
    uid, cid = _make_user_and_case("p3_inv_1", "New Same New-Field Case")
    db = SessionLocal()

    rec_v1 = {
        "txn_id": "TXN-P3-001",
        "from_account": acc1,
        "to_account": acc2,
        "amount_paise": 150000,
        "date_iso": "2026-08-10",
    }

    # 1. Preview mode must not persist any records
    prev_res = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-file-1",
        record_type="transaction",
        records=[rec_v1],
        user_id=uid,
        preview=True,
    )
    assert prev_res["mode"] == "preview"
    assert prev_res["counts"]["new"] == 1
    assert db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid).count() == 0

    # 2. Apply File 1 -> NEW record
    res1 = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-file-1",
        record_type="transaction",
        records=[rec_v1],
        user_id=uid,
        preview=False,
    )
    assert res1["counts"]["new"] == 1
    ext_rec = db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid).first()
    assert ext_rec is not None
    assert ext_rec.status == "active"
    assert ext_rec.staged_table == "transactions"

    # 3. Re-ingest File 1 identically -> Idempotent (SAME = 1, 0 new claims)
    claim_count_before = db.query(FieldClaim).filter(FieldClaim.case_id == cid).count()
    res_idem = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-file-1",
        record_type="transaction",
        records=[rec_v1],
        user_id=uid,
    )
    assert res_idem["counts"]["same"] == 1
    assert res_idem["counts"]["new"] == 0
    assert db.query(FieldClaim).filter(FieldClaim.case_id == cid).count() == claim_count_before

    # 4. Ingest File 2 with same key + a new known field ('reference') + an unknown extra field ('branch_terminal_code')
    rec_v2 = {
        **rec_v1,
        "reference": "NEFT-CORROBORATED-01",
        "branch_terminal_code": "BR-DEL-099",
    }
    res2 = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-file-2",
        record_type="transaction",
        records=[rec_v2],
        user_id=uid,
    )
    assert res2["counts"]["new"] == 0
    assert res2["counts"]["new_fields"] == 1
    db.refresh(ext_rec)
    data_parsed = json.loads(ext_rec.data_json)
    extra_parsed = json.loads(ext_rec.extra_json)
    assert data_parsed["reference"] == "NEFT-CORROBORATED-01"
    assert extra_parsed["branch_terminal_code"] == "BR-DEL-099"

    # Verify RecordSource has both ev-file-1 and ev-file-2
    sources = db.query(RecordSource).filter(RecordSource.record_id == ext_rec.id).all()
    assert {s.evidence_id for s in sources} == {"ev-file-1", "ev-file-2"}

    # Verify unknown field registered in schema_registry
    reg = (
        db.query(SchemaRegistry)
        .filter(
            SchemaRegistry.record_type == "transaction",
            SchemaRegistry.field_name == "branch_terminal_code",
        )
        .first()
    )
    assert reg is not None
    assert reg.seen_count >= 1
    db.close()


def test_trust_order_win_margin_conflict_and_locked_officer_resolution():
    gen = SyntheticDataGenerator(seed=302)
    acc1 = gen.generate_account()
    acc2 = gen.generate_account()
    uid, cid = _make_user_and_case("p3_inv_2", "Conflict & Lock Case")
    db = SessionLocal()

    # 1. Ingest OCR printed record (lower trust rank)
    ocr_rec = {
        "txn_id": "TXN-P3-CONF-1",
        "from_account": acc1,
        "to_account": acc2,
        "amount_paise": 200000,
        "date_iso": "2026-08-12",
        "reference": "OCR-REF-NOISY",
    }
    apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-ocr",
        record_type="transaction",
        records=[ocr_rec],
        user_id=uid,
        source_kind="ocr_printed",
        default_confidence=0.82,
    )

    # 2. Ingest structured_file record (higher trust rank) with different reference -> auto-wins by trust order!
    struct_rec1 = {
        **ocr_rec,
        "reference": "STRUCT-REF-ALPHA",
    }
    res_trust = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-struct-1",
        record_type="transaction",
        records=[struct_rec1],
        user_id=uid,
        source_kind="structured_file",
        default_confidence=0.90,
    )
    assert res_trust["counts"]["conflicts"] == 0
    assert res_trust["counts"]["updated"] == 1
    ext_rec = db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid).first()
    assert json.loads(ext_rec.data_json)["reference"] == "STRUCT-REF-ALPHA"

    # 3. Ingest second structured_file with different reference and confidence within margin (0.92 vs 0.90, diff 0.02 < 0.08) -> CONFLICT!
    struct_rec2 = {
        **ocr_rec,
        "reference": "STRUCT-REF-BETA",
    }
    res_conf = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-struct-2",
        record_type="transaction",
        records=[struct_rec2],
        user_id=uid,
        source_kind="structured_file",
        default_confidence=0.92,
    )
    assert res_conf["counts"]["conflicts"] == 1
    open_conflict = (
        db.query(MergeConflict)
        .filter(MergeConflict.case_id == cid, MergeConflict.status == "open")
        .first()
    )
    assert open_conflict is not None
    assert open_conflict.field_name == "reference"

    # Previous golden value ('STRUCT-REF-ALPHA') is preserved while conflict is open
    db.refresh(ext_rec)
    assert json.loads(ext_rec.data_json)["reference"] == "STRUCT-REF-ALPHA"

    # 4. Officer resolves conflict by picking 'STRUCT-REF-BETA' claim -> locks field
    beta_claim = (
        db.query(FieldClaim)
        .filter(
            FieldClaim.subject_id == ext_rec.id,
            FieldClaim.field_name == "reference",
            FieldClaim.value_norm == "STRUCT-REF-BETA",
        )
        .first()
    )
    res_resolve = resolve_conflict_by_officer(
        db=db,
        conflict_id=open_conflict.id,
        selected_claim_id=beta_claim.id,
        officer_id=uid,
        note="Verified against original bank voucher",
    )
    assert res_resolve["locked"] is True
    assert res_resolve["selected_value"] == "STRUCT-REF-BETA"

    db.refresh(ext_rec)
    assert json.loads(ext_rec.data_json)["reference"] == "STRUCT-REF-BETA"
    staged_txn = db.query(Transaction).filter(Transaction.id == ext_rec.staged_id).first()
    assert staged_txn.reference == "STRUCT-REF-BETA"

    # 5. Subsequent ingest of File 3 with 'STRUCT-REF-GAMMA' must NOT overwrite locked officer decision,
    #    and must emit a NEW_EVIDENCE_DIFFERS_FROM_LOCKED notice
    struct_rec3 = {
        **ocr_rec,
        "reference": "STRUCT-REF-GAMMA",
    }
    res_after_lock = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="ev-struct-3",
        record_type="transaction",
        records=[struct_rec3],
        user_id=uid,
        source_kind="structured_file",
        default_confidence=0.99,
    )
    db.refresh(ext_rec)
    assert json.loads(ext_rec.data_json)["reference"] == "STRUCT-REF-BETA"
    notices = res_after_lock["changes"][0].get("notices", [])
    assert any(n["notice"] == "NEW_EVIDENCE_DIFFERS_FROM_LOCKED" for n in notices)
    db.close()


def test_repeated_legitimate_rows_and_overlapping_statement_dedup():
    gen = SyntheticDataGenerator(seed=303)
    acc1 = gen.generate_account()
    acc2 = gen.generate_account()
    uid, cid = _make_user_and_case("p3_inv_3", "Occurrence Index Dedup Case")
    db = SessionLocal()

    # Two legitimate identical UPI transfers on the same day in Statement 1 (no unique txn_id)
    repeated_row = {
        "account": f"{acc1}->{acc2}",
        "from_account": acc1,
        "to_account": acc2,
        "date_iso": "2026-08-14",
        "amount_paise": 50000,
        "direction": "debit",
        "balance_after_paise": 100000,
        "reference": "UPI/REPEAT/500",
    }
    res1 = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="stmt-month-1",
        record_type="transaction",
        records=[repeated_row, repeated_row],
        user_id=uid,
    )
    # Both legitimate rows in the same file are kept (occurrence_idx 1 and 2)
    assert res1["counts"]["new"] == 2
    assert db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid, ExtractionRecord.status == "active").count() == 2

    # Statement 2 overlaps with Statement 1 (contains those 2 rows + 1 new row)
    third_row = {
        **repeated_row,
        "amount_paise": 75000,
        "reference": "UPI/NEW/750",
    }
    res2 = apply_evidence_merge(
        db=db,
        case_id=cid,
        evidence_id="stmt-month-2",
        record_type="transaction",
        records=[repeated_row, repeated_row, third_row],
        user_id=uid,
    )
    assert res2["counts"]["same"] == 2
    assert res2["counts"]["new"] == 1
    assert db.query(ExtractionRecord).filter(ExtractionRecord.case_id == cid, ExtractionRecord.status == "active").count() == 3
    db.close()


def test_order_independence_and_rollback_restores_golden_values_and_graph():
    gen = SyntheticDataGenerator(seed=304)
    p1 = gen.generate_phone()
    p2 = gen.generate_phone()
    p3 = gen.generate_phone()

    # Batch A: lower-trust OCR call record + 1 tie-confidence record
    batch_a = [
        {
            "caller": p1,
            "receiver": p2,
            "datetime_iso": "2026-08-15T10:00:00Z",
            "duration_seconds": 120,
            "call_type": "voice",
            "cell_id": "CELL-OCR-1",
            "_source_kind": "ocr_printed",
            "_confidence": 0.78,
        },
        {
            "caller": p1,
            "receiver": p3,
            "datetime_iso": "2026-08-15T11:00:00Z",
            "duration_seconds": 60,
            "call_type": "voice",
            "cell_id": "CELL-TIE-A",
            "_source_kind": "structured_file",
            "_confidence": 0.90,
        },
    ]

    # Batch B: higher-trust structured call record for (p1, p2) + tie-confidence record for (p1, p3) + 1 B-only call
    batch_b = [
        {
            "caller": p1,
            "receiver": p2,
            "datetime_iso": "2026-08-15T10:00:00Z",
            "duration_seconds": 120,
            "call_type": "voice",
            "cell_id": "CELL-STRUCT-WIN",
            "_source_kind": "structured_file",
            "_confidence": 0.95,
        },
        {
            "caller": p1,
            "receiver": p3,
            "datetime_iso": "2026-08-15T11:00:00Z",
            "duration_seconds": 60,
            "call_type": "voice",
            "cell_id": "CELL-TIE-B",
            "_source_kind": "structured_file",
            "_confidence": 0.92,
        },
        {
            "caller": p2,
            "receiver": p3,
            "datetime_iso": "2026-08-15T12:00:00Z",
            "duration_seconds": 45,
            "call_type": "voice",
            "cell_id": "CELL-ONLY-B",
            "_source_kind": "structured_file",
            "_confidence": 0.95,
        },
    ]

    # Case 1: Ingest A then B
    uid1, cid1 = _make_user_and_case("p3_order_1", "Order A then B")
    # Case 2: Ingest B then A
    uid2, cid2 = _make_user_and_case("p3_order_2", "Order B then A")
    db = SessionLocal()

    apply_evidence_merge(db, cid1, "file-A", "call", batch_a, uid1)
    apply_evidence_merge(db, cid1, "file-B", "call", batch_b, uid1)

    apply_evidence_merge(db, cid2, "file-B", "call", batch_b, uid2)
    apply_evidence_merge(db, cid2, "file-A", "call", batch_a, uid2)

    # Compare auto-resolved fields (record 1: cell_id must be 'CELL-STRUCT-WIN' in BOTH cases)
    r1_c1 = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == cid1, ExtractionRecord.data_json.contains("CELL-STRUCT-WIN"))
        .first()
    )
    r1_c2 = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == cid2, ExtractionRecord.data_json.contains("CELL-STRUCT-WIN"))
        .first()
    )
    assert r1_c1 is not None and r1_c2 is not None
    assert json.loads(r1_c1.data_json)["cell_id"] == json.loads(r1_c2.data_json)["cell_id"] == "CELL-STRUCT-WIN"

    # Both cases must have exactly 1 open conflict on 'cell_id' for the tied record (p1 -> p3)
    confs_c1 = db.query(MergeConflict).filter(MergeConflict.case_id == cid1, MergeConflict.status == "open").all()
    confs_c2 = db.query(MergeConflict).filter(MergeConflict.case_id == cid2, MergeConflict.status == "open").all()
    assert len(confs_c1) == 1 and len(confs_c2) == 1
    assert confs_c1[0].field_name == confs_c2[0].field_name == "cell_id"

    # Now test ROLLBACK of file-B in Case 1:
    # - Record (p1, p2) cell_id must revert to 'CELL-OCR-1'
    # - Open conflict on (p1, p3) must resolve automatically to 'CELL-TIE-A'
    # - Record (p2, p3) ('CELL-ONLY-B') must be retracted and its CallRecord.is_active set to False
    rb_res = rollback_evidence_merge(db, cid1, "file-B", uid1)
    assert rb_res["counts"]["records_retracted"] == 1
    assert rb_res["counts"]["records_restored_to_prior_evidence"] == 2

    db.refresh(r1_c1)
    assert json.loads(r1_c1.data_json)["cell_id"] == "CELL-OCR-1"
    assert db.query(MergeConflict).filter(MergeConflict.case_id == cid1, MergeConflict.status == "open").count() == 0

    retracted_rec = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == cid1, ExtractionRecord.status == "retracted")
        .first()
    )
    assert retracted_rec is not None
    staged_call = db.query(CallRecord).filter(CallRecord.id == retracted_rec.staged_id).first()
    assert staged_call.is_active is False

    # Graph for Case 1 must NOT contain the retracted (p2 -> p3) CALLED edge
    g = build_detail_graph(db, cid1)
    assert not g.has_edge(f"{cid1}|Phone|{p2}", f"{cid1}|Phone|{p3}")
    assert g.has_edge(f"{cid1}|Phone|{p1}", f"{cid1}|Phone|{p2}")

    # Verify audit_log entries exist for merge_apply, merge_rollback
    audit_actions = {
        a.action for a in db.query(AuditLog).filter(AuditLog.case_id == cid1).all()
    }
    assert "merge_apply" in audit_actions
    assert "merge_rollback" in audit_actions
    db.close()


def test_person_entities_never_merged_by_name_and_concurrency_lock():
    gen = SyntheticDataGenerator(seed=305)
    p_name = f"{gen.fake.first_name()} {gen.fake.last_name()}"
    uid, cid = _make_user_and_case("p3_person_inv", "Person Non-Merge Case")
    db = SessionLocal()

    person_rec = {
        "label": "Person",
        "canonical_id": p_name.lower(),
        "display_name": p_name,
    }
    apply_evidence_merge(db, cid, "fir-doc-1", "entity", [person_rec], uid)
    apply_evidence_merge(db, cid, "fir-doc-2", "entity", [person_rec], uid)

    # Must create 2 distinct ExtractionRecords (Person entities are never auto-merged by name)
    person_records = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == cid, ExtractionRecord.record_type == "entity")
        .all()
    )
    assert len(person_records) == 2

    # Concurrency guard check: holding the case lock causes concurrent apply to raise MergeConcurrencyError
    lock = _get_case_lock(cid)
    lock.acquire()
    try:
        with pytest.raises(MergeConcurrencyError):
            apply_evidence_merge(db, cid, "fir-doc-3", "entity", [person_rec], uid)
    finally:
        lock.release()
    db.close()

