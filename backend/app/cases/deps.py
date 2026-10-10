from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.sql import get_db, Case, CaseMember, User
from backend.app.auth.deps import get_current_user

def get_case_for_user(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Case:
    """
    Enforces case membership on every case-scoped endpoint.
    - Resolves case by case_id.
    - Admins have blanket access across all cases.
    - Other users MUST be present in case_members; otherwise 403 Forbidden is raised.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' not found"
        )

    if current_user.role == "admin":
        return case

    membership = (
        db.query(CaseMember)
        .filter(CaseMember.case_id == case_id, CaseMember.user_id == current_user.id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not assigned as a member of this case"
        )

    return case
