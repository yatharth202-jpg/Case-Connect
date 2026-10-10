import json
from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.db.sql import get_db, Case, Entity, EntityLink, Alert, EvidenceFile
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.services.ai.gemini_service import (
    is_gemini_configured,
    generate_case_modus_operandi,
    answer_investigation_copilot_query
)
from backend.app.services.analytics.router import (
    get_analytics_overview,
    get_leads_advisor,
    get_case_alerts
)

router = APIRouter(prefix="/ai", tags=["AI & Gemini Copilot"])

class CopilotQueryRequest(BaseModel):
    query: str

@router.get("/status")
def get_ai_status():
    """Returns whether Gemini AI engine is configured and ready."""
    configured = is_gemini_configured()
    return {
        "enabled": configured,
        "model": getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash") if configured else None,
        "message": "Gemini AI active" if configured else "Gemini API key not configured. Add GEMINI_API_KEY in .env"
    }

@router.post("/cases/{case_id}/brief")
async def generate_case_ai_brief(
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db)
):
    """Generates an executive Modus Operandi & Crime Nexus brief correlating all case data."""
    if not is_gemini_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured. Please supply GEMINI_API_KEY in .env."
        )

    # Gather case context
    overview = get_analytics_overview(case.id, None, None, case, None, db)
    leads_res = get_leads_advisor(case.id, None, 10, case, None, db)
    alerts_res = get_case_alerts(case.id, None, None, False, case, None, db)
    vehicles = db.query(Entity).filter(Entity.case_id == case.id, Entity.label == "Vehicle").all()

    context = {
        "title": case.title,
        "description": case.description,
        "total_money_volume": overview.get("total_money_volume_rs"),
        "total_txns": overview.get("total_txns"),
        "total_calls": overview.get("total_calls"),
        "vehicles": [v.canonical_id for v in vehicles],
        "leads": [
            {"name": l.get("display_name"), "priority": l.get("priority"), "level": l.get("level")}
            for l in leads_res.get("leads", [])[:5]
        ],
        "alerts": [
            {"entity": a.get("entity_id"), "pattern": a.get("pattern_type"), "explanation": a.get("explanation")}
            for a in alerts_res.get("alerts", [])[:5]
        ]
    }

    narrative = await generate_case_modus_operandi(context)
    return {
        "case_id": case.id,
        "brief": narrative
    }

@router.post("/cases/{case_id}/copilot")
async def ask_case_copilot(
    req: CopilotQueryRequest,
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db)
):
    """Ask natural language questions about the active case evidence and graph."""
    if not is_gemini_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured. Please supply GEMINI_API_KEY in .env."
        )

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    overview = get_analytics_overview(case.id, None, None, case, None, db)
    leads_res = get_leads_advisor(case.id, None, 10, case, None, db)
    alerts_res = get_case_alerts(case.id, None, None, False, case, None, db)
    entities = db.query(Entity).filter(Entity.case_id == case.id).limit(100).all()
    ev_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()

    case_context = {
        "case_title": case.title,
        "overview": overview,
        "top_leads": leads_res.get("leads", [])[:5],
        "alerts": alerts_res.get("alerts", [])[:10],
        "evidence_files": [e.original_name for e in ev_files],
        "key_entities": [{"id": e.canonical_id, "label": e.label, "name": e.display_name} for e in entities[:50]]
    }

    answer = await answer_investigation_copilot_query(req.query, case_context)
    return {
        "case_id": case.id,
        "query": req.query,
        "answer": answer
    }
