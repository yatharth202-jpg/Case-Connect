import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    get_db, EvidenceFile, Case, ColumnMapping, Job, RejectedRow,
    CallRecord, Transaction, IPEvent, Entity, User
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.services.ingestion.readers import (
    read_tabular_file,
    read_tabular_file_detailed,
    TabularReadError,
)
from backend.app.services.ingestion.detect import detect_file_type, detect_file_sections
from backend.app.services.ingestion.mapping import (
    suggest_column_mappings,
    compute_header_signature,
    compute_column_content_profile,
    get_mapping_template,
    save_mapping_template,
    check_mapping_template_drift,
    REQUIRED_FIELDS,
)
from backend.app.services.ingestion.stage import stage_evidence_file, preview_normalized_rows
from backend.app.audit.service import record_audit_log

router = APIRouter()


class ConfirmMappingRequest(BaseModel):
    file_type: str
    mapping: Dict[str, str]
    statement_account: Optional[str] = None


def run_ingestion_job(job_id: str, evidence_id: str, user_id: str, file_type: str, mapping: dict, stmt_acct: str = None):
    """Background task executing the file staging pipeline with per-chunk progress updates."""
    from backend.app.db.sql import SessionLocal
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    steps_log = ["Parsing file structure and encodings", "Normalizing fields and detecting anomalies"]

    def _on_progress(pct: int, msg: str):
        job.progress = pct
        job.steps_json = json.dumps(steps_log + [msg])
        db.commit()

    try:
        job.status = "running"
        job.progress = 20
        job.steps_json = json.dumps(steps_log)
        db.commit()

        result = stage_evidence_file(
            db=db,
            evidence_id=evidence_id,
            user_id=user_id,
            file_type=file_type,
            column_mapping=mapping,
            statement_account=stmt_acct,
            progress_callback=_on_progress,
        )

        if result.get("needs_owner_confirmation"):
            job.status = "needs_owner_confirmation"
            job.progress = 100
            job.steps_json = json.dumps(steps_log + [
                "Statement account owner not found in header; waiting for officer confirmation"
            ])
        else:
            job.status = "done"
            job.progress = 100
            job.steps_json = json.dumps(steps_log + [
                f"Ingested {result['rows_ingested']} rows ({result['rows_rejected']} rejected, {result['duplicates_skipped']} duplicates skipped)"
            ])
        db.commit()

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()


@router.get("/evidence/{evidence_id}/preview")
def preview_evidence_mapping(
    evidence_id: str,
    sheet_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes uploaded evidence file:
    Sniffs data, detects candidate file type (including multi-sheet/mixed-section breakdown),
    computes content-based column mappings (top-3 candidates per column), checks template drift,
    and returns first 20 raw and normalized preview rows.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    file_path = Path(ev.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File missing on disk")

    try:
        detailed = read_tabular_file_detailed(file_path, sheet_name=sheet_name)
    except TabularReadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": exc.message, "reason_code": exc.reason_code},
        )

    records = detailed["records"]
    headers = detailed["headers"]
    banners = detailed["banner_rows"]
    file_meta = detailed["file_metadata"]

    detection = detect_file_type(headers, records, filename=ev.original_name, banners=banners)
    best_type = detection["detected_type"]
    sections_info = detect_file_sections(file_meta, headers, records, filename=ev.original_name, banners=banners)

    sig = compute_header_signature(headers)
    saved_tpl = get_mapping_template(db, sig)
    drift = check_mapping_template_drift(db, best_type, headers, records)

    computed_suggestions = suggest_column_mappings(
        best_type if best_type != "unknown" else "cdr",
        headers,
        records,
    )

    if saved_tpl and not drift["has_drift"]:
        suggested = {}
        for h in headers:
            comp = computed_suggestions.get(h, {})
            tpl_canon = saved_tpl.get(h, "ignore")
            suggested[h] = {
                "canonical": tpl_canon,
                "confidence": 1.0,
                "reasons": ["Matched saved mapping template with zero drift"],
                "candidates": comp.get("candidates", [{"canonical": tpl_canon, "confidence": 1.0, "reasons": ["Saved template"]}]),
                "content_profile": comp.get("content_profile", {}),
            }
    else:
        suggested = computed_suggestions

    flat_mapping = {h: v["canonical"] for h, v in suggested.items()}
    owner_meta = file_meta.get("statement_owner", {})
    stmt_acct = owner_meta.get("account_number")
    needs_owner_conf = bool(best_type == "bank_statement" and owner_meta.get("needs_owner_confirmation"))

    if needs_owner_conf and ev.status == "uploaded":
        ev.status = "needs_owner_confirmation"
        ev.detected_type = "bank_statement"
        db.commit()

    normalized_preview = preview_normalized_rows(
        best_type if best_type != "unknown" else "cdr",
        records,
        flat_mapping,
        statement_account=stmt_acct,
        limit=20,
    )

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "header_signature": sig,
        "detected_type": best_type,
        "confidence": detection["confidence"],
        "detection_reasons": detection.get("reasons", []),
        "alternatives": detection["alternatives"],
        "banner_rows": banners,
        "headers": headers,
        "suggested_mapping": suggested,
        "template_drift": drift,
        "requires_confirmation": bool(drift["requires_confirmation"] or needs_owner_conf),
        "needs_owner_confirmation": needs_owner_conf,
        "file_metadata": {
            "encoding": file_meta.get("encoding"),
            "delimiter": file_meta.get("delimiter"),
            "opening_balance_paise": file_meta.get("opening_balance_paise"),
            "closing_balance_paise": file_meta.get("closing_balance_paise"),
            "total_rows_dropped": file_meta.get("total_rows_dropped", 0),
            "repeated_headers_dropped": file_meta.get("repeated_headers_dropped", 0),
            "statement_owner": owner_meta,
            "multi_sheet": file_meta.get("multi_sheet", False),
            "sheets": [
                {
                    "sheet_name": s["sheet_name"],
                    "headers": s["headers"],
                    "row_count": s["row_count"],
                }
                for s in file_meta.get("sheets", [])
            ],
            "sections": sections_info,
        },
        "preview_rows": records[:20],
        "normalized_preview_rows": normalized_preview,
        "total_rows": len(records),
        "required_fields": REQUIRED_FIELDS.get(best_type, [])
    }


@router.post("/evidence/{evidence_id}/mapping")
def confirm_column_mapping(
    evidence_id: str,
    req: ConfirmMappingRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Confirms column mapping for an evidence file and saves template (with column content profiles)
    for future files with identical headers.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    mapping_entry = ColumnMapping(
        evidence_id=ev.id,
        mapping_json=json.dumps({
            "file_type": req.file_type,
            "mapping": req.mapping,
            "statement_account": req.statement_account
        }),
        confirmed_by=current_user.id
    )
    db.add(mapping_entry)

    detailed = read_tabular_file_detailed(Path(ev.stored_path))
    records = detailed["records"]
    headers = detailed["headers"]
    file_meta = detailed["file_metadata"]
    sig = compute_header_signature(headers)

    col_profiles = {
        h: compute_column_content_profile([r.get(h) for r in records[:100]])
        for h in headers
    }
    save_mapping_template(
        db,
        sig,
        req.file_type,
        req.mapping,
        headers=headers,
        column_profiles=col_profiles,
    )

    owner_acct = req.statement_account or file_meta.get("statement_owner", {}).get("account_number")
    if req.file_type == "bank_statement" and not owner_acct:
        ev.status = "needs_owner_confirmation"
    else:
        ev.status = "mapped"
    ev.detected_type = req.file_type
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="confirm_mapping",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={
            "file_type": req.file_type,
            "mapped_columns": len(req.mapping),
            "statement_account_confirmed": bool(owner_acct),
        }
    )

    return {
        "status": ev.status,
        "evidence_id": ev.id,
        "file_type": req.file_type,
        "needs_owner_confirmation": ev.status == "needs_owner_confirmation",
    }


@router.post("/evidence/{evidence_id}/ingest")
def start_ingestion_job(
    evidence_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Queues a background ingestion job to clean, normalize, deduplicate, and stage records.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    case = get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    mapping_rec = db.query(ColumnMapping).filter(ColumnMapping.evidence_id == ev.id).order_by(ColumnMapping.confirmed_at.desc()).first()
    if mapping_rec:
        m_data = json.loads(mapping_rec.mapping_json)
        file_type = m_data.get("file_type", ev.detected_type or "cdr")
        mapping = m_data.get("mapping", {})
        stmt_acct = m_data.get("statement_account")
    else:
        detailed = read_tabular_file_detailed(Path(ev.stored_path))
        records = detailed["records"]
        headers = detailed["headers"]
        banners = detailed["banner_rows"]
        det = detect_file_type(headers, records, filename=ev.original_name, banners=banners)
        file_type = det["detected_type"] if det["detected_type"] != "unknown" else "cdr"

        drift = check_mapping_template_drift(db, file_type, headers, records)
        if drift["template_found"] and drift["has_drift"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Saved mapping template has schema/type drift; explicit mapping confirmation required.",
                    "reason_code": "MAPPING_TEMPLATE_DRIFT_REQUIRES_CONFIRMATION",
                    "template_drift": drift,
                },
            )

        suggested = suggest_column_mappings(file_type, headers, records)
        mapping = {h: v["canonical"] for h, v in suggested.items()}
        stmt_acct = detailed["file_metadata"].get("statement_owner", {}).get("account_number")

    job = Job(
        case_id=case.id,
        job_type="ingest",
        status="queued",
        progress=0,
        steps_json=json.dumps(["Queued for ingestion worker"])
    )
    db.add(job)
    ev.status = "ingesting"
    db.commit()
    db.refresh(job)

    background_tasks.add_task(
        run_ingestion_job,
        job.id,
        ev.id,
        current_user.id,
        file_type,
        mapping,
        stmt_acct
    )

    return {"job_id": job.id, "status": "queued", "case_id": case.id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll background ingestion job progress."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    steps = []
    try:
        steps = json.loads(job.steps_json)
    except Exception:
        pass

    return {
        "job_id": job.id,
        "case_id": job.case_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "steps": steps,
        "error_message": job.error_message
    }


@router.get("/evidence/{evidence_id}/rejected-rows")
def get_rejected_rows(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Inspect rejected rows and anomaly reasons for an evidence file."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    rejections = db.query(RejectedRow).filter(RejectedRow.evidence_id == ev.id).all()
    return [
        {
            "row_number": r.row_number,
            "reason": r.reason,
            "raw_data": json.loads(r.raw_data_json)
        }
        for r in rejections
    ]


@router.get("/evidence/{evidence_id}/quality")
def get_data_quality_summary(evidence_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve data quality summary metrics."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    calls_count = db.query(CallRecord).filter(CallRecord.source_file == ev.original_name).count()
    txns_count = db.query(Transaction).filter(Transaction.source_file == ev.original_name).count()
    ips_count = db.query(IPEvent).filter(IPEvent.source_file == ev.original_name).count()
    entities_count = db.query(Entity).filter(Entity.source_file == ev.original_name).count()
    staged_total = calls_count + txns_count + ips_count + entities_count

    rejected_count = db.query(RejectedRow).filter(RejectedRow.evidence_id == ev.id).count()

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "status": ev.status,
        "file_type": ev.detected_type,
        "staged_rows": staged_total,
        "rejected_rows": rejected_count
    }
