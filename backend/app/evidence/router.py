import os
import stat
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.db.sql import get_db, Case, EvidenceFile, User
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.audit.service import record_audit_log

router = APIRouter()

# Size thresholds
MAX_TABULAR_SIZE = 200 * 1024 * 1024  # 200 MB
MAX_DOC_SIZE = 20 * 1024 * 1024       # 20 MB
MAX_IMAGE_SIZE = 30 * 1024 * 1024     # 30 MB

ALLOWED_EXTENSIONS = {
    ".csv": MAX_TABULAR_SIZE,
    ".xlsx": MAX_TABULAR_SIZE,
    ".json": MAX_TABULAR_SIZE,
    ".jsonl": MAX_TABULAR_SIZE,
    ".txt": MAX_DOC_SIZE,
    ".pdf": MAX_DOC_SIZE,
    ".docx": MAX_DOC_SIZE,
    ".png": MAX_IMAGE_SIZE,
    ".jpg": MAX_IMAGE_SIZE,
    ".jpeg": MAX_IMAGE_SIZE,
    ".webp": MAX_IMAGE_SIZE,
    ".bmp": MAX_IMAGE_SIZE,
    ".tiff": MAX_IMAGE_SIZE,
}

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    original_name: str
    file_size: int
    sha256: str
    detected_type: Optional[str]
    status: str
    uploaded_at: str

class VerifyEvidenceResponse(BaseModel):
    valid: bool
    evidence_id: str
    original_name: str
    stored_hash: str
    computed_hash: str

def validate_magic_bytes(ext: str, header: bytes):
    """Validate file signatures for binary documents and images."""
    if ext == ".pdf":
        if not header.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file: Missing %PDF magic byte signature"
            )
    elif ext in [".xlsx", ".docx"]:
        # Both are OpenXML ZIP packages
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {ext.upper()} file: Missing ZIP archive signature"
            )
    elif ext == ".png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PNG image: Missing PNG signature"
            )
    elif ext in [".jpg", ".jpeg"]:
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JPEG image: Missing JPEG signature"
            )
    elif ext == ".bmp":
        if not header.startswith(b"BM"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid BMP image: Missing BMP signature"
            )
    elif ext == ".webp":
        if not (header.startswith(b"RIFF") and b"WEBP" in header[:12]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid WEBP image: Missing WEBP signature"
            )

def detect_initial_type(filename: str) -> str:
    """Heuristic file type identification for initial status."""
    fn = filename.lower()
    ext = Path(filename).suffix.lower()
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        return "image_document"
    if "cdr" in fn or "call" in fn or "telecom" in fn:
        return "cdr"
    elif "bank" in fn or "txn" in fn or "statement" in fn or "paysim" in fn:
        return "bank_transactions"
    elif "fir" in fn or "complaint" in fn:
        return "fir"
    elif "ip" in fn or "log" in fn:
        return "ip_logs"
    elif "sdr" in fn:
        return "sdr"
    return "unknown"

@router.post("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
@router.post("/cases/{case_id}/evidence/", response_model=List[EvidenceResponse])
async def upload_evidence(
    case_id: str,
    files: List[UploadFile] = File(...),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """
    Upload multipart evidence files into case repository.
    Validates extension, size limit, and magic bytes.
    Stream-computes SHA-256 while saving to read-only path.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    upload_base = Path(settings.UPLOAD_DIR) / case.id
    upload_base.mkdir(parents=True, exist_ok=True)

    results = []

    for file in files:
        original_name = Path(file.filename).name
        ext = Path(original_name).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not supported. Allowed: {list(ALLOWED_EXTENSIONS.keys())}"
            )

        max_limit = ALLOWED_EXTENSIONS[ext]
        file_uuid = str(uuid.uuid4())
        target_path = upload_base / f"{file_uuid}_{original_name}"

        hasher = hashlib.sha256()
        total_size = 0
        first_chunk = True

        # Stream save and compute hash
        with open(target_path, "wb") as out_f:
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                
                total_size += len(chunk)
                if total_size > max_limit:
                    out_f.close()
                    target_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File '{original_name}' exceeds size limit of {max_limit // (1024 * 1024)} MB"
                    )

                if first_chunk:
                    validate_magic_bytes(ext, chunk)
                    first_chunk = False

                hasher.update(chunk)
                out_f.write(chunk)

        computed_sha = hasher.hexdigest()

        # Set read-only permissions
        try:
            os.chmod(target_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except Exception:
            pass

        # Insert record into evidence_files
        evidence_entry = EvidenceFile(
            id=file_uuid,
            case_id=case.id,
            original_name=original_name,
            stored_path=str(target_path.resolve()),
            sha256=computed_sha,
            file_size=total_size,
            detected_type=detect_initial_type(original_name),
            status="uploaded",
            uploader_id=current_user.id,
            created_at=datetime.utcnow()
        )
        db.add(evidence_entry)
        db.commit()
        db.refresh(evidence_entry)

        # Log action to cryptographic audit chain
        record_audit_log(
            db=db,
            user_id=current_user.id,
            action="upload_evidence",
            case_id=case.id,
            object_type="evidence_file",
            object_id=evidence_entry.id,
            details={
                "original_name": original_name,
                "sha256": computed_sha,
                "size_bytes": total_size
            }
        )

        results.append(EvidenceResponse(
            id=evidence_entry.id,
            case_id=case.id,
            original_name=original_name,
            file_size=total_size,
            sha256=computed_sha,
            detected_type=evidence_entry.detected_type,
            status=evidence_entry.status,
            uploaded_at=evidence_entry.created_at.isoformat()
        ))

    return results

@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
def list_case_evidence(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db)
):
    """List all evidence files uploaded to the specified case."""
    files = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.case_id == case.id)
        .order_by(EvidenceFile.created_at.desc())
        .all()
    )
    return [
        EvidenceResponse(
            id=f.id,
            case_id=f.case_id,
            original_name=f.original_name,
            file_size=f.file_size,
            sha256=f.sha256,
            detected_type=f.detected_type,
            status=f.status,
            uploaded_at=f.created_at.isoformat()
        )
        for f in files
    ]

@router.post("/evidence/{evidence_id}/verify", response_model=VerifyEvidenceResponse)
def verify_evidence_integrity(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recompute SHA-256 of the stored evidence file on disk.
    Confirms bit-for-bit integrity against the stored hash in the database.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    # Enforce case membership
    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    file_path = Path(ev.stored_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence file missing on disk at {ev.stored_path}"
        )

    # Recompute hash
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)

    computed_sha = hasher.hexdigest()
    is_valid = (computed_sha == ev.sha256)

    # Record verification in audit log
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="verify_evidence",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={
            "original_name": ev.original_name,
            "valid": is_valid,
            "stored_hash": ev.sha256,
            "computed_hash": computed_sha
        }
    )

    return VerifyEvidenceResponse(
        valid=is_valid,
        evidence_id=ev.id,
        original_name=ev.original_name,
        stored_hash=ev.sha256,
        computed_hash=computed_sha
    )

@router.delete("/evidence/{evidence_id}")
def delete_evidence(
    evidence_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Remove evidence file from disk and database with full audit logging."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    # Enforce case membership
    case = get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    # Remove file on disk
    file_path = Path(ev.stored_path)
    if file_path.exists():
        try:
            # Clear read-only bit to allow unlinking
            os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
            file_path.unlink()
        except Exception:
            pass

    # Log action before deletion
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_evidence",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={"original_name": ev.original_name, "sha256": ev.sha256}
    )

    db.delete(ev)
    db.commit()

    return {"status": "deleted", "id": evidence_id, "case_id": case.id}
