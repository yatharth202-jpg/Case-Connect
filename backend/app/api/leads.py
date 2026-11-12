"""
Forensic Lead Advisor API Router for CaseConnect AI (Phase 3 Upgrade).
Exposes explainable Top-N Primary Attributed Leads compliant with Section 63 BSA 2023.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.sql import get_db, Case, User
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.services.top_leads import (
    get_stored_or_computed_top_leads,
    compute_case_top_leads,
    LEGAL_DISCLAIMER
)

router = APIRouter()


@router.get("/cases/{case_id}/top-leads", summary="Retrieve Top-N Primary Attributed Leads")
def get_case_top_leads(
    case_id: str,
    n: int = Query(5, ge=1, le=50, description="Number of top leads to return (defaults to 5)"),
    recompute: bool = Query(False, description="Force recomputation rather than loading persisted DB analysis"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Returns prioritized Primary Attributed Leads based on weighted topological centrality,
    pass-through transaction analysis, and cross-case intelligence.

    All scores are explainable statistical indicators for investigative prioritization,
    strictly compliant with Section 63 BSA 2023.
    """
    try:
        leads = get_stored_or_computed_top_leads(
            db=db,
            case_id=case.id,
            n=n,
            recompute=recompute
        )

        return {
            "case_id": case.id,
            "legal_standard": "Section 63 Bharatiya Sakshya Adhiniyam, 2023",
            "disclaimer": LEGAL_DISCLAIMER,
            "count": len(leads),
            "leads": leads,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lead computation failed: {str(e)}"
        )
