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
from backend.app.services.ingestion.readers import read_tabular_file
from backend.app.services.ingestion.detect import detect_file_type
from backend.app.services.ingestion.mapping import (
    suggest_column_mappings, compute_header_signature,
    get_mapping_template, save_mapping_template, REQUIRED_FIELDS
)
from backend.app.services.ingestion.stage import stage_evidence_file
from backend.app.audit.service import record_audit_log

router = APIRouter()

class ConfirmMappingRequest(BaseModel):
    file_type: str
    mapping: Dict[str, str]
    statement_account: Optional[str] = None

def run_ingestion_job(job_id: str, evidence_id: str, user_id: str, file_type: str, mapping: dict, stmt_acct: str = None):
    """Background task executing the file staging pipeline."""
    from backend.app.db.sql import SessionLocal
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        db.close()
        return

    try:
        job.status = "running"
        job.progress = 20
        job.steps_json = json.dumps(["Parsing file structure and encodings", "Normalizing fields and detecting anomalies"])
        db.commit()

        # Run staging
        result = stage_evidence_file(
            db=db,
            evidence_id=evidence_id,
            user_id=user_id,
            file_type=file_type,
            column_mapping=mapping,
            statement_account=stmt_acct
        )

        job.status = "done"
        job.progress = 100
        job.steps_json = json.dumps([
            "Parsed file structure and encodings",
            "Normalized fields and detected anomalies",
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes uploaded evidence file:
    Sniffs data, detects candidate file type, suggests column mappings,
    and returns first 20 raw preview rows.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    file_path = Path(ev.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File missing on disk")

    records, headers, banners = read_tabular_file(file_path)
    detection = detect_file_type(headers, records, filename=ev.original_name)
    best_type = detection["detected_type"]

    sig = compute_header_signature(headers)
    saved_tpl = get_mapping_template(db, sig)

    if saved_tpl:
        suggested = {h: {"canonical": saved_tpl.get(h, "ignore"), "confidence": 1.0} for h in headers}
    else:
        suggested = suggest_column_mappings(best_type if best_type != "unknown" else "cdr", headers)

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "header_signature": sig,
        "detected_type": best_type,
        "confidence": detection["confidence"],
        "alternatives": detection["alternatives"],
        "banner_rows": banners,
        "headers": headers,
        "suggested_mapping": suggested,
        "preview_rows": records[:20],
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
    Confirms column mapping for an evidence file and saves template for future files with identical headers.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    # Save mapping in column_mappings
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

    # Save reusable template
    records, headers, _ = read_tabular_file(Path(ev.stored_path))
    sig = compute_header_signature(headers)
    save_mapping_template(db, sig, req.file_type, req.mapping)

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
        details={"file_type": req.file_type, "mapped_columns": len(req.mapping)}
    )

    return {"status": "confirmed", "evidence_id": ev.id, "file_type": req.file_type}

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

    # Retrieve confirmed mapping or default
    mapping_rec = db.query(ColumnMapping).filter(ColumnMapping.evidence_id == ev.id).order_by(ColumnMapping.confirmed_at.desc()).first()
    if mapping_rec:
        m_data = json.loads(mapping_rec.mapping_json)
        file_type = m_data.get("file_type", ev.detected_type or "cdr")
        mapping = m_data.get("mapping", {})
        stmt_acct = m_data.get("statement_account")
    else:
        # Default auto-mapping if not confirmed
        records, headers, _ = read_tabular_file(Path(ev.stored_path))
        det = detect_file_type(headers, records, filename=ev.original_name)
        file_type = det["detected_type"] if det["detected_type"] != "unknown" else "cdr"
        suggested = suggest_column_mappings(file_type, headers)
        mapping = {h: v["canonical"] for h, v in suggested.items()}
        stmt_acct = None

    # Create Job
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

    # Count staged rows
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
