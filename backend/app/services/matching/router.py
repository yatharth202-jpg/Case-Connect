import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.sql import (
    get_db, MatchSuggestion, ProfileMember, Entity, EntityLink, User
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.services.matching.service import (
    generate_case_matches,
    approve_match,
    reject_match,
    undo_match,
    get_case_master_profiles,
    get_master_profile_detail,
    find_cross_case_alerts
)

router = APIRouter()

@router.get("/cases/{case_id}/matches")
def list_matches(
    case_id: str,
    level: Optional[str] = Query(None, description="Filter by level: HIGH, MEDIUM, SHARED_DEVICE, LOW"),
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, undone"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns entity match suggestions for a case.
    Enriched with Person A and Person B attributes for side-by-side comparison.
    """
    get_case_for_user(case_id, current_user, db)

    q = db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id)
    if level:
        q = q.filter(MatchSuggestion.level == level)
    if status:
        q = q.filter(MatchSuggestion.status == status)

    total = q.count()
    items = q.order_by(MatchSuggestion.score.desc(), MatchSuggestion.id.desc()).offset(offset).limit(limit).all()

    # Pre-fetch person entities for enrichment
    person_ids = set()
    for m in items:
        person_ids.add(m.entity_a_id)
        person_ids.add(m.entity_b_id)

    persons = db.query(Entity).filter(
        Entity.case_id == case_id,
        Entity.canonical_id.in_(list(person_ids))
    ).all()
    person_map = {p.canonical_id: p for p in persons}

    # Fetch links for identifiers
    links = db.query(EntityLink).filter(
        EntityLink.case_id == case_id,
        EntityLink.source_entity_id.in_(list(person_ids))
    ).all()
    links_by_person: Dict[str, Dict[str, List[str]]] = {}
    for l in links:
        links_by_person.setdefault(l.source_entity_id, {}).setdefault(l.relationship_type, []).append(l.target_entity_id)

    results = []
    for m in items:
        p_a = person_map.get(m.entity_a_id)
        p_b = person_map.get(m.entity_b_id)
        reasons = []
        try:
            reasons = json.loads(m.reasons_json)
        except Exception:
            pass

        results.append({
            "id": m.id,
            "case_id": m.case_id,
            "level": m.level,
            "score": m.score,
            "status": m.status,
            "reasons": reasons,
            "decided_by": m.decided_by,
            "decided_at": m.decided_at.isoformat() if m.decided_at else None,
            "entity_a": {
                "id": m.entity_a_id,
                "name": p_a.display_name if p_a else m.entity_a_id,
                "source_file": p_a.source_file if p_a else "Unknown",
                "source_ref": p_a.source_ref if p_a else "Unknown",
                "phones": links_by_person.get(m.entity_a_id, {}).get("USES", []),
                "accounts": links_by_person.get(m.entity_a_id, {}).get("OWNS", []),
                "vehicles": links_by_person.get(m.entity_a_id, {}).get("DRIVES", [])
            },
            "entity_b": {
                "id": m.entity_b_id,
                "name": p_b.display_name if p_b else m.entity_b_id,
                "source_file": p_b.source_file if p_b else "Unknown",
                "source_ref": p_b.source_ref if p_b else "Unknown",
                "phones": links_by_person.get(m.entity_b_id, {}).get("USES", []),
                "accounts": links_by_person.get(m.entity_b_id, {}).get("OWNS", []),
                "vehicles": links_by_person.get(m.entity_b_id, {}).get("DRIVES", [])
            }
        })

    return {
        "total": total,
        "items": results
    }

@router.post("/cases/{case_id}/matches/generate")
def run_match_generation(
    case_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Executes the candidate matching engine on case entities."""
    get_case_for_user(case_id, current_user, db)
    result = generate_case_matches(db, case_id)
    return result

@router.post("/matches/{match_id}/approve")
def approve_match_endpoint(
    match_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Approves an entity match suggestion and creates or updates a MasterProfile.
    Enforces non-destructive resolution.
    """
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found")

    get_case_for_user(ms.case_id, current_user, db)

    try:
        res = approve_match(db, match_id, current_user.id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/matches/{match_id}/reject")
def reject_match_endpoint(
    match_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Rejects an entity match suggestion."""
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found")

    get_case_for_user(ms.case_id, current_user, db)

    try:
        res = reject_match(db, match_id, current_user.id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/matches/{match_id}/undo")
def undo_match_endpoint(
    match_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Undoes an approved entity match and restores the original entity graph."""
    ms = db.query(MatchSuggestion).filter(MatchSuggestion.id == match_id).first()
    if not ms:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match suggestion not found")

    get_case_for_user(ms.case_id, current_user, db)

    try:
        res = undo_match(db, match_id, current_user.id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/cases/{case_id}/profiles")
def list_master_profiles(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists consolidated Master Profiles for a case."""
    get_case_for_user(case_id, current_user, db)
    return get_case_master_profiles(db, case_id)

@router.get("/cases/{case_id}/profiles/{profile_id}")
def get_master_profile_detail_endpoint(
    case_id: str,
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns detailed dossier for a specific Master Profile."""
    get_case_for_user(case_id, current_user, db)
    detail = get_master_profile_detail(db, case_id, profile_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master profile not found")
    return detail

@router.get("/cases/{case_id}/cross-case-alerts")
def get_cross_case_alerts_endpoint(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns cross-case alerts for matching identifiers."""
    get_case_for_user(case_id, current_user, db)
    return find_cross_case_alerts(db, case_id, current_user.id)
