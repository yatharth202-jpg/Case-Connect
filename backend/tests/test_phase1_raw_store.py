
"""
Test Suite for Phase 1: Lossless Raw Store & Reconciliation Invariant.
Tests the complete robustness fixture pack against the non-negotiable rules:
  1. Lossless capture of every row and column in raw_sheets and raw_rows.
  2. Reconciliation invariant: rows_in_file == staged + rejected + preamble + blank.
  3. Preservation of exact string values (leading zeros, unstripped text).
  4. Preservation of unmapped extra columns in raw_json.
  5. Idempotent re-uploads and surgical single-file rollback.
"""

import json
import os
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from backend.app.db.sql import (
    Base, engine, SessionLocal,
    User, Case, EvidenceFile, RawSheet, RawRow,
    CallRecord, Transaction, RejectedRow
)
from backend.app.services.ingestion.raw_store import (
    capture_raw_file_lossless,
    reconcile_evidence_file,
    rollback_evidence_file,
)
from tests.fixtures.generate import generate_fixtures


@pytest.fixture(scope="module")
def setup_db_and_fixtures():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Generate robustness test fixtures if absent
    fixture_dir = Path("tests/fixtures/generated")
    if not (fixture_dir / "fixture_1_shuffled_cdr_pipe.csv").exists():
        generate_fixtures(output_dir=str(fixture_dir), scale_rows=100)

    # Setup test user and case
    test_user = db.query(User).filter(User.username == "test_officer_raw_store").first()
    if not test_user:
        test_user = User(
            username="test_officer_raw_store",
            password_hash="mock_hash",
            role="investigator",
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

    test_case = db.query(Case).filter(Case.title == "Test Case Lossless Raw Store").first()
    if not test_case:
        test_case = Case(
            title="Test Case Lossless Raw Store",
            description="Case for testing lossless raw evidence store",
            created_by=test_user.id,
        )
        db.add(test_case)
        db.commit()
        db.refresh(test_case)

    yield db, test_case, test_user
    db.close()


def test_lossless_capture_and_reconciliation_across_fixtures(setup_db_and_fixtures):
    """Verifies that all varied robustness fixtures are captured losslessly and satisfy reconciliation."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")

    fixture_files = [
        "fixture_1_shuffled_cdr_pipe.csv",
        "fixture_2_bank_lakh_semicolon.csv",
        "fixture_3_bank_signed_tab.tsv",
        "fixture_4_multisheet_evidence.xlsx",
        "fixture_5b_header_only.csv",
        "fixture_5c_one_row_leading_zeros.csv",
    ]

    for fname in fixture_files:
        fpath = fixture_dir / fname
        if not fpath.exists():
            continue

        # Register evidence file
        ev = EvidenceFile(
            case_id=case.id,
            original_name=fname,
            stored_path=str(fpath.resolve()),
            file_size=fpath.stat().st_size,
            sha256="mock_sha256",
            detected_type="cdr" if "cdr" in fname else "bank_statement",
            uploader_id=user.id,
            status="uploaded",
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)

        # Execute lossless capture
        capture_res = capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)
        assert capture_res["total_rows"] > 0, f"Expected rows captured for {fname}"

        # Verify raw_sheets entries exist
        sheets = db.query(RawSheet).filter(RawSheet.evidence_file_id == ev.id).all()
        assert len(sheets) >= 1, f"Expected RawSheet records for {fname}"

        # Enforce independent reconciliation invariant
        recon = reconcile_evidence_file(db=db, evidence_file_id=ev.id, file_path=fpath)
        assert recon["is_reconciled"] is True, f"Reconciliation failed for {fname}: {recon}"

        for sh_res in recon["sheets"]:
            assert sh_res["discrepancy"] == 0, f"Discrepancy must be 0 for sheet {sh_res['sheet_name']}"
            assert sh_res["rows_in_file"] == sh_res["db_total"]


def test_leading_zeros_and_exact_strings_preserved(setup_db_and_fixtures):
    """Verifies that phone numbers and accounts with leading zeros are preserved as exact strings."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")
    fpath = fixture_dir / "fixture_5c_one_row_leading_zeros.csv"

    ev = EvidenceFile(
        case_id=case.id,
        original_name=fpath.name,
        stored_path=str(fpath.resolve()),
        file_size=fpath.stat().st_size,
        sha256="mock_sha_zeros",
        detected_type="text/csv",
        uploader_id=user.id,
        status="uploaded",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)

    # Data row is row_no=2 (row_no=1 is header)
    data_row = db.query(RawRow).filter(
        RawRow.evidence_file_id == ev.id,
        RawRow.row_no == 2
    ).first()
    assert data_row is not None

    row_data = json.loads(data_row.raw_json)
    # Check that leading zero in phone '09876543210' was NOT stripped to '9876543210'
    assert "09876543210" in row_data.values()
    # Check that leading zeros in account '000123456789' were NOT stripped
    assert "000123456789" in row_data.values()


def test_unmapped_extra_columns_preserved(setup_db_and_fixtures):
    """Verifies that unknown extra columns remain stored in raw_rows.raw_json without error."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")
    fpath = fixture_dir / "fixture_1_shuffled_cdr_pipe.csv"

    ev = EvidenceFile(
        case_id=case.id,
        original_name=fpath.name,
        stored_path=str(fpath.resolve()),
        file_size=fpath.stat().st_size,
        sha256="mock_sha_extra",
        detected_type="text/csv",
        uploader_id=user.id,
        status="uploaded",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)

    # Pick any data row (after preamble)
    rows = db.query(RawRow).filter(
        RawRow.evidence_file_id == ev.id,
        RawRow.status == "staged"
    ).all()
    assert len(rows) > 0

    # Ensure every column from the file is present in raw_json
    sample_row = json.loads(rows[10].raw_json)
    # 6 columns were written in fixture 1
    assert len(sample_row) == 6


def test_idempotent_reupload(setup_db_and_fixtures):
    """Verifies that re-uploading the same evidence file cleans up and replaces earlier raw rows without duplication."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")
    fpath = fixture_dir / "fixture_3_bank_signed_tab.tsv"

    ev = EvidenceFile(
        case_id=case.id,
        original_name=fpath.name,
        stored_path=str(fpath.resolve()),
        file_size=fpath.stat().st_size,
        sha256="mock_sha_idempotent",
        detected_type="text/tab-separated-values",
        uploader_id=user.id,
        status="uploaded",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    res1 = capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)
    count1 = db.query(RawRow).filter(RawRow.evidence_file_id == ev.id).count()

    # Second capture (simulating re-upload)
    res2 = capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)
    count2 = db.query(RawRow).filter(RawRow.evidence_file_id == ev.id).count()

    assert count1 == count2 == res1["total_rows"] == res2["total_rows"]


def test_surgical_single_file_rollback(setup_db_and_fixtures):
    """Verifies that rolling back an evidence file deletes only its records and leaves other files intact."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")
    fpath1 = fixture_dir / "fixture_5b_header_only.csv"
    fpath2 = fixture_dir / "fixture_5c_one_row_leading_zeros.csv"

    ev1 = EvidenceFile(case_id=case.id, original_name=fpath1.name, stored_path=str(fpath1.resolve()), file_size=10, sha256="sha1", detected_type="text/csv", uploader_id=user.id, status="uploaded")
    ev2 = EvidenceFile(case_id=case.id, original_name=fpath2.name, stored_path=str(fpath2.resolve()), file_size=20, sha256="sha2", detected_type="text/csv", uploader_id=user.id, status="uploaded")
    db.add_all([ev1, ev2])
    db.commit()

    capture_raw_file_lossless(db=db, evidence_file_id=ev1.id, file_path=fpath1)
    capture_raw_file_lossless(db=db, evidence_file_id=ev2.id, file_path=fpath2)

    ev1_count_before = db.query(RawRow).filter(RawRow.evidence_file_id == ev1.id).count()
    ev2_count_before = db.query(RawRow).filter(RawRow.evidence_file_id == ev2.id).count()
    assert ev1_count_before > 0
    assert ev2_count_before > 0

    # Roll back ev1 only
    rollback_res = rollback_evidence_file(db=db, evidence_file_id=ev1.id, case_id=case.id, user_id=user.id)
    assert rollback_res["status"] == "rolled_back"

    ev1_count_after = db.query(RawRow).filter(RawRow.evidence_file_id == ev1.id).count()
    ev2_count_after = db.query(RawRow).filter(RawRow.evidence_file_id == ev2.id).count()

    assert ev1_count_after == 0
    assert ev2_count_after == ev2_count_before


def test_reconciliation_failure_detection(setup_db_and_fixtures):
    """Verifies that if row count mismatches, reconciliation flags is_reconciled == False with discrepancy details."""
    db, case, user = setup_db_and_fixtures
    fixture_dir = Path("tests/fixtures/generated")
    fpath = fixture_dir / "fixture_5c_one_row_leading_zeros.csv"

    ev = EvidenceFile(case_id=case.id, original_name=fpath.name, stored_path=str(fpath.resolve()), file_size=20, sha256="sha_mismatch", detected_type="text/csv", uploader_id=user.id, status="uploaded")
    db.add(ev)
    db.commit()

    capture_raw_file_lossless(db=db, evidence_file_id=ev.id, file_path=fpath)

    # Artificially delete one raw row to induce discrepancy
    first_row = db.query(RawRow).filter(RawRow.evidence_file_id == ev.id).first()
    db.delete(first_row)
    db.commit()

    # Reconcile must now detect failure
    recon = reconcile_evidence_file(db=db, evidence_file_id=ev.id, file_path=fpath)
    assert recon["is_reconciled"] is False
    assert recon["sheets"][0]["discrepancy"] == 1
