import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, EvidenceFile, CallRecord, Transaction, Entity, RejectedRow
)
from backend.app.auth.security import hash_password
from backend.app.services.ingestion.readers import (
    read_tabular_file_detailed,
    iter_tabular_chunks,
    TabularReadError,
)
from backend.app.services.ingestion.detect import detect_file_type, detect_file_sections
from backend.app.services.ingestion.mapping import (
    suggest_column_mappings,
    compute_header_signature,
    compute_column_content_profile,
    save_mapping_template,
    check_mapping_template_drift,
)
from backend.app.services.ingestion.stage import stage_evidence_file
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _ensure_user_and_case(username: str, case_title: str):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(username=username, password_hash=hash_password("Pass1234!"), role="investigator", is_active=True)
        db.add(u)
        db.commit()
        db.refresh(u)
    c = Case(title=case_title, description="Phase 2 test case", status="active", created_by=u.id)
    db.add(c)
    db.commit()
    db.refresh(c)
    uid, cid = u.id, c.id
    db.close()
    return uid, cid


@pytest.fixture(scope="module")
def phase2_suite_dir(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("phase2_messy")
    gen = SyntheticDataGenerator(seed=108)
    data = gen.build_scenario_data("ring", "small")
    manifest = gen.write_phase2_messy_suite(data, out_dir)
    return out_dir, manifest, data


def test_preamble_repeated_headers_and_opening_closing_balances(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir
    csv_path = suite_dir / "statement_preamble_balances.csv"

    detailed = read_tabular_file_detailed(csv_path)
    records = detailed["records"]
    headers = detailed["headers"]
    meta = detailed["file_metadata"]

    # Exact row count: opening balance, repeated header, closing balance, and grand total must not be treated as transactions
    assert len(records) == manifest["statement_txn_count"]
    assert meta["opening_balance_paise"] == manifest["opening_balance_paise"]
    assert meta["closing_balance_paise"] == manifest["closing_balance_paise"]
    assert meta["repeated_headers_dropped"] == 1
    assert meta["total_rows_dropped"] >= 3  # opening + closing + grand total
    assert meta["statement_owner"]["owner_found"] is True
    assert meta["statement_owner"]["account_number"] == manifest["owner_account"]
    assert meta["statement_owner"]["ifsc"] == "SBIN0001234"


def test_multiline_headers_and_cp1252_semicolon_csv(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir

    # 1. Multi-line header CSV
    ml_det = read_tabular_file_detailed(suite_dir / "bank_multiline_header.csv")
    assert len(ml_det["records"]) == manifest["multiline_txn_count"]
    det_type = detect_file_type(ml_det["headers"], ml_det["records"])
    assert det_type["detected_type"] == "bank_transactions"

    # 2. CP1252 semicolon-delimited CSV
    cp_det = read_tabular_file_detailed(suite_dir / "cdr_cp1252_semicolon.csv")
    assert len(cp_det["records"]) == manifest["cp1252_call_count"]
    assert cp_det["file_metadata"]["delimiter"] == ";"
    cdr_type = detect_file_type(cp_det["headers"], cp_det["records"])
    assert cdr_type["detected_type"] == "cdr"


def test_multi_sheet_merged_xlsx_and_hidden_row_filtering(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir
    xlsx_path = suite_dir / "multi_sheet_merged.xlsx"

    detailed = read_tabular_file_detailed(xlsx_path)
    meta = detailed["file_metadata"]

    # Primary sheet is CDR_Log; hidden junk row (row 4) must be excluded
    assert len(detailed["records"]) == manifest["xlsx_cdr_count"]
    assert all(r.get("Call Type") != "JUNK_HIDDEN" for r in detailed["records"])

    # Multi-sheet detection must report both CDR_Log (cdr) and SDR_Identity (identity_table)
    assert meta["multi_sheet"] is True
    assert len(meta["sheets"]) == 2
    sec_info = detect_file_sections(meta, detailed["headers"], detailed["records"])
    assert sec_info["has_multiple_sections"] is True
    assert sec_info["has_multiple_record_types"] is True
    types_by_sheet = {s["sheet_name"]: s["detected_type"] for s in sec_info["sections"]}
    assert types_by_sheet["CDR_Log"] == "cdr"
    assert types_by_sheet["SDR_Identity"] == "identity_table"

    # Staging the multi-sheet workbook stages both the CDR sheet and the SDR identity sheet
    uid, cid = _ensure_user_and_case("p2_xlsx_user", "Multi-Sheet XLSX Case")
    db = SessionLocal()
    ev = EvidenceFile(
        case_id=cid,
        original_name="multi_sheet_merged.xlsx",
        stored_path=str(xlsx_path),
        sha256="p2_xlsx_hash",
        file_size=xlsx_path.stat().st_size,
        uploader_id=uid,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    sug = suggest_column_mappings("cdr", detailed["headers"], detailed["records"])
    flat_map = {h: v["canonical"] for h, v in sug.items()}
    res = stage_evidence_file(db, ev.id, uid, "cdr", flat_map)
    assert res["rows_ingested"] == manifest["xlsx_cdr_count"] + manifest["xlsx_sdr_count"]
    assert res["rows_rejected"] == 0
    assert db.query(CallRecord).filter(CallRecord.case_id == cid).count() == manifest["xlsx_cdr_count"]
    assert db.query(Entity).filter(Entity.case_id == cid, Entity.label == "Person").count() == manifest["xlsx_sdr_count"]
    db.close()


def test_multipage_pdf_bank_statement_stitching_and_wrapped_narrations(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir
    pdf_path = suite_dir / "statement_multipage.pdf"

    detailed = read_tabular_file_detailed(pdf_path)
    records = detailed["records"]
    headers = detailed["headers"]
    meta = detailed["file_metadata"]

    # Wrapped narrations on page 1 joined into parent row; repeated header on page 2 dropped; closing balance captured
    assert len(records) == manifest["statement_txn_count"]
    assert meta["opening_balance_paise"] == manifest["opening_balance_paise"]
    assert meta["closing_balance_paise"] == manifest["closing_balance_paise"]
    assert meta["repeated_headers_dropped"] >= 1
    assert meta["statement_owner"]["owner_found"] is True
    assert meta["statement_owner"]["account_number"] == manifest["owner_account"]

    # Provenance: page 1 and page 2 row markers preserved
    pages_seen = {r.get("_page_no") for r in records}
    assert 1 in pages_seen and 2 in pages_seen

    # Wrapped narration pieces were joined back together (contain account suffix after 2nd slash)
    assert all(len(str(r.get("Narration", "")).split("/")) >= 3 for r in records)

    # Detect file type recognizes tabular PDF as bank_statement
    det = detect_file_type(headers, records, filename="statement_multipage.pdf", banners=detailed["banner_rows"])
    assert det["detected_type"] == "bank_statement"


def test_owner_unknown_statement_blocks_edge_creation_until_confirmed(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir
    pdf_ownerless = suite_dir / "statement_ownerless.pdf"

    uid, cid = _ensure_user_and_case("p2_owner_user", "Ownerless Statement Case")
    db = SessionLocal()
    ev = EvidenceFile(
        case_id=cid,
        original_name="statement_ownerless.pdf",
        stored_path=str(pdf_ownerless),
        sha256="p2_ownerless_hash",
        file_size=pdf_ownerless.stat().st_size,
        uploader_id=uid,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    detailed = read_tabular_file_detailed(pdf_ownerless)
    sug = suggest_column_mappings("bank_statement", detailed["headers"], detailed["records"])
    flat_map = {h: v["canonical"] for h, v in sug.items()}

    # 1. Stage without statement_account -> must block with needs_owner_confirmation and create ZERO transactions
    res_blocked = stage_evidence_file(db, ev.id, uid, "bank_statement", flat_map, statement_account=None)
    assert res_blocked["status"] == "needs_owner_confirmation"
    assert res_blocked["needs_owner_confirmation"] is True
    assert res_blocked["rows_ingested"] == 0
    assert db.query(Transaction).filter(Transaction.case_id == cid).count() == 0

    # 2. Officer confirms owner account -> staging succeeds and creates all transactions
    res_confirmed = stage_evidence_file(
        db, ev.id, uid, "bank_statement", flat_map, statement_account=manifest["owner_account"]
    )
    assert res_confirmed["status"] == "ingested"
    assert res_confirmed["needs_owner_confirmation"] is False
    assert res_confirmed["rows_ingested"] == 3
    assert db.query(Transaction).filter(Transaction.case_id == cid).count() == 3
    db.close()


def test_content_based_column_mapping_and_template_drift_detection(phase2_suite_dir):
    _, _, data = phase2_suite_dir
    calls = data["calls"][:10]

    # Obfuscated headers where only content profile can identify the columns
    obfuscated_headers = ["Col_Alpha", "Col_Beta", "Col_Gamma", "Col_Delta"]
    obfuscated_records = [
        {
            "Col_Alpha": c["caller"],
            "Col_Beta": c["receiver"],
            "Col_Gamma": c["date"],
            "Col_Delta": str(c["duration_seconds"]),
        }
        for c in calls
    ]

    sug = suggest_column_mappings("cdr", obfuscated_headers, obfuscated_records)
    assert sug["Col_Alpha"]["canonical"] in ("caller", "receiver")
    assert sug["Col_Beta"]["canonical"] in ("caller", "receiver")
    assert sug["Col_Gamma"]["canonical"] in ("date", "datetime")
    assert len(sug["Col_Alpha"]["candidates"]) <= 3
    assert sug["Col_Alpha"]["content_profile"]["phone_ratio"] == 1.0

    # Template drift test: save template for standard CDR headers, then test drift scenarios
    db = SessionLocal()
    base_headers = ["A-Party", "B-Party", "Call Date", "Dur(sec)"]
    base_records = [
        {"A-Party": c["caller"], "B-Party": c["receiver"], "Call Date": c["date"], "Dur(sec)": str(c["duration_seconds"])}
        for c in calls
    ]
    sig = compute_header_signature(base_headers)
    col_profiles = {h: compute_column_content_profile([r[h] for r in base_records]) for h in base_headers}
    save_mapping_template(
        db,
        sig,
        "cdr",
        {"A-Party": "caller", "B-Party": "receiver", "Call Date": "date", "Dur(sec)": "duration"},
        headers=base_headers,
        column_profiles=col_profiles,
    )

    # 1. Exact match -> no drift
    drift_none = check_mapping_template_drift(db, "cdr", base_headers, base_records)
    assert drift_none["has_drift"] is False
    assert drift_none["requires_confirmation"] is False

    # 2. Column added + removed -> drift detected
    drifted_headers = ["A-Party", "B-Party", "Call Date", "Cell Tower ID"]
    drift_cols = check_mapping_template_drift(db, "cdr", drifted_headers, base_records)
    assert drift_cols["has_drift"] is True
    assert "Cell Tower ID" in drift_cols["added_columns"]
    assert "Dur(sec)" in drift_cols["removed_columns"]
    assert drift_cols["requires_confirmation"] is True

    # 3. Same header names, but 'A-Party' column now contains non-phone text/dates -> type drift detected
    corrupted_records = [
        {"A-Party": "2026-08-15", "B-Party": c["receiver"], "Call Date": c["date"], "Dur(sec)": str(c["duration_seconds"])}
        for c in calls
    ]
    drift_type = check_mapping_template_drift(db, "cdr", base_headers, corrupted_records)
    assert drift_type["has_drift"] is True
    assert any(tc["column"] == "A-Party" for tc in drift_type["type_changed_columns"])
    assert drift_type["requires_confirmation"] is True
    db.close()


def test_mixed_file_section_splitting_and_dd_mm_vs_mm_dd_and_streaming(phase2_suite_dir):
    suite_dir, manifest, _ = phase2_suite_dir

    # 1. Mixed file (CDR + Bank Transactions in one CSV)
    mixed_path = suite_dir / "mixed_cdr_and_bank.csv"
    mixed_det = read_tabular_file_detailed(mixed_path)
    assert mixed_det["file_metadata"]["is_mixed_file"] is True
    assert len(mixed_det["file_metadata"]["sections"]) == 2

    uid, cid = _ensure_user_and_case("p2_mixed_user", "Mixed & Date Case")
    db = SessionLocal()
    ev_mix = EvidenceFile(
        case_id=cid,
        original_name="mixed_cdr_and_bank.csv",
        stored_path=str(mixed_path),
        sha256="p2_mixed_hash",
        file_size=mixed_path.stat().st_size,
        uploader_id=uid,
    )
    db.add(ev_mix)
    db.commit()
    db.refresh(ev_mix)

    sug_cdr = suggest_column_mappings("cdr", mixed_det["headers"], mixed_det["records"])
    map_cdr = {h: v["canonical"] for h, v in sug_cdr.items()}
    res_mix = stage_evidence_file(db, ev_mix.id, uid, "cdr", map_cdr)
    assert res_mix["rows_ingested"] == manifest["mixed_cdr_count"] + manifest["mixed_bank_count"]
    assert res_mix["rows_rejected"] == 0

    # 2. DD/MM vs MM/DD column-level date inference
    for fname in ("cdr_dd_mm.csv", "cdr_mm_dd.csv"):
        fpath = suite_dir / fname
        ev_d = EvidenceFile(
            case_id=cid,
            original_name=fname,
            stored_path=str(fpath),
            sha256=f"hash_{fname}",
            file_size=fpath.stat().st_size,
            uploader_id=uid,
        )
        db.add(ev_d)
        db.commit()
        db.refresh(ev_d)
        det_d = read_tabular_file_detailed(fpath)
        sug_d = suggest_column_mappings("cdr", det_d["headers"], det_d["records"])
        res_d = stage_evidence_file(db, ev_d.id, uid, "cdr", {h: v["canonical"] for h, v in sug_d.items()})
        # Both files represent 2026-08-05 and 2026-08-21
        assert res_d["date_range"]["min"] == "2026-08-05"
        assert res_d["date_range"]["max"] == "2026-08-21"

    # 3. Streaming chunked reader test (chunk_size=2)
    chunks = list(iter_tabular_chunks(suite_dir / "cdr_cp1252_semicolon.csv", chunk_size=2))
    assert len(chunks) == 3
    assert sum(len(ch["records"]) for ch in chunks) == manifest["cp1252_call_count"]
    db.close()


def test_api_preview_drift_guard_and_zero_silent_drops(phase2_suite_dir, tmp_path):
    suite_dir, manifest, data = phase2_suite_dir

    # Create investigator user and login
    db = SessionLocal()
    u = db.query(User).filter(User.username == "p2_api_inv").first()
    if not u:
        u = User(username="p2_api_inv", password_hash=hash_password("Pass1234!"), role="investigator", is_active=True)
        db.add(u)
        db.commit()
    db.close()

    login_res = client.post("/auth/login", json={"username": "p2_api_inv", "password": "Pass1234!"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    case_res = client.post("/cases", headers=headers, json={"title": "Phase 2 API Case"})
    case_id = case_res.json()["id"]

    # 1. Upload statement_preamble_balances.csv and verify /preview returns balances, owner, normalized preview rows, and top-3 candidates
    stmt_path = suite_dir / "statement_preamble_balances.csv"
    with open(stmt_path, "rb") as f:
        up_res = client.post(f"/cases/{case_id}/evidence", headers=headers, files={"files": ("statement_preamble_balances.csv", f, "text/csv")})
    ev_id = up_res.json()[0]["id"]

    prev = client.get(f"/evidence/{ev_id}/preview", headers=headers)
    assert prev.status_code == 200
    p_data = prev.json()
    assert p_data["detected_type"] == "bank_statement"
    assert p_data["file_metadata"]["opening_balance_paise"] == manifest["opening_balance_paise"]
    assert p_data["file_metadata"]["closing_balance_paise"] == manifest["closing_balance_paise"]
    assert p_data["file_metadata"]["statement_owner"]["account_number"] == manifest["owner_account"]
    assert len(p_data["normalized_preview_rows"]) == manifest["statement_txn_count"]
    for col_info in p_data["suggested_mapping"].values():
        assert "candidates" in col_info
        assert "content_profile" in col_info

    # 2. Verify zero silent drops: create a file with 3 valid CDR rows + 2 malformed rows -> rows_read=5, rows_ingested=3, rows_rejected=2
    calls = data["calls"][:3]
    partial_bad_csv = tmp_path / "cdr_with_bad_rows.csv"
    with open(partial_bad_csv, "w", encoding="utf-8", newline="") as f:
        f.write("A-Party,B-Party,Call Date,Call Time,Dur(sec)\n")
        for c in calls:
            f.write(f"{c['caller']},{c['receiver']},{c['date']},{c['time']},{c['duration_seconds']}\n")
        f.write(f",{calls[0]['receiver']},2026-08-10,12:00:00,30\n")  # Missing caller
        f.write("INVALID_NUM,,2026-08-10,12:05:00,15\n")  # Invalid caller & missing receiver

    with open(partial_bad_csv, "rb") as f:
        up_bad = client.post(f"/cases/{case_id}/evidence", headers=headers, files={"files": ("cdr_with_bad_rows.csv", f, "text/csv")})
    ev_bad_id = up_bad.json()[0]["id"]

    db = SessionLocal()
    u = db.query(User).filter(User.username == "p2_api_inv").first()
    res_bad = stage_evidence_file(
        db,
        ev_bad_id,
        u.id,
        "cdr",
        {"A-Party": "caller", "B-Party": "receiver", "Call Date": "date", "Call Time": "time", "Dur(sec)": "duration"},
    )
    assert res_bad["rows_read"] == 5
    assert res_bad["rows_ingested"] == 3
    assert res_bad["rows_rejected"] == 2
    assert res_bad["rows_read"] == res_bad["rows_ingested"] + res_bad["rows_rejected"] + res_bad["duplicates_skipped"]
    db.close()

    rej_res = client.get(f"/evidence/{ev_bad_id}/rejected-rows", headers=headers)
    assert rej_res.status_code == 200
    assert len(rej_res.json()) == 2
    assert all(r["reason"] == "MISSING_OR_INVALID_PHONE_NUMBER" for r in rej_res.json())

