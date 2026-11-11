"""
Forensic Job Lifecycle, Concurrency Locking, and Cooperative Cancellation Engine
for CaseConnect AI (Extraction V2 Phase 8).

Ensures:
  - Every heavy forensic task (ingest, merge, OCR, recompute) tracks steps_json progress.
  - Per-case concurrency locking prevents conflicting concurrent writes.
  - Cooperative cancellation allows clean aborts at batch/page boundaries without corrupting state.
  - Retriable endpoints allow officers to re-run failed or cancelled jobs.
  - Structured reason codes on failure or cancellation.
"""

from datetime import datetime
import json
import threading
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.db.sql import Job, EvidenceFile

_GLOBAL_LOCK_GUARD = threading.Lock()
_CASE_RUNNING_JOBS: Dict[str, str] = {}  # case_id -> active job_id


def acquire_case_job_lock(
    case_id: str,
    job_id: str,
    job_type: str,
    db: Optional[Session] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Attempts to acquire exclusive forensic processing lock for the given case.
    Returns (True, None) if lock is successfully acquired.
    Returns (False, conflicting_job_id) if another heavy job is actively running.
    """
    with _GLOBAL_LOCK_GUARD:
        existing_active = _CASE_RUNNING_JOBS.get(case_id)
        if existing_active and existing_active != job_id:
            # Check if existing job is truly still running in DB
            if db:
                running_job = db.query(Job).filter(
                    Job.id == existing_active,
                    Job.status.in_(["running", "queued"]),
                ).first()
                if running_job:
                    return False, existing_active
                else:
                    # Stale in-memory lock cleared
                    _CASE_RUNNING_JOBS.pop(case_id, None)
            else:
                return False, existing_active

        _CASE_RUNNING_JOBS[case_id] = job_id
        return True, None


def release_case_job_lock(case_id: str, job_id: str) -> None:
    """Releases exclusive processing lock for a case."""
    with _GLOBAL_LOCK_GUARD:
        if _CASE_RUNNING_JOBS.get(case_id) == job_id:
            _CASE_RUNNING_JOBS.pop(case_id, None)


def is_job_cancelled(db: Session, job_id: str) -> bool:
    """
    Cooperative cancellation check invoked by workers at chunk/page boundaries.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return True
    return job.status in ("cancelling", "cancelled")


def cancel_job(
    db: Session,
    job_id: str,
    user_id: str,
    reason: str = "Cancelled by officer",
) -> Job:
    """
    Cooperatively cancels a queued or running job, updating steps_json and reason_code.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status in ("done", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JOB_NOT_RUNNING: Cannot cancel a job in '{job.status}' status.",
        )

    current_steps: List[str] = []
    try:
        current_steps = json.loads(job.steps_json or "[]")
    except Exception:
        current_steps = []

    current_steps.append(f"Cancellation requested: {reason}")
    job.status = "cancelled"
    job.reason_code = "CANCELLED_BY_OFFICER"
    job.error_message = reason
    job.steps_json = json.dumps(current_steps)
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    release_case_job_lock(job.case_id, job.id)

    record_audit_log(
        db=db,
        user_id=user_id,
        action="cancel_job",
        case_id=job.case_id,
        object_type="job",
        object_id=job.id,
        details={
            "job_type": job.job_type,
            "reason": reason,
            "status": "cancelled",
        },
    )

    return job


def reset_job_for_retry(
    db: Session,
    job_id: str,
    user_id: str,
) -> Job:
    """
    Resets a failed or cancelled job into queued state for reprocessing.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JOB_NOT_RETRIABLE: Only failed or cancelled jobs can be retried (current status: '{job.status}').",
        )

    current_steps: List[str] = []
    try:
        current_steps = json.loads(job.steps_json or "[]")
    except Exception:
        current_steps = []

    current_steps.append("Job retry initialized by officer")
    job.status = "queued"
    job.progress = 0
    job.error_message = None
    job.reason_code = None
    job.steps_json = json.dumps(current_steps)
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    record_audit_log(
        db=db,
        user_id=user_id,
        action="retry_job",
        case_id=job.case_id,
        object_type="job",
        object_id=job.id,
        details={
            "job_type": job.job_type,
            "status": "queued",
        },
    )

    return job
