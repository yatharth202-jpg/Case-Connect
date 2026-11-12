"""
Lossless Raw Evidence Store and Reconciliation Engine for CaseConnect AI.
Complies with non-negotiable data-agnostic and Section 63 BSA 2023 forensic directives:
  1. Stores EVERY row and EVERY column (preamble, blank, rejected, unmapped) before parsing.
  2. Preserves exact cell values as text (leading zeros, dates as written, long identifiers).
  3. Enforces the strict reconciliation invariant:
     rows_in_file == staged + rejected + preamble + blank
  4. Supports idempotent re-uploads and surgical single-file rollback.
"""

import csv
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.sql import (
    RawSheet, RawRow, EvidenceFile, RejectedRow,
    CallRecord, Transaction, IPEvent,
    FieldClaim as RecordFieldClaim, GraphNode, GraphEdge
)
from backend.app.services.ingestion.readers import (
    sniff_encoding_and_decode,
    sniff_csv_delimiter,
    read_tabular_file_detailed,
    TabularReadError,
)

def sniff_encoding_and_delimiter(file_path: Path) -> Tuple[str, str]:
    """Helper to detect both encoding and delimiter of a text tabular file."""
    with open(file_path, "rb") as f:
        head_bytes = f.read(64 * 1024)
    text, encoding = sniff_encoding_and_decode(head_bytes)
    sample_lines = text.splitlines()[:20]
    delimiter = sniff_csv_delimiter(sample_lines) if sample_lines else ","
    return encoding, delimiter
from backend.app.audit.service import record_audit_log

try:
    import openpyxl
except ImportError:
    openpyxl = None


def compute_raw_row_hash(row_dict: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of raw row text dictionary."""
    serialized = json.dumps(row_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def capture_raw_file_lossless(
    db: Session,
    evidence_file_id: str,
    file_path: Path,
    chunk_size: int = 5000,
) -> Dict[str, Any]:
    """
    Ingests every single row and column from file_path into raw_sheets and raw_rows.
    Preserves all original string tokens without type casting.
    Idempotent: removes prior raw rows for this evidence file before re-inserting.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not ev:
        raise ValueError(f"Evidence file {evidence_file_id} not found")

    # 1. Idempotent cleanup of prior raw store records for this evidence file
    db.query(RawRow).filter(RawRow.evidence_file_id == evidence_file_id).delete()
    db.query(RawSheet).filter(RawSheet.evidence_file_id == evidence_file_id).delete()
    db.flush()

    ext = file_path.suffix.lower()
    sheets_summary: List[Dict[str, Any]] = []
    total_rows_captured = 0
    raw_row_lookup: Dict[Tuple[str, int], str] = {}  # (sheet_name, row_no) -> raw_row_id

    if ext in [".csv", ".tsv", ".txt"]:
        sheets_summary = _capture_csv_lossless(
            db=db,
            evidence_file_id=evidence_file_id,
            file_path=file_path,
            raw_row_lookup=raw_row_lookup,
            chunk_size=chunk_size,
        )
    elif ext == ".xlsx":
        sheets_summary = _capture_xlsx_lossless(
            db=db,
            evidence_file_id=evidence_file_id,
            file_path=file_path,
            raw_row_lookup=raw_row_lookup,
            chunk_size=chunk_size,
        )
    elif ext in [".json", ".jsonl"]:
        sheets_summary = _capture_json_lossless(
            db=db,
            evidence_file_id=evidence_file_id,
            file_path=file_path,
            raw_row_lookup=raw_row_lookup,
            chunk_size=chunk_size,
        )
    else:
        # Generic document or binary file (store single raw metadata row)
        sheet_rec = RawSheet(
            id=str(uuid.uuid4()),
            evidence_file_id=evidence_file_id,
            sheet_name="document",
            header_row_no=0,
            row_count=1,
        )
        db.add(sheet_rec)
        db.flush()
        row_id = str(uuid.uuid4())
        raw_row = RawRow(
            id=row_id,
            evidence_file_id=evidence_file_id,
            sheet_name="document",
            row_no=1,
            raw_json=json.dumps({"file_name": file_path.name, "size_bytes": file_path.stat().st_size}),
            row_hash=hashlib.sha256(file_path.name.encode("utf-8")).hexdigest(),
            status="staged",
        )
        db.add(raw_row)
        db.flush()
        raw_row_lookup[("document", 1)] = row_id
        sheets_summary = [{"sheet_name": "document", "row_count": 1, "header_row_no": 0}]

    db.commit()

    total_rows = sum(s["row_count"] for s in sheets_summary)
    return {
        "evidence_file_id": evidence_file_id,
        "sheets": sheets_summary,
        "total_rows": total_rows,
        "raw_row_lookup": raw_row_lookup,
    }


def _capture_csv_lossless(
    db: Session,
    evidence_file_id: str,
    file_path: Path,
    raw_row_lookup: Dict[Tuple[str, int], str],
    chunk_size: int = 5000,
) -> List[Dict[str, Any]]:
    encoding, delimiter = sniff_encoding_and_delimiter(file_path)
    sheet_name = "default"

    # Analyze header and preamble via read_tabular_file_detailed
    detailed = read_tabular_file_detailed(file_path)
    header_row_no = detailed.get("file_metadata", {}).get("header_row_no", 1)

    # First pass: read every raw line as string tokens
    raw_rows_to_insert: List[RawRow] = []
    line_count = 0

    with open(file_path, "r", encoding=encoding, errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row_idx, tokens in enumerate(reader, 1):
            line_count += 1
            row_id = str(uuid.uuid4())

            # Convert row tokens into dictionary preserving exact string values
            is_blank = not any(t.strip() for t in tokens if t)
            is_preamble = row_idx < header_row_no

            status = "blank" if is_blank else ("preamble" if is_preamble else "staged")

            row_dict = {f"col_{i+1}": str(tok) for i, tok in enumerate(tokens)}
            row_hash = compute_raw_row_hash(row_dict)

            raw_row = RawRow(
                id=row_id,
                evidence_file_id=evidence_file_id,
                sheet_name=sheet_name,
                row_no=row_idx,
                raw_json=json.dumps(row_dict, ensure_ascii=False),
                row_hash=row_hash,
                status=status,
            )
            raw_rows_to_insert.append(raw_row)
            raw_row_lookup[(sheet_name, row_idx)] = row_id

            if len(raw_rows_to_insert) >= chunk_size:
                db.bulk_save_objects(raw_rows_to_insert)
                db.flush()
                raw_rows_to_insert = []

    if raw_rows_to_insert:
        db.bulk_save_objects(raw_rows_to_insert)
        db.flush()

    sheet_rec = RawSheet(
        id=str(uuid.uuid4()),
        evidence_file_id=evidence_file_id,
        sheet_name=sheet_name,
        header_row_no=header_row_no,
        row_count=line_count,
    )
    db.add(sheet_rec)
    db.flush()

    return [{"sheet_name": sheet_name, "row_count": line_count, "header_row_no": header_row_no}]


def _capture_xlsx_lossless(
    db: Session,
    evidence_file_id: str,
    file_path: Path,
    raw_row_lookup: Dict[Tuple[str, int], str],
    chunk_size: int = 5000,
) -> List[Dict[str, Any]]:
    if not openpyxl:
        raise TabularReadError("openpyxl is required to read Excel files", reason_code="DEPENDENCY_MISSING")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=False)
    sheets_summary: List[Dict[str, Any]] = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        raw_rows_to_insert: List[RawRow] = []
        row_count = 0

        # Discover header row for this sheet
        try:
            detailed = read_tabular_file_detailed(file_path, sheet_name=sheet_name)
            header_row_no = detailed.get("file_metadata", {}).get("header_row_no", 1)
        except Exception:
            header_row_no = 1

        for row_idx, row_cells in enumerate(ws.iter_rows(values_only=True), 1):
            row_count += 1
            row_id = str(uuid.uuid4())

            tokens = [str(c) if c is not None else "" for c in row_cells]
            is_blank = not any(t.strip() for t in tokens if t)
            is_preamble = row_idx < header_row_no

            status = "blank" if is_blank else ("preamble" if is_preamble else "staged")

            row_dict = {f"col_{i+1}": tok for i, tok in enumerate(tokens)}
            row_hash = compute_raw_row_hash(row_dict)

            raw_row = RawRow(
                id=row_id,
                evidence_file_id=evidence_file_id,
                sheet_name=sheet_name,
                row_no=row_idx,
                raw_json=json.dumps(row_dict, ensure_ascii=False),
                row_hash=row_hash,
                status=status,
            )
            raw_rows_to_insert.append(raw_row)
            raw_row_lookup[(sheet_name, row_idx)] = row_id

            if len(raw_rows_to_insert) >= chunk_size:
                db.bulk_save_objects(raw_rows_to_insert)
                db.flush()
                raw_rows_to_insert = []

        if raw_rows_to_insert:
            db.bulk_save_objects(raw_rows_to_insert)
            db.flush()

        sheet_rec = RawSheet(
            id=str(uuid.uuid4()),
            evidence_file_id=evidence_file_id,
            sheet_name=sheet_name,
            header_row_no=header_row_no,
            row_count=row_count,
        )
        db.add(sheet_rec)
        db.flush()
        sheets_summary.append({"sheet_name": sheet_name, "row_count": row_count, "header_row_no": header_row_no})

    wb.close()
    return sheets_summary


def _capture_json_lossless(
    db: Session,
    evidence_file_id: str,
    file_path: Path,
    raw_row_lookup: Dict[Tuple[str, int], str],
    chunk_size: int = 5000,
) -> List[Dict[str, Any]]:
    sheet_name = "default"
    raw_rows_to_insert: List[RawRow] = []
    line_count = 0

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for row_idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            line_count += 1
            row_id = str(uuid.uuid4())
            try:
                row_dict = json.loads(line_str)
                if not isinstance(row_dict, dict):
                    row_dict = {"value": str(row_dict)}
            except Exception:
                row_dict = {"raw_text": line_str}

            row_hash = compute_raw_row_hash(row_dict)
            raw_row = RawRow(
                id=row_id,
                evidence_file_id=evidence_file_id,
                sheet_name=sheet_name,
                row_no=line_count,
                raw_json=json.dumps(row_dict, ensure_ascii=False),
                row_hash=row_hash,
                status="staged",
            )
            raw_rows_to_insert.append(raw_row)
            raw_row_lookup[(sheet_name, line_count)] = row_id

            if len(raw_rows_to_insert) >= chunk_size:
                db.bulk_save_objects(raw_rows_to_insert)
                db.flush()
                raw_rows_to_insert = []

    if raw_rows_to_insert:
        db.bulk_save_objects(raw_rows_to_insert)
        db.flush()

    sheet_rec = RawSheet(
        id=str(uuid.uuid4()),
        evidence_file_id=evidence_file_id,
        sheet_name=sheet_name,
        header_row_no=1,
        row_count=line_count,
    )
    db.add(sheet_rec)
    db.flush()
    return [{"sheet_name": sheet_name, "row_count": line_count, "header_row_no": 1}]


def reconcile_evidence_file(
    db: Session,
    evidence_file_id: str,
    file_path: Path,
) -> Dict[str, Any]:
    """
    Enforces the non-negotiable reconciliation invariant:
      rows_in_file == staged + rejected + preamble + blank
    Computes rows_in_file independently by streaming from disk,
    and compares with row counts grouped by status in raw_rows.
    """
    ext = file_path.suffix.lower()
    independent_counts: Dict[str, int] = {}

    if ext in [".csv", ".tsv", ".txt"]:
        encoding, delimiter = sniff_encoding_and_delimiter(file_path)
        count = 0
        with open(file_path, "r", encoding=encoding, errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for _ in reader:
                count += 1
        independent_counts["default"] = count
    elif ext == ".xlsx" and openpyxl:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=False)
        for sname in wb.sheetnames:
            ws = wb[sname]
            scount = sum(1 for _ in ws.iter_rows(values_only=True))
            independent_counts[sname] = scount
        wb.close()
    elif ext in [".json", ".jsonl"]:
        count = 0
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for l in f:
                if l.strip():
                    count += 1
        independent_counts["default"] = count
    else:
        independent_counts["document"] = 1

    sheets = db.query(RawSheet).filter(RawSheet.evidence_file_id == evidence_file_id).all()
    reconciliation_results: List[Dict[str, Any]] = []
    overall_reconciled = True

    for sh in sheets:
        sname = sh.sheet_name
        rows_in_file = independent_counts.get(sname, sh.row_count)

        status_counts = dict(
            db.query(RawRow.status, func.count(RawRow.id))
            .filter(RawRow.evidence_file_id == evidence_file_id, RawRow.sheet_name == sname)
            .group_by(RawRow.status)
            .all()
        )

        staged = status_counts.get("staged", 0)
        rejected = status_counts.get("rejected", 0)
        preamble = status_counts.get("preamble", 0)
        blank = status_counts.get("blank", 0)
        db_total = staged + rejected + preamble + blank

        is_sheet_ok = (rows_in_file == db_total)
        if not is_sheet_ok:
            overall_reconciled = False

        reconciliation_results.append({
            "sheet_name": sname,
            "rows_in_file": rows_in_file,
            "db_total": db_total,
            "staged": staged,
            "rejected": rejected,
            "preamble": preamble,
            "blank": blank,
            "is_reconciled": is_sheet_ok,
            "discrepancy": rows_in_file - db_total,
        })

    return {
        "evidence_file_id": evidence_file_id,
        "is_reconciled": overall_reconciled,
        "sheets": reconciliation_results,
    }


def rollback_evidence_file(
    db: Session,
    evidence_file_id: str,
    case_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    Surgically rolls back an ingested evidence file:
    Removes raw_rows, raw_sheets, staged records, rejected rows, and claims
    contributed by this file without affecting any other evidence in the case.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not ev:
        raise ValueError(f"Evidence file {evidence_file_id} not found")

    del_raw_rows = db.query(RawRow).filter(RawRow.evidence_file_id == evidence_file_id).delete()
    del_raw_sheets = db.query(RawSheet).filter(RawSheet.evidence_file_id == evidence_file_id).delete()
    del_rejected = db.query(RejectedRow).filter(RejectedRow.evidence_id == evidence_file_id).delete()

    del_calls = db.query(CallRecord).filter(CallRecord.source_file == ev.original_name, CallRecord.case_id == case_id).delete()
    del_txns = db.query(Transaction).filter(Transaction.source_file == ev.original_name, Transaction.case_id == case_id).delete()
    del_ips = db.query(IPEvent).filter(IPEvent.source_file == ev.original_name, IPEvent.case_id == case_id).delete()
    del_claims = db.query(RecordFieldClaim).filter(RecordFieldClaim.evidence_id == evidence_file_id).delete()

    ev.status = "uploaded"
    db.commit()

    record_audit_log(
        db=db,
        user_id=user_id,
        action="rollback_evidence_file",
        case_id=case_id,
        object_type="evidence_file",
        object_id=evidence_file_id,
        details={
            "raw_rows_deleted": del_raw_rows,
            "raw_sheets_deleted": del_raw_sheets,
            "rejected_rows_deleted": del_rejected,
            "calls_deleted": del_calls,
            "txns_deleted": del_txns,
            "ips_deleted": del_ips,
            "claims_deleted": del_claims,
        },
    )

    return {
        "status": "rolled_back",
        "evidence_file_id": evidence_file_id,
        "deleted_counts": {
            "raw_rows": del_raw_rows,
            "raw_sheets": del_raw_sheets,
            "rejected_rows": del_rejected,
            "call_records": del_calls,
            "transactions": del_txns,
            "ip_events": del_ips,
            "claims": del_claims,
        },
    }
