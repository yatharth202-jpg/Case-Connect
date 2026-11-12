"""
Forensic Persistence and Reopen API Router (Phase 5).
Compliant with Section 63 BSA 2023.

Endpoints:
- GET  /cases/{case_id}/analysis-results: List persisted analysis findings.
- POST /cases/{case_id}/analysis-results: Save analysis finding (and attach Finding node).
- GET  /cases/{case_id}/views: List saved graph views.
- POST /cases/{case_id}/views: Save viewport camera, selections, and filters.
- GET  /cases/{case_id}/views/{view_id}: Retrieve specific view.
- DELETE /cases/{case_id}/views/{view_id}: Delete view.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.db.sql import get_db, User, Case
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.services.persistence.service import (
    persist_analysis_result, get_case_analysis_results,
    save_graph_view, list_graph_views, get_graph_view, delete_graph_view
)

router = APIRouter(tags=["Forensic Persistence & Views"])


class AnalysisResultCreate(BaseModel):
    entity_id: str = Field(..., description="Canonical ID of the attributed entity")
    rank: int = Field(..., ge=1, description="Investigative rank")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized attribution score")
    breakdown: Dict[str, Any] = Field(default_factory=dict, description="Feature signals breakdown")
    evidence_ids: List[str] = Field(default_factory=list, description="Associated evidence file names or IDs")
    run_id: Optional[str] = Field(None, description="Optional batch run identifier")


class GraphViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120, description="Name for the saved view")
    view_data: Dict[str, Any] = Field(..., description="Viewport zoom, pan, selection, and filters")


# -------------------------------------------------------------------------
# Analysis Results Endpoints
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analysis-results", summary="Get Persisted Analysis Results")
def get_analysis_results(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all persisted forensic analysis findings for this case docket."""
    results = get_case_analysis_results(db, case.id)
    return {
        "case_id": case.id,
        "count": len(results),
        "results": results
    }


@router.post("/cases/{case_id}/analysis-results", summary="Persist Analysis Finding")
def create_analysis_result(
    case_id: str,
    payload: AnalysisResultCreate,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Persists an analysis finding and links a Finding node into the SQLite graph."""
    res = persist_analysis_result(
        db=db,
        case_id=case.id,
        user_id=current_user.id,
        entity_id=payload.entity_id,
        rank=payload.rank,
        score=payload.score,
        breakdown=payload.breakdown,
        evidence_ids=payload.evidence_ids,
        run_id=payload.run_id
    )
    return {
        "status": "persisted",
        "id": res.id,
        "case_id": case.id,
        "entity_id": res.entity_id,
        "rank": res.rank,
        "score": res.score
    }


# -------------------------------------------------------------------------
# Saved Graph Views Endpoints
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/views", summary="List Saved Graph Views")
def list_views(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all saved viewport states for the case."""
    views = list_graph_views(db, case.id)
    return {
        "case_id": case.id,
        "count": len(views),
        "views": views
    }


@router.post("/cases/{case_id}/views", summary="Save Graph View")
def create_view(
    case_id: str,
    payload: GraphViewCreate,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves the current graph viewport, camera pan/zoom, selection, and active filters."""
    view = save_graph_view(
        db=db,
        case_id=case.id,
        user_id=current_user.id,
        name=payload.name,
        view_data=payload.view_data
    )
    return {
        "status": "saved",
        "id": view.id,
        "case_id": case.id,
        "name": view.name
    }


@router.get("/cases/{case_id}/views/{view_id}", summary="Get Saved Graph View")
def get_view(
    case_id: str,
    view_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves a specific saved view configuration."""
    view = get_graph_view(db, case.id, view_id)
    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved graph view not found"
        )
    return view


@router.delete("/cases/{case_id}/views/{view_id}", summary="Delete Saved Graph View")
def delete_view(
    case_id: str,
    view_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a saved graph view."""
    success = delete_graph_view(db, case.id, current_user.id, view_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved graph view not found"
        )
    return {"status": "deleted", "view_id": view_id, "case_id": case.id}
