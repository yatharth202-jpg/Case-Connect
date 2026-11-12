"""
Excel Export API Router for CaseConnect AI (Phase 2 Upgrade).
Provides streaming and background export endpoints compliant with Section 63 BSA 2023.
"""

import os
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.app.db.sql import get_db, Case, Job, User, SessionLocal
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.services.excel_export import export_case_to_excel

router = APIRouter()


def _run_background_export(
    job_id: str,
    case_id: str,
    user_id: str,
    tables: Optional[List[str]],
    file_id: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
):
    """Worker function for heavy background exports."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        case = db.query(Case).filter(Case.id == case_id).first()
        user = db.query(User).filter(User.id == user_id).first() if user_id else None

        if not job or not case:
            return

        job.status = "running"
        job.progress = 25
        db.commit()

        filepath, sha256_hash, exported_counts = export_case_to_excel(
            db=db,
            case=case,
            user=user,
            tables=tables,
            file_id=file_id,
            date_from=date_from,
            date_to=date_to,
        )

        job.status = "done"
        job.progress = 100
        job.steps_json = json.dumps({
            "filepath": str(filepath),
            "sha256": sha256_hash,
            "counts": exported_counts
        })
        db.commit()
    except Exception as e:
        db.rollback()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/cases/{case_id}/export.xlsx", summary="Export Case Data to Excel Dossier")
def export_case_xlsx(
    case_id: str,
    background_tasks: BackgroundTasks,
    tables: Optional[str] = Query(None, description="Comma-separated list of tables to include (e.g. raw_rows,call_records,transactions)"),
    file_id: Optional[str] = Query(None, description="Filter raw_rows and staged tables by evidence file ID"),
    date_from: Optional[str] = Query(None, description="ISO-8601 start date filter (inclusive)"),
    date_to: Optional[str] = Query(None, description="ISO-8601 end date filter (inclusive)"),
    background: bool = Query(False, description="Run export in background job and return download link"),
    job_id: Optional[str] = Query(None, description="Retrieve completed background export job"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Generates a multi-sheet, formula-safe Excel (.xlsx) workbook containing
    all lossless raw rows, staged records, entities, and graph topologies.
    """
    tables_list = [t.strip().lower() for t in tables.split(",")] if tables else None

    # Handle check or retrieval of an existing background job
    if job_id:
        job = db.query(Job).filter(Job.id == job_id, Job.case_id == case.id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Export job {job_id} not found for this case."
            )
        if job.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Export job failed: {job.error_message}"
            )
        if job.status in ("queued", "running"):
            return {
                "job_id": job.id,
                "status": job.status,
                "progress": job.progress,
                "message": "Export is currently generating in background."
            }
        # Done
        try:
            steps_data = json.loads(job.steps_json or "{}")
            filepath = Path(steps_data.get("filepath", ""))
            if not filepath.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Generated export file is no longer available on disk."
                )
            download_filename = f"case_{getattr(case, 'case_number', None) or case.id[:8]}_export.xlsx"
            return FileResponse(
                path=str(filepath),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=download_filename,
            )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve export file: {str(e)}"
            )

    # If background processing is explicitly requested
    if background:
        job = Job(
            case_id=case.id,
            job_type="export",
            status="queued",
            progress=0,
            steps_json="{}"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        background_tasks.add_task(
            _run_background_export,
            job_id=job.id,
            case_id=case.id,
            user_id=str(current_user.id) if hasattr(current_user, "id") else "",
            tables=tables_list,
            file_id=file_id,
            date_from=date_from,
            date_to=date_to,
        )

        return {
            "job_id": job.id,
            "status": "queued",
            "download_url": f"/cases/{case.id}/export.xlsx?job_id={job.id}"
        }

    # Direct synchronous streaming export
    try:
        filepath, sha256_hash, exported_counts = export_case_to_excel(
            db=db,
            case=case,
            user=current_user,
            tables=tables_list,
            file_id=file_id,
            date_from=date_from,
            date_to=date_to,
        )

        download_filename = f"case_{getattr(case, 'case_number', None) or case.id[:8]}_export.xlsx"
        return FileResponse(
            path=str(filepath),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=download_filename,
            headers={
                "X-Case-Integrity-SHA256": sha256_hash,
                "Access-Control-Expose-Headers": "X-Case-Integrity-SHA256, Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excel export failed: {str(e)}"
        )
