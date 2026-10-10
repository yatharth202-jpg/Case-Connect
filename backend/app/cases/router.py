import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    get_db, Case, CaseMember, CaseSetting, EvidenceFile, User,
    SavedView, CallRecord, Transaction, Alert, Entity, EntityLink,
    ExtractedEntity, MatchSuggestion, LeadDecision
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.audit.service import record_audit_log

DEFAULTS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "defaults.yaml"

def get_effective_case_settings(db: Session, case_id: str) -> dict:
    defaults = {}
    if DEFAULTS_PATH.exists():
        try:
            with open(DEFAULTS_PATH, "r", encoding="utf-8") as f:
                defaults = yaml.safe_load(f) or {}
        except Exception:
            defaults = {}

    row = db.query(CaseSetting).filter(CaseSetting.case_id == case_id).first()
    if not row:
        return defaults

    try:
        overrides = json.loads(row.settings_json)
        merged = dict(defaults)
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k] = {**merged[k], **v}
            else:
                merged[k] = v
        return merged
    except Exception:
        return defaults


router = APIRouter()

class CreateCaseRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium" # high, medium, low

class AddMemberRequest(BaseModel):
    user_id: str
    role: str = "investigator"

class CaseMemberResponse(BaseModel):
    id: str
    user_id: str
    username: str
    role: str

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    created_by: str
    created_at: str
    evidence_count: int = 0

@router.post("", response_model=CaseResponse)
def create_case(
    req: CreateCaseRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Create a new investigation case and assign creator as lead member."""
    if not req.title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Case title cannot be empty"
        )

    new_case = Case(
        title=req.title.strip(),
        description=req.description.strip() if req.description else "",
        priority=req.priority.lower(),
        status="active",
        created_by=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Assign creator as lead member
    membership = CaseMember(
        case_id=new_case.id,
        user_id=current_user.id,
        role="lead",
        added_at=datetime.utcnow()
    )
    db.add(membership)
    db.commit()

    # Log action to immutable audit trail
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="create_case",
        case_id=new_case.id,
        object_type="case",
        object_id=new_case.id,
        details={"title": new_case.title, "priority": new_case.priority}
    )

    return CaseResponse(
        id=new_case.id,
        title=new_case.title,
        description=new_case.description,
        priority=new_case.priority,
        status=new_case.status,
        created_by=new_case.created_by,
        created_at=new_case.created_at.isoformat(),
        evidence_count=0
    )

@router.get("", response_model=List[CaseResponse])
def list_cases(
    search: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List accessible cases.
    - Admins see all cases.
    - Investigators and Viewers only see cases where they are registered members.
    """
    if current_user.role == "admin":
        query = db.query(Case)
    else:
        query = (
            db.query(Case)
            .join(CaseMember, Case.id == CaseMember.case_id)
            .filter(CaseMember.user_id == current_user.id)
        )

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Case.title.ilike(s)) | (Case.description.ilike(s)))

    if priority:
        query = query.filter(Case.priority == priority.lower())

    cases = query.order_by(Case.created_at.desc()).all()

    # Compute evidence count per case
    results = []
    for c in cases:
        ev_count = db.query(EvidenceFile).filter(EvidenceFile.case_id == c.id).count()
        results.append(CaseResponse(
            id=c.id,
            title=c.title,
            description=c.description,
            priority=c.priority,
            status=c.status,
            created_by=c.created_by,
            created_at=c.created_at.isoformat(),
            evidence_count=ev_count
        ))

    return results

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db)
):
    """Retrieve case details with strict membership validation."""
    ev_count = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).count()
    return CaseResponse(
        id=case.id,
        title=case.title,
        description=case.description,
        priority=case.priority,
        status=case.status,
        created_by=case.created_by,
        created_at=case.created_at.isoformat(),
        evidence_count=ev_count
    )

@router.delete("/{case_id}")
def delete_case(
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Permanently delete a case and all associated evidence and extracted data."""
    case_id = case.id
    db.query(CaseMember).filter(CaseMember.case_id == case_id).delete(synchronize_session=False)
    db.query(CaseSetting).filter(CaseSetting.case_id == case_id).delete(synchronize_session=False)
    db.query(CallRecord).filter(CallRecord.case_id == case_id).delete(synchronize_session=False)
    db.query(Transaction).filter(Transaction.case_id == case_id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.case_id == case_id).delete(synchronize_session=False)
    db.query(Entity).filter(Entity.case_id == case_id).delete(synchronize_session=False)
    db.query(EntityLink).filter(EntityLink.case_id == case_id).delete(synchronize_session=False)
    db.query(ExtractedEntity).filter(ExtractedEntity.case_id == case_id).delete(synchronize_session=False)
    db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id).delete(synchronize_session=False)
    db.query(LeadDecision).filter(LeadDecision.case_id == case_id).delete(synchronize_session=False)
    db.query(SavedView).filter(SavedView.case_id == case_id).delete(synchronize_session=False)
    db.query(EvidenceFile).filter(EvidenceFile.case_id == case_id).delete(synchronize_session=False)
    db.delete(case)
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_case",
        case_id=case_id,
        object_type="case",
        object_id=case_id,
        details={"case_id": case_id, "title": case.title}
    )
    return {"status": "success", "message": f"Case '{case.title}' deleted successfully"}

@router.post("/{case_id}/members")
def add_case_member(
    req: AddMemberRequest,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Add a user as a member to this case."""
    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    existing = db.query(CaseMember).filter(CaseMember.case_id == case.id, CaseMember.user_id == req.user_id).first()
    if existing:
        return {"status": "exists", "message": "User is already a member of this case"}

    membership = CaseMember(
        case_id=case.id,
        user_id=req.user_id,
        role=req.role,
        added_at=datetime.utcnow()
    )
    db.add(membership)
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="add_member",
        case_id=case.id,
        object_type="user",
        object_id=req.user_id,
        details={"case_title": case.title, "role": req.role}
    )

    return {"status": "added", "user_id": req.user_id, "case_id": case.id}

@router.delete("/{case_id}/members/{user_id}")
def remove_case_member(
    user_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Remove a user from case membership."""
    membership = db.query(CaseMember).filter(CaseMember.case_id == case.id, CaseMember.user_id == user_id).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found")

    db.delete(membership)
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="remove_member",
        case_id=case.id,
        object_type="user",
        object_id=user_id,
        details={"case_title": case.title}
    )

    return {"status": "removed", "user_id": user_id, "case_id": case.id}

@router.get("/{case_id}/settings")
def get_case_settings(
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db)
):
    """Returns effective case settings (defaults merged with case-specific overrides)."""
    return get_effective_case_settings(db, case.id)

@router.put("/{case_id}/settings")
def update_case_settings(
    settings_data: dict,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Updates case-specific settings overrides and records audit entry."""
    row = db.query(CaseSetting).filter(CaseSetting.case_id == case.id).first()
    if not row:
        row = CaseSetting(case_id=case.id, settings_json=json.dumps(settings_data))
        db.add(row)
    else:
        row.settings_json = json.dumps(settings_data)
        row.updated_at = datetime.utcnow()
    db.commit()

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="settings_change",
        case_id=case.id,
        object_type="case_setting",
        object_id=case.id,
        details={"updated_keys": list(settings_data.keys())}
    )

    return get_effective_case_settings(db, case.id)


@router.post("/{case_id}/settings/recompute")
def recompute_case_analytics(
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Re-runs communication and financial pattern detection using effective case settings.
    Updates system Alerts and re-evaluates Lead Advisor scores.
    Audited as 'analytics_recompute'.
    """
    from backend.app.services.analytics.comm_patterns import detect_communication_patterns
    from backend.app.services.money.patterns import detect_money_patterns
    from backend.app.services.analytics.lead_advisor import compute_lead_advisor

    settings = get_effective_case_settings(db, case.id)
    calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
    txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()

    comm_alerts = detect_communication_patterns(calls, settings)
    money_alerts = detect_money_patterns(txns, settings)
    all_raw_alerts = comm_alerts + money_alerts

    # Delete existing automatic alerts for this case
    db.query(Alert).filter(Alert.case_id == case.id).delete()

    # Re-persist newly computed alerts
    persisted_alerts = []
    for a in all_raw_alerts:
        alt = Alert(
            case_id=case.id,
            entity_id=str(a.get("entity_id", "Unknown")),
            pattern_type=str(a.get("pattern_type", "anomaly")),
            severity=str(a.get("severity", "medium")),
            alert_date=str(a.get("date") or datetime.utcnow().strftime("%Y-%m-%d")),
            explanation=str(a.get("explanation", "")),
            evidence_ids_json=json.dumps(a.get("evidence_ids", []))
        )
        db.add(alt)
        persisted_alerts.append(alt)

    db.commit()

    # Re-evaluate lead advisor
    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    from backend.app.db.sql import EntityLink, ExtractedEntity
    entity_links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()
    extracted_entities = db.query(ExtractedEntity).filter(ExtractedEntity.case_id == case.id).all()

    leads_res = compute_lead_advisor(
        case_id=case.id,
        entities=entities,
        entity_links=entity_links,
        call_records=calls,
        transactions=txns,
        evidence_files=evidence_files,
        extracted_entities=extracted_entities,
        alerts=all_raw_alerts,
        settings=settings
    )

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="analytics_recompute",
        case_id=case.id,
        object_type="case_setting",
        object_id=case.id,
        details={
            "alerts_generated": len(persisted_alerts),
            "leads_evaluated": len(leads_res)
        }
    )

    return {
        "status": "success",
        "case_id": case.id,
        "alerts_count": len(persisted_alerts),
        "leads_count": len(leads_res),
        "message": f"Analytics recomputed successfully: {len(persisted_alerts)} alerts and {len(leads_res)} leads updated."
    }


class SavedViewCreate(BaseModel):
    title: str
    view_config: dict

@router.get("/{case_id}/saved-views")
def list_saved_views(
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve saved graph and investigation bookmarks for this user in this case."""
    views = db.query(SavedView).filter(
        SavedView.case_id == case.id,
        SavedView.user_id == current_user.id
    ).order_by(SavedView.created_at.desc()).all()

    res = []
    for v in views:
        cfg = {}
        try:
            cfg = json.loads(v.view_config_json)
        except Exception:
            pass
        res.append({
            "id": v.id,
            "title": v.title,
            "view_config": cfg,
            "created_at": v.created_at.isoformat() if v.created_at else None
        })
    return res

@router.post("/{case_id}/saved-views")
def create_saved_view(
    payload: SavedViewCreate,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an investigation view bookmark."""
    if not payload.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    sv = SavedView(
        case_id=case.id,
        user_id=current_user.id,
        title=payload.title.strip(),
        view_config_json=json.dumps(payload.view_config)
    )
    db.add(sv)
    db.commit()
    db.refresh(sv)
    return {
        "id": sv.id,
        "title": sv.title,
        "view_config": payload.view_config,
        "created_at": sv.created_at.isoformat() if sv.created_at else None
    }

@router.delete("/{case_id}/saved-views/{view_id}")
def delete_saved_view(
    view_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a saved view."""
    sv = db.query(SavedView).filter(
        SavedView.id == view_id,
        SavedView.case_id == case.id,
        SavedView.user_id == current_user.id
    ).first()
    if not sv:
        raise HTTPException(status_code=404, detail="Saved view not found")
    db.delete(sv)
    db.commit()
    return {"status": "deleted", "id": view_id}

@router.post("/seed/hawala")
def seed_hawala_syndicate_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generates and auto-analyzes the Operation RedSand Hawala & Angadia Syndicate case."""
    from scripts.generate_hawala_case import seed_and_analyze_hawala_case
    case_id = seed_and_analyze_hawala_case()
    case = db.query(Case).filter(Case.id == case_id).first()
    return {
        "status": "success",
        "case_id": case_id,
        "title": case.title if case else "Operation RedSand (FIR 409/2026)",
        "message": "Hawala syndicate case fully ingested, indexed, and analyzed."
    }


