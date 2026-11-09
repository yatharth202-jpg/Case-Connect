import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import openpyxl
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.db.sql import (
    get_db,
    SessionLocal,
    User,
    Case,
    EvidenceFile,
    Job,
    ExtractionRecord,
    RecordSource,
    FieldClaim,
    GoldenField,
    MergeConflict,
    IngestRun,
    Annotation,
    Entity,
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.services.merge.engine import (
    apply_evidence_merge,
    rollback_evidence_merge,
    resolve_conflict_by_officer,
    extract_merge_payload_from_evidence,
    MergeConcurrencyError,
)
from backend.app.services.merge.resolve import get_source_trust_rank
from backend.app.audit.service import record_audit_log

router = APIRouter()


class MergeApplyPayload(BaseModel):
    record_type: Optional[str] = None
    records: Optional[List[Dict[str, Any]]] = None
    source_kind: Optional[str] = None
    method: Optional[str] = "structured"
    default_confidence: float = 1.0


class ConflictResolveRequest(BaseModel):
    claim_id: str
    note: Optional[str] = None


class AnnotationCreateRequest(BaseModel):
    subject_type: str = Field(..., description="'record' or 'entity'")
    subject_id: str
    note_text: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


def _run_merge_apply_job(
    job_id: str,
    case_id: str,
    evidence_id: str,
    user_id: str,
    payload_override: Optional[Dict[str, Any]] = None,
):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        job.status = "running"
        job.progress = 20
        job.steps_json = json.dumps(["Extracting normalized records and dynamic fields", "Resolving claims and updating golden store"])
        db.commit()

        ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id, EvidenceFile.case_id == case_id).first()
        src_name = ev.original_name if ev else evidence_id

        if payload_override and payload_override.get("records") is not None:
            record_type = payload_override.get("record_type") or "transaction"
            records = payload_override["records"]
            source_kind = payload_override.get("source_kind") or "structured_file"
            method = payload_override.get("method") or "structured"
            conf = float(payload_override.get("default_confidence", 1.0))
        else:
            if not ev:
                raise ValueError(f"Evidence file {evidence_id} not found in case {case_id}")
            record_type, records, source_kind = extract_merge_payload_from_evidence(db, ev)
            method = ev.detected_type or "structured"
            conf = 1.0

        res = apply_evidence_merge(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            record_type=record_type,
            records=records,
            user_id=user_id,
            source_kind=source_kind,
            method=method,
            default_confidence=conf,
            job_id=job_id,
            preview=False,
            source_file_name=src_name,
        )

        if ev:
            ev.status = "ingested"
        job.status = "done"
        job.progress = 100
        job.steps_json = json.dumps([
            "Extracted normalized records and dynamic fields",
            "Resolved claims and updated golden store",
            f"Merge complete: {json.dumps(res['counts'])}",
        ])
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
    finally:
        db.close()


def _run_merge_rollback_job(
    job_id: str,
    case_id: str,
    evidence_id: str,
    user_id: str,
):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        job.status = "running"
        job.progress = 30
        job.steps_json = json.dumps(["Retracting evidence claims and recomputing golden values"])
        db.commit()

        res = rollback_evidence_merge(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            user_id=user_id,
            job_id=job_id,
        )

        job.status = "done"
        job.progress = 100
        job.steps_json = json.dumps([
            "Retracted evidence claims and recomputed golden values",
            f"Rollback complete: {json.dumps(res['counts'])}",
        ])
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        db.commit()
    finally:
        db.close()


# -------------------------------------------------------------------------
# 1. MERGE PREVIEW, APPLY & ROLLBACK
# -------------------------------------------------------------------------
@router.post("/cases/{case_id}/evidence/{evidence_id}/merge/preview")
def preview_evidence_merge_endpoint(
    case_id: str,
    evidence_id: str,
    payload: Optional[MergeApplyPayload] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Runs the deterministic merge engine in rollback-only preview mode (no DB writes).
    Returns counts (new, same, updated, new_fields, conflicts, rejected) and sample of changes.
    """
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id, EvidenceFile.case_id == case_id).first()
    if payload and payload.records is not None:
        record_type = payload.record_type or "transaction"
        records = payload.records
        source_kind = payload.source_kind or "structured_file"
        method = payload.method or "structured"
        conf = payload.default_confidence
        src_name = ev.original_name if ev else evidence_id
    else:
        if not ev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found in case")
        record_type, records, source_kind = extract_merge_payload_from_evidence(db, ev)
        method = ev.detected_type or "structured"
        conf = 1.0
        src_name = ev.original_name

    try:
        res = apply_evidence_merge(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            record_type=record_type,
            records=records,
            user_id=current_user.id,
            source_kind=source_kind,
            method=method,
            default_confidence=conf,
            preview=True,
            source_file_name=src_name,
        )
        return res
    except MergeConcurrencyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(exc), "reason_code": exc.reason_code},
        )


@router.post("/cases/{case_id}/evidence/{evidence_id}/merge/apply")
def apply_evidence_merge_endpoint(
    case_id: str,
    evidence_id: str,
    background_tasks: BackgroundTasks,
    payload: Optional[MergeApplyPayload] = None,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """
    Creates a background merge job and returns job_id immediately.
    On completion: SQLite write -> rebuild_graph(case_id) -> audit_log.
    """
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id, EvidenceFile.case_id == case_id).first()
    if not ev and (not payload or payload.records is None):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found in case")

    job = Job(
        case_id=case_id,
        job_type="merge_apply",
        status="queued",
        progress=0,
        steps_json=json.dumps(["Queued merge apply job"]),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    override_dict = payload.model_dump() if payload and payload.records is not None else None
    background_tasks.add_task(
        _run_merge_apply_job,
        job.id,
        case_id,
        evidence_id,
        current_user.id,
        override_dict,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "case_id": case_id,
        "evidence_id": evidence_id,
    }


@router.post("/cases/{case_id}/evidence/{evidence_id}/rollback")
def rollback_evidence_merge_endpoint(
    case_id: str,
    evidence_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """
    Creates a background rollback job for an evidence file and returns job_id immediately.
    On completion: SQLite soft-retraction + golden recompute -> rebuild_graph(case_id) -> audit_log.
    """
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    job = Job(
        case_id=case_id,
        job_type="merge_rollback",
        status="queued",
        progress=0,
        steps_json=json.dumps(["Queued merge rollback job"]),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        _run_merge_rollback_job,
        job.id,
        case_id,
        evidence_id,
        current_user.id,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "case_id": case_id,
        "evidence_id": evidence_id,
    }


# -------------------------------------------------------------------------
# 2. UNIFIED RECORDS SEARCH & PAGINATION
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/records")
def list_case_extraction_records(
    case_id: str,
    type: Optional[str] = Query(None, description="Filter by record_type (transaction, call, ip_event, entity)"),
    status_filter: Optional[str] = Query("active", alias="status", description="active | retracted | merged | all"),
    q: Optional[str] = Query(None, description="Full-text search across data_json and extra_json"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paginated listing and parameterized search over unified extraction_records."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    query = db.query(ExtractionRecord).filter(ExtractionRecord.case_id == case_id)
    if type:
        query = query.filter(ExtractionRecord.record_type == type)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(ExtractionRecord.status == status_filter)
    if q and q.strip():
        like_pat = f"%{q.strip()}%"
        query = query.filter(
            or_(
                ExtractionRecord.data_json.ilike(like_pat),
                ExtractionRecord.extra_json.ilike(like_pat),
                ExtractionRecord.raw_json.ilike(like_pat),
            )
        )

    total = query.count()
    rows = (
        query.order_by(ExtractionRecord.created_at.desc(), ExtractionRecord.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in rows:
        sources = (
            db.query(RecordSource)
            .filter(RecordSource.record_id == r.id)
            .all()
        )
        items.append({
            "id": r.id,
            "case_id": r.case_id,
            "evidence_id": r.evidence_id,
            "record_type": r.record_type,
            "natural_key": r.natural_key,
            "occurrence_idx": r.occurrence_idx,
            "data": json.loads(r.data_json or "{}"),
            "extra": json.loads(r.extra_json or "{}"),
            "raw": json.loads(r.raw_json or "{}"),
            "source_ref": r.source_ref,
            "page_no": r.page_no,
            "method": r.method,
            "source_kind": r.source_kind,
            "confidence": r.confidence,
            "extractor_version": r.extractor_version,
            "status": r.status,
            "sources": [{"evidence_id": s.evidence_id, "source_ref": s.source_ref} for s in sources],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "case_id": case_id,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# -------------------------------------------------------------------------
# 3. CONFLICTS QUEUE & OFFICER RESOLUTION
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/conflicts")
def list_case_merge_conflicts(
    case_id: str,
    status_filter: Optional[str] = Query("open", alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists merge conflicts for a case with candidate claims and trust/confidence metadata."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    query = db.query(MergeConflict).filter(MergeConflict.case_id == case_id)
    if status_filter and status_filter.lower() != "all":
        query = query.filter(MergeConflict.status == status_filter)

    conflicts = query.order_by(MergeConflict.created_at.desc()).all()
    out = []
    for c in conflicts:
        c_ids = json.loads(c.claim_ids_json or "[]")
        claims = (
            db.query(FieldClaim)
            .filter(
                FieldClaim.subject_type == c.subject_type,
                FieldClaim.subject_id == c.subject_id,
                FieldClaim.field_name == c.field_name,
            )
            .all()
        )
        golden = (
            db.query(GoldenField)
            .filter(
                GoldenField.subject_type == c.subject_type,
                GoldenField.subject_id == c.subject_id,
                GoldenField.field_name == c.field_name,
            )
            .first()
        )
        out.append({
            "id": c.id,
            "case_id": c.case_id,
            "subject_type": c.subject_type,
            "subject_id": c.subject_id,
            "field_name": c.field_name,
            "status": c.status,
            "reason_code": c.reason_code,
            "resolution_claim_id": c.resolution_claim_id,
            "resolved_by": c.resolved_by,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
            "competing_claim_ids": c_ids,
            "golden_selected_claim_id": golden.selected_claim_id if golden else None,
            "locked": golden.locked if golden else False,
            "candidates": [
                {
                    "claim_id": cl.id,
                    "value_norm": cl.value_norm,
                    "value_raw": cl.value_raw,
                    "evidence_id": cl.evidence_id,
                    "source_ref": cl.source_ref,
                    "source_kind": cl.source_kind,
                    "trust_rank": get_source_trust_rank(cl.source_kind),
                    "method": cl.method,
                    "confidence": cl.confidence,
                    "validator_ok": cl.validator_ok,
                    "status": cl.status,
                    "observed_at": cl.observed_at.isoformat() if cl.observed_at else None,
                }
                for cl in claims
            ],
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return out


@router.post("/conflicts/{conflict_id}/resolve")
@router.post("/cases/{case_id}/conflicts/{conflict_id}/resolve")
def resolve_conflict_endpoint(
    conflict_id: str,
    req: ConflictResolveRequest,
    case_id: Optional[str] = None,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Officer resolves a merge conflict and locks the chosen golden field."""
    conflict = db.query(MergeConflict).filter(MergeConflict.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merge conflict not found")

    if case_id and conflict.case_id != case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict does not belong to this case")

    # Enforce BOLA case membership
    get_case_for_user(case_id=conflict.case_id, current_user=current_user, db=db)

    try:
        return resolve_conflict_by_officer(
            db=db,
            conflict_id=conflict.id,
            selected_claim_id=req.claim_id,
            officer_id=current_user.id,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# -------------------------------------------------------------------------
# 4. RECORD & ENTITY CLAIM HISTORY
# -------------------------------------------------------------------------
def _build_subject_claim_history(db: Session, case_id: str, subject_id: str) -> Dict[str, Any]:
    ext_rec = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.id == subject_id)
        .first()
    )
    if not ext_rec:
        # Also allow lookup by staged_id (e.g. Entity.id)
        ext_rec = (
            db.query(ExtractionRecord)
            .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.staged_id == subject_id)
            .first()
        )
    if not ext_rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record or entity not found in case")

    claims = (
        db.query(FieldClaim)
        .filter(FieldClaim.case_id == case_id, FieldClaim.subject_id == ext_rec.id)
        .order_by(FieldClaim.observed_at.asc(), FieldClaim.id.asc())
        .all()
    )
    goldens = (
        db.query(GoldenField)
        .filter(GoldenField.subject_id == ext_rec.id)
        .all()
    )
    golden_by_field = {g.field_name: g for g in goldens}
    sources = db.query(RecordSource).filter(RecordSource.record_id == ext_rec.id).all()

    fields_history: Dict[str, Any] = {}
    all_claims_out: List[Dict[str, Any]] = []

    for cl in claims:
        g = golden_by_field.get(cl.field_name)
        is_sel = bool(g and g.selected_claim_id == cl.id)
        c_item = {
            "claim_id": cl.id,
            "field_name": cl.field_name,
            "value_norm": cl.value_norm,
            "value_raw": cl.value_raw,
            "evidence_id": cl.evidence_id,
            "source_ref": cl.source_ref,
            "source_kind": cl.source_kind,
            "trust_rank": get_source_trust_rank(cl.source_kind),
            "method": cl.method,
            "confidence": cl.confidence,
            "validator_ok": cl.validator_ok,
            "status": cl.status,
            "is_selected": is_sel,
            "selected_by": g.selected_by if is_sel else None,
            "locked": g.locked if is_sel else False,
            "reason_code": g.reason_code if is_sel else None,
            "observed_at": cl.observed_at.isoformat() if cl.observed_at else None,
            "run_id": cl.run_id,
        }
        all_claims_out.append(c_item)
        f_entry = fields_history.setdefault(cl.field_name, {
            "field_name": cl.field_name,
            "selected_claim_id": g.selected_claim_id if g else None,
            "selected_by": g.selected_by if g else "auto",
            "locked": g.locked if g else False,
            "reason_code": g.reason_code if g else None,
            "claims": [],
        })
        f_entry["claims"].append(c_item)

    return {
        "case_id": case_id,
        "record_id": ext_rec.id,
        "staged_id": ext_rec.staged_id,
        "record_type": ext_rec.record_type,
        "status": ext_rec.status,
        "extractor_version": ext_rec.extractor_version,
        "sources": [
            {
                "evidence_id": s.evidence_id,
                "source_ref": s.source_ref,
                "seen_at": s.seen_at.isoformat() if s.seen_at else None,
            }
            for s in sources
        ],
        "fields": fields_history,
        "claims": all_claims_out,
    }


@router.get("/cases/{case_id}/records/{record_id}/history")
def get_record_claim_history(
    case_id: str,
    record_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)
    return _build_subject_claim_history(db, case_id, record_id)


@router.get("/cases/{case_id}/entities/{entity_id}/history")
def get_entity_claim_history(
    case_id: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)
    return _build_subject_claim_history(db, case_id, entity_id)


# -------------------------------------------------------------------------
# 5. CONSOLIDATED MASTER SHEET EXPORT (JSON, CSV, XLSX + SHA-256 + AUDIT)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/master-sheet")
def export_case_master_sheet(
    case_id: str,
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
    view: str = Query("wide", pattern="^(wide|per_type)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Consolidates all active ExtractionRecords in the case into a Master Sheet:
    - WIDE view: one row per entity/record, one column per field (union of known columns + dynamic extra_json keys),
      cell = golden value.
    - per_type view: grouped by record_type with per-type column unions.
    - Formats: json | csv | xlsx.
    Every export computes a SHA-256 of the exported bytes, sets X-Export-SHA256 header, and logs EXPORT to audit_log.
    """
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    active_records = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.status == "active")
        .order_by(ExtractionRecord.record_type.asc(), ExtractionRecord.created_at.asc(), ExtractionRecord.id.asc())
        .all()
    )

    meta_cols = ["record_id", "record_type", "evidence_id", "source_ref", "confidence", "extractor_version"]
    known_cols_ordered: List[str] = []
    extra_cols_ordered: List[str] = []
    known_seen = set()
    extra_seen = set()

    wide_rows_raw: List[Dict[str, Any]] = []
    by_type_rows: Dict[str, List[Dict[str, Any]]] = {}
    by_type_cols: Dict[str, List[str]] = {}
    records_detail: List[Dict[str, Any]] = []

    for r in active_records:
        d_map = json.loads(r.data_json or "{}")
        e_map = json.loads(r.extra_json or "{}")

        for k in d_map:
            if k not in known_seen:
                known_seen.add(k)
                known_cols_ordered.append(k)
        for k in e_map:
            if k not in extra_seen and k not in known_seen:
                extra_seen.add(k)
                extra_cols_ordered.append(k)

        t_cols = by_type_cols.setdefault(r.record_type, list(meta_cols))
        for k in list(d_map.keys()) + list(e_map.keys()):
            if k not in t_cols:
                t_cols.append(k)

        row_combined = {
            "record_id": r.id,
            "record_type": r.record_type,
            "evidence_id": r.evidence_id,
            "source_ref": r.source_ref,
            "confidence": r.confidence,
            "extractor_version": r.extractor_version,
            **d_map,
            **e_map,
        }
        wide_rows_raw.append(row_combined)
        by_type_rows.setdefault(r.record_type, []).append(row_combined)

        if format == "json":
            claims = (
                db.query(FieldClaim)
                .filter(FieldClaim.subject_id == r.id)
                .order_by(FieldClaim.observed_at.asc())
                .all()
            )
            sources = db.query(RecordSource).filter(RecordSource.record_id == r.id).all()
            records_detail.append({
                "record_id": r.id,
                "record_type": r.record_type,
                "natural_key": r.natural_key,
                "occurrence_idx": r.occurrence_idx,
                "data": d_map,
                "extra": e_map,
                "confidence": r.confidence,
                "extractor_version": r.extractor_version,
                "sources": [{"evidence_id": s.evidence_id, "source_ref": s.source_ref} for s in sources],
                "claims": [
                    {
                        "claim_id": cl.id,
                        "field_name": cl.field_name,
                        "value_norm": cl.value_norm,
                        "value_raw": cl.value_raw,
                        "evidence_id": cl.evidence_id,
                        "source_kind": cl.source_kind,
                        "method": cl.method,
                        "confidence": cl.confidence,
                        "validator_ok": cl.validator_ok,
                        "status": cl.status,
                    }
                    for cl in claims
                ],
            })

    all_wide_columns = meta_cols + known_cols_ordered + extra_cols_ordered
    normalized_wide_rows = [
        {col: r.get(col) for col in all_wide_columns}
        for r in wide_rows_raw
    ]

    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=all_wide_columns)
        writer.writeheader()
        for r in normalized_wide_rows:
            writer.writerow({k: ("" if v is None else v) for k, v in r.items()})
        csv_bytes = buf.getvalue().encode("utf-8")
        sha256_hex = hashlib.sha256(csv_bytes).hexdigest()

        record_audit_log(
            db=db,
            user_id=current_user.id,
            action="EXPORT",
            case_id=case_id,
            object_type="master_sheet",
            object_id=case_id,
            details={"format": "csv", "view": view, "rows": len(normalized_wide_rows), "sha256": sha256_hex},
        )
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "X-Export-SHA256": sha256_hex,
                "Content-Disposition": f'attachment; filename="master_sheet_{case_id}.csv"',
            },
        )

    elif format == "xlsx":
        wb = openpyxl.Workbook()
        if view == "per_type" and by_type_rows:
            first_sheet = True
            for rtype, r_list in by_type_rows.items():
                ws = wb.active if first_sheet else wb.create_sheet(title=rtype[:31])
                ws.title = rtype[:31]
                first_sheet = False
                cols = by_type_cols.get(rtype, all_wide_columns)
                ws.append(cols)
                for r in r_list:
                    ws.append([r.get(c) for c in cols])
        else:
            ws = wb.active
            ws.title = "Master_Sheet_Wide"
            ws.append(all_wide_columns)
            for r in normalized_wide_rows:
                ws.append([r.get(c) for c in all_wide_columns])

        x_buf = io.BytesIO()
        wb.save(x_buf)
        xlsx_bytes = x_buf.getvalue()
        sha256_hex = hashlib.sha256(xlsx_bytes).hexdigest()

        record_audit_log(
            db=db,
            user_id=current_user.id,
            action="EXPORT",
            case_id=case_id,
            object_type="master_sheet",
            object_id=case_id,
            details={"format": "xlsx", "view": view, "rows": len(normalized_wide_rows), "sha256": sha256_hex},
        )
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "X-Export-SHA256": sha256_hex,
                "Content-Disposition": f'attachment; filename="master_sheet_{case_id}.xlsx"',
            },
        )

    # Default format == "json"
    body_payload = {
        "case_id": case_id,
        "format": "json",
        "view": view,
        "total_records": len(normalized_wide_rows),
        "columns": all_wide_columns,
        "known_columns": known_cols_ordered,
        "extra_columns": extra_cols_ordered,
        "rows": normalized_wide_rows,
        "by_type": {
            rt: {
                "columns": by_type_cols.get(rt, []),
                "rows": [{c: row.get(c) for c in by_type_cols.get(rt, [])} for row in rows_list],
            }
            for rt, rows_list in by_type_rows.items()
        },
        "records_detail": records_detail,
    }
    canonical_bytes = json.dumps(body_payload, sort_keys=True, default=str).encode("utf-8")
    sha256_hex = hashlib.sha256(canonical_bytes).hexdigest()
    body_payload["sha256"] = sha256_hex
    final_json_bytes = json.dumps(body_payload, default=str).encode("utf-8")
    exact_sha256 = hashlib.sha256(final_json_bytes).hexdigest()
    # Store sha256 of the payload and also return X-Export-SHA256 matching the exact response bytes
    body_payload["sha256"] = exact_sha256
    final_bytes = json.dumps(body_payload, default=str).encode("utf-8")
    bytes_sha256 = hashlib.sha256(final_bytes).hexdigest()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="EXPORT",
        case_id=case_id,
        object_type="master_sheet",
        object_id=case_id,
        details={"format": "json", "view": view, "rows": len(normalized_wide_rows), "sha256": bytes_sha256},
    )
    return Response(
        content=final_bytes,
        media_type="application/json",
        headers={"X-Export-SHA256": bytes_sha256},
    )


# -------------------------------------------------------------------------
# 6. INGEST RUNS CHANGELOG
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/ingest-runs")
def list_case_ingest_runs(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns chronological changelog of ingest runs (new/same/updated/new_fields/conflicts/rejected)."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    runs = (
        db.query(IngestRun)
        .filter(IngestRun.case_id == case_id)
        .order_by(IngestRun.started_at.desc(), IngestRun.id.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "evidence_id": r.evidence_id,
            "job_id": r.job_id,
            "mode": r.mode,
            "counts": json.loads(r.counts_json or "{}"),
            "status": r.status,
            "extractor_version": r.extractor_version,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]


# -------------------------------------------------------------------------
# 7. OFFICER ANNOTATIONS & TAGS (APPEND-ONLY WITH SOFT DELETE)
# -------------------------------------------------------------------------
@router.post("/cases/{case_id}/annotations")
def create_case_annotation(
    case_id: str,
    req: AnnotationCreateRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Creates an append-only officer note/tag annotation on a record or entity."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    if req.subject_type not in ("record", "entity"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subject_type must be 'record' or 'entity'")

    ann = Annotation(
        case_id=case_id,
        subject_type=req.subject_type,
        subject_id=req.subject_id,
        note_text=req.note_text,
        tags_json=json.dumps(req.tags),
        created_by=current_user.id,
        is_deleted=False,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="create_annotation",
        case_id=case_id,
        object_type=req.subject_type,
        object_id=req.subject_id,
        details={"annotation_id": ann.id, "tags": req.tags},
    )

    return {
        "id": ann.id,
        "case_id": ann.case_id,
        "subject_type": ann.subject_type,
        "subject_id": ann.subject_id,
        "note_text": ann.note_text,
        "tags": json.loads(ann.tags_json or "[]"),
        "created_by": ann.created_by,
        "created_at": ann.created_at.isoformat() if ann.created_at else None,
        "is_deleted": ann.is_deleted,
    }


@router.get("/cases/{case_id}/annotations")
def list_case_annotations(
    case_id: str,
    subject_id: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists active officer annotations/tags for a case (or specific record/entity)."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    query = db.query(Annotation).filter(Annotation.case_id == case_id)
    if subject_id:
        query = query.filter(Annotation.subject_id == subject_id)
    if not include_deleted:
        query = query.filter(Annotation.is_deleted.is_(False))

    rows = query.order_by(Annotation.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "case_id": a.case_id,
            "subject_type": a.subject_type,
            "subject_id": a.subject_id,
            "note_text": a.note_text,
            "tags": json.loads(a.tags_json or "[]"),
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "is_deleted": a.is_deleted,
        }
        for a in rows
    ]


@router.delete("/cases/{case_id}/annotations/{annotation_id}")
def soft_delete_case_annotation(
    case_id: str,
    annotation_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Soft-deletes an annotation (never physically deletes the row)."""
    get_case_for_user(case_id=case_id, current_user=current_user, db=db)

    ann = (
        db.query(Annotation)
        .filter(Annotation.id == annotation_id, Annotation.case_id == case_id)
        .first()
    )
    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")

    ann.is_deleted = True
    ann.deleted_by = current_user.id
    ann.deleted_at = datetime.now(timezone.utc)
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="soft_delete_annotation",
        case_id=case_id,
        object_type="annotation",
        object_id=ann.id,
        details={"subject_id": ann.subject_id},
    )

    return {"id": ann.id, "status": "soft_deleted", "is_deleted": True}

