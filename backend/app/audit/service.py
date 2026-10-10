import hashlib
import json
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.sql import AuditLog

AUDIT_LOCK = threading.Lock()

def canonical_json(data: dict) -> str:
    """Format dictionary into deterministic sorted canonical JSON string."""
    if not data:
        return "{}"
    return json.dumps(data, sort_keys=True, separators=(",", ":"))

def compute_row_hash(prev_hash: str, ts_str: str, user_id: str, action: str, object_type: str, object_id: str, details_canonical: str) -> str:
    """Compute deterministic SHA-256 hash for an audit log entry."""
    payload = f"{prev_hash}|{ts_str}|{user_id}|{action}|{object_type or ''}|{object_id or ''}|{details_canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def record_audit_log(
    db: Session,
    user_id: str,
    action: str,
    case_id: str = None,
    object_type: str = None,
    object_id: str = None,
    details: dict = None
) -> AuditLog:
    """
    Append an immutable, cryptographic SHA-256 chained entry to the audit log.
    If table is empty, prev_hash is set to 'GENESIS'. Thread-safe via AUDIT_LOCK.
    """
    with AUDIT_LOCK:
        last_log = db.execute(text("SELECT hash FROM audit_log ORDER BY rowid DESC LIMIT 1")).fetchone()
        prev_hash = last_log[0] if last_log else "GENESIS"

        now = datetime.utcnow()
        ts_str = now.isoformat()
        det_canonical = canonical_json(details or {})
        current_hash = compute_row_hash(prev_hash, ts_str, user_id, action, object_type, object_id, det_canonical)

        entry = AuditLog(
            ts=now,
            user_id=user_id,
            action=action,
            case_id=case_id,
            object_type=object_type,
            object_id=object_id,
            details_json=det_canonical,
            prev_hash=prev_hash,
            hash=current_hash
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

def verify_audit_chain(db: Session) -> dict:
    """
    Traverse the entire audit_log table in chronological insertion order.
    Verifies that:
      1. First row's prev_hash is 'GENESIS'.
      2. Every row's current hash matches the computed hash from its fields.
      3. Every subsequent row's prev_hash matches the previous row's current hash.
    Returns {valid: bool, checked_rows: int, broken_at: int | None, error: str | None}.
    """
    rows = db.query(AuditLog).all()
    if not rows:
        return {"valid": True, "checked_rows": 0, "broken_at": None, "error": None}

    expected_prev = "GENESIS"
    for idx, row in enumerate(rows):
        # 1. Check prev_hash continuity
        if row.prev_hash != expected_prev:
            return {
                "valid": False,
                "checked_rows": idx,
                "broken_at": idx + 1,
                "error": f"Hash chain broken at row {idx + 1}: expected prev_hash {expected_prev}, got {row.prev_hash}"
            }

        # 2. Recompute row hash
        ts_str = row.ts.isoformat()
        expected_hash = compute_row_hash(
            row.prev_hash,
            ts_str,
            row.user_id,
            row.action,
            row.object_type,
            row.object_id,
            row.details_json
        )
        if row.hash != expected_hash:
            return {
                "valid": False,
                "checked_rows": idx,
                "broken_at": idx + 1,
                "error": f"Row tampering detected at row {idx + 1}: stored hash {row.hash} != computed hash {expected_hash}"
            }

        expected_prev = row.hash

    return {
        "valid": True,
        "checked_rows": len(rows),
        "broken_at": None,
        "error": None
    }
