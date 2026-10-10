from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.sql import get_db, AuditLog
from backend.app.auth.deps import require_role
from backend.app.audit.service import verify_audit_chain

router = APIRouter()

@router.get("/verify")
def verify_audit(
    current_user=Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Cryptographic verification endpoint (Admin only).
    Walks the entire SHA-256 hash chain and flags any direct database tampering.
    """
    result = verify_audit_chain(db)
    return result

@router.get("/logs")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user=Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """List audit log entries (Admin only)."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.ts.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(AuditLog).count()
    
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "timestamp": log.ts.isoformat(),
                "user_id": log.user_id,
                "action": log.action,
                "case_id": log.case_id,
                "object_type": log.object_type,
                "object_id": log.object_id,
                "details_json": log.details_json,
                "prev_hash": log.prev_hash,
                "hash": log.hash
            }
            for log in logs
        ]
    }
