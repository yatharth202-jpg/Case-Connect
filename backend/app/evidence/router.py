import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import stat
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.config import get_extraction_config, settings
from backend.app.db.sql import Case, EvidenceFile, User, get_db
from backend.app.services.extraction.ocr.preprocess import (
    assess_image_quality,
    extract_exif_and_hashes,
    phash_distance,
)
from backend.app.services.ingestion.malware import get_malware_scanner
from backend.app.services.ingestion.safety import (
    sanitize_filename,
    safe_unpack_zip,
    safe_inspect_docx,
    safe_inspect_pdf,
)

router = APIRouter()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
DOC_EXTENSIONS = {".txt", ".pdf", ".docx"}


def get_allowed_extensions_map() -> Dict[str, int]:
    """Builds extension -> max_bytes mapping from `extraction.upload` in defaults.yaml."""
    up_cfg = get_extraction_config().get("upload", {})
    max_tab_bytes = int(up_cfg.get("max_file_mb", 200)) * 1024 * 1024
    max_doc_bytes = int(up_cfg.get("max_doc_mb", 20)) * 1024 * 1024
    max_img_bytes = int(up_cfg.get("max_image_mb", 30)) * 1024 * 1024
    allowed_list = up_cfg.get("allowed_types") or [
        ".csv", ".xlsx", ".json", ".jsonl", ".pdf", ".docx", ".txt",
        ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".zip",
    ]
    out: Dict[str, int] = {}
    for ext in allowed_list:
        ext_norm = str(ext).lower().strip()
        if ext_norm in IMAGE_EXTENSIONS:
            out[ext_norm] = max_img_bytes
        elif ext_norm in DOC_EXTENSIONS:
            out[ext_norm] = max_doc_bytes
        else:
            out[ext_norm] = max_tab_bytes
    return out


class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    original_name: str
    file_size: int
    sha256: str
    detected_type: Optional[str]
    status: str
    uploaded_at: str
    perceptual_hash: Optional[str] = None
    is_handwritten: bool = False
    quality_reason: Optional[str] = None
    duplicate_of_evidence_id: Optional[str] = None
    exif: Optional[Dict[str, Any]] = None


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
                detail="Invalid PDF file: Missing %PDF magic byte signature",
            )
    elif ext in [".xlsx", ".docx", ".zip"]:
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {ext.upper()} file: Missing ZIP archive signature",
            )
    elif ext == ".png":
        if not header.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PNG image: Missing PNG signature",
            )
    elif ext in [".jpg", ".jpeg"]:
        if not header.startswith(b"\xff\xd8\xff"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JPEG image: Missing JPEG signature",
            )
    elif ext == ".bmp":
        if not header.startswith(b"BM"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid BMP image: Missing BMP signature",
            )
    elif ext == ".webp":
        if not (header.startswith(b"RIFF") and b"WEBP" in header[:12]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid WEBP image: Missing WEBP signature",
            )
    elif ext in [".tiff", ".tif"]:
        if not (header.startswith(b"II*\x00") or header.startswith(b"MM\x00*")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid TIFF image: Missing TIFF byte-order signature",
            )


def detect_initial_type(filename: str) -> str:
    """Heuristic file type identification for initial status."""
    fn = filename.lower()
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
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


def _build_evidence_response(ev: EvidenceFile) -> EvidenceResponse:
    q_data: Dict[str, Any] = {}
    exif_data: Optional[Dict[str, Any]] = None
    try:
        q_data = json.loads(ev.quality_json or "{}")
    except Exception:
        q_data = {}
    try:
        exif_parsed = json.loads(ev.exif_json or "{}")
        if exif_parsed:
            exif_data = exif_parsed
    except Exception:
        exif_data = None

    return EvidenceResponse(
        id=ev.id,
        case_id=ev.case_id,
        original_name=ev.original_name,
        file_size=ev.file_size,
        sha256=ev.sha256,
        detected_type=ev.detected_type,
        status=ev.status,
        uploaded_at=ev.created_at.isoformat(),
        perceptual_hash=ev.perceptual_hash,
        is_handwritten=bool(ev.is_handwritten),
        quality_reason=q_data.get("quality_reason"),
        duplicate_of_evidence_id=q_data.get("duplicate_of_evidence_id"),
        exif=exif_data,
    )


@router.post("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
@router.post("/cases/{case_id}/evidence/", response_model=List[EvidenceResponse])
async def upload_evidence(
    case_id: str,
    files: List[UploadFile] = File(...),
    is_handwritten: bool = Query(False, description="Optional officer flag marking uploaded image/PDF as handwritten"),
    evidence_password: Optional[str] = Query(None, description="Optional one-time password for encrypted PDF evidence (never stored)"),
    x_evidence_password: Optional[str] = Header(None, alias="X-Evidence-Password"),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """
    Upload multipart evidence files into case repository.
    Validates extension, size limit (from config), and magic bytes.
    Stream-computes SHA-256 while saving to read-only path.
    Sanitizes filenames to prevent path traversal.
    Safely unpacks ZIP archives (zip bomb defense) into discrete evidence records.
    Runs defusedxml security inspection on DOCX files.
    Enforces password authentication on encrypted PDFs without storing passwords.
    Invokes pluggable malware scanner before storage.
    For images, extracts EXIF ('as reported by file'), perceptual hash, duplicate check, and OpenCV quality gate.
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    allowed_map = get_allowed_extensions_map()
    ocr_cfg = get_extraction_config().get("ocr", {})
    phash_max_dist = int(ocr_cfg.get("phash_duplicate_max_dist", 4))
    scanner = get_malware_scanner()
    effective_pdf_pwd = evidence_password or x_evidence_password

    upload_base = Path(settings.UPLOAD_DIR) / case.id
    upload_base.mkdir(parents=True, exist_ok=True)

    results = []

    for file in files:
        raw_name = Path(file.filename).name if file.filename else "evidence_file.bin"
        original_name = sanitize_filename(raw_name)
        ext = Path(original_name).suffix.lower()

        if ext not in allowed_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not supported. Allowed: {list(allowed_map.keys())}",
            )

        max_limit = allowed_map[ext]
        file_uuid = str(uuid.uuid4())
        target_path = upload_base / f"{file_uuid}_{original_name}"

        hasher = hashlib.sha256()
        total_size = 0
        first_chunk = True

        # Stream save and compute hash
        try:
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
                            detail=f"File '{original_name}' exceeds size limit of {max_limit // (1024 * 1024)} MB",
                        )

                    if first_chunk:
                        validate_magic_bytes(ext, chunk)
                        first_chunk = False

                    hasher.update(chunk)
                    out_f.write(chunk)
        except Exception:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            raise

        computed_sha = hasher.hexdigest()

        # 1. Safe ZIP Archive Handling (Bulk unpack with zip-bomb & traversal defense)
        if ext == ".zip":
            try:
                unpacked = safe_unpack_zip(
                    zip_path=target_path,
                    target_dir=upload_base,
                    allowed_extensions=allowed_map,
                )
            finally:
                target_path.unlink(missing_ok=True)

            for item in unpacked:
                inner_path = Path(item["stored_path"])
                inner_ext = item["extension"]

                # Malware check on inner file
                scan_res = scanner.scan(inner_path)
                if not scan_res.clean:
                    inner_path.unlink(missing_ok=True)
                    record_audit_log(
                        db=db,
                        user_id=current_user.id,
                        action="malware_quarantine",
                        case_id=case.id,
                        object_type="evidence_file",
                        object_id=item["id"],
                        details={"threat": scan_res.threat_name, "filename": item["original_name"]},
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"MALWARE_DETECTED: Threat '{scan_res.threat_name}' detected in archive entry '{item['original_name']}'",
                    )

                inner_status = "uploaded"
                inner_phash: Optional[str] = None
                inner_exif: Dict[str, Any] = {}
                inner_quality: Dict[str, Any] = {}

                if inner_ext in IMAGE_EXTENSIONS:
                    try:
                        with Image.open(inner_path) as pil_img:
                            meta = extract_exif_and_hashes(pil_img)
                            inner_phash = meta["perceptual_hash"]
                            inner_exif = meta["exif"]
                            q_res = assess_image_quality(pil_img)
                            inner_quality = {
                                "passed": q_res["passed"],
                                "status": q_res["status"],
                                "quality_reason": q_res["reason"],
                                "metrics": q_res["metrics"],
                            }
                            if not q_res["passed"]:
                                inner_status = "needs_better_image"
                    except Exception as exc:
                        inner_status = "needs_better_image"
                        inner_quality = {
                            "passed": False,
                            "status": "needs_better_image",
                            "quality_reason": f"Image decode failure: {str(exc)}",
                        }

                try:
                    os.chmod(inner_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
                except Exception:
                    pass

                ev_entry = EvidenceFile(
                    id=item["id"],
                    case_id=case.id,
                    original_name=item["original_name"],
                    stored_path=item["stored_path"],
                    sha256=item["sha256"],
                    file_size=item["file_size"],
                    detected_type=detect_initial_type(item["original_name"]),
                    status=inner_status,
                    uploader_id=current_user.id,
                    perceptual_hash=inner_phash,
                    exif_json=json.dumps(inner_exif, default=str),
                    is_handwritten=bool(is_handwritten),
                    quality_json=json.dumps(inner_quality, default=str),
                    created_at=datetime.utcnow(),
                )
                db.add(ev_entry)
                db.commit()
                db.refresh(ev_entry)

                record_audit_log(
                    db=db,
                    user_id=current_user.id,
                    action="upload_evidence",
                    case_id=case.id,
                    object_type="evidence_file",
                    object_id=ev_entry.id,
                    details={
                        "original_name": item["original_name"],
                        "sha256": item["sha256"],
                        "size_bytes": item["file_size"],
                        "status": inner_status,
                        "source_archive": original_name,
                    },
                )
                results.append(_build_evidence_response(ev_entry))

            continue

        # 2. Malware Scanner Hook on raw file
        scan_res = scanner.scan(target_path)
        if not scan_res.clean:
            target_path.unlink(missing_ok=True)
            record_audit_log(
                db=db,
                user_id=current_user.id,
                action="malware_quarantine",
                case_id=case.id,
                object_type="evidence_file",
                object_id=file_uuid,
                details={"threat": scan_res.threat_name, "filename": original_name},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MALWARE_DETECTED: File rejected due to detected threat: {scan_res.threat_name}",
            )

        # 3. Format-specific security inspections
        if ext == ".docx":
            try:
                safe_inspect_docx(target_path)
            except Exception:
                target_path.unlink(missing_ok=True)
                raise
        elif ext == ".pdf":
            try:
                doc_handle, pdf_meta = safe_inspect_pdf(target_path, password=effective_pdf_pwd)
                doc_handle.close()
            except Exception:
                target_path.unlink(missing_ok=True)
                raise

        ev_status = "uploaded"
        phash_val: Optional[str] = None
        exif_dict: Dict[str, Any] = {}
        quality_payload: Dict[str, Any] = {}

        if ext in IMAGE_EXTENSIONS:
            try:
                with Image.open(target_path) as pil_img:
                    meta = extract_exif_and_hashes(pil_img)
                    phash_val = meta["perceptual_hash"]
                    exif_dict = meta["exif"]
                    q_res = assess_image_quality(pil_img)
                    quality_payload = {
                        "passed": q_res["passed"],
                        "status": q_res["status"],
                        "quality_reason": q_res["reason"],
                        "metrics": q_res["metrics"],
                    }
                    if not q_res["passed"]:
                        ev_status = "needs_better_image"

                    # Check perceptual-hash duplicate across existing images in the same case
                    if phash_val:
                        existing_imgs = (
                            db.query(EvidenceFile)
                            .filter(
                                EvidenceFile.case_id == case.id,
                                EvidenceFile.perceptual_hash.isnot(None),
                            )
                            .all()
                        )
                        for ex_ev in existing_imgs:
                            dist = phash_distance(phash_val, ex_ev.perceptual_hash)
                            if dist <= phash_max_dist:
                                quality_payload["duplicate_of_evidence_id"] = ex_ev.id
                                quality_payload["phash_distance"] = dist
                                break
            except Exception as exc:
                ev_status = "needs_better_image"
                quality_payload = {
                    "passed": False,
                    "status": "needs_better_image",
                    "quality_reason": f"Image could not be decoded for quality inspection: {str(exc)}",
                }

        # Set read-only permissions
        try:
            os.chmod(target_path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
        except Exception:
            pass

        evidence_entry = EvidenceFile(
            id=file_uuid,
            case_id=case.id,
            original_name=original_name,
            stored_path=str(target_path.resolve()),
            sha256=computed_sha,
            file_size=total_size,
            detected_type=detect_initial_type(original_name),
            status=ev_status,
            uploader_id=current_user.id,
            perceptual_hash=phash_val,
            exif_json=json.dumps(exif_dict, default=str),
            is_handwritten=bool(is_handwritten),
            quality_json=json.dumps(quality_payload, default=str),
            created_at=datetime.utcnow(),
        )
        db.add(evidence_entry)
        db.commit()
        db.refresh(evidence_entry)

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
                "size_bytes": total_size,
                "status": ev_status,
                "perceptual_hash": phash_val,
            },
        )

        results.append(_build_evidence_response(evidence_entry))

    return results


@router.get("/cases/{case_id}/evidence", response_model=List[EvidenceResponse])
def list_case_evidence(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    db: Session = Depends(get_db),
):
    """List all evidence files uploaded to the specified case."""
    files = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.case_id == case.id)
        .order_by(EvidenceFile.created_at.desc())
        .all()
    )
    return [_build_evidence_response(f) for f in files]


@router.post("/evidence/{evidence_id}/verify", response_model=VerifyEvidenceResponse)
def verify_evidence_integrity(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Recompute SHA-256 of the stored evidence file on disk.
    Confirms bit-for-bit integrity against the stored hash in the database.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    file_path = Path(ev.stored_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence file missing on disk at {ev.stored_path}",
        )

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)

    computed_sha = hasher.hexdigest()
    is_valid = computed_sha == ev.sha256

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
            "computed_hash": computed_sha,
        },
    )

    return VerifyEvidenceResponse(
        valid=is_valid,
        evidence_id=ev.id,
        original_name=ev.original_name,
        stored_hash=ev.sha256,
        computed_hash=computed_sha,
    )


@router.delete("/evidence/{evidence_id}")
def delete_evidence(
    evidence_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Remove evidence file from disk and database with full audit logging."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    case = get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    file_path = Path(ev.stored_path)
    if file_path.exists():
        try:
            os.chmod(file_path, stat.S_IWRITE | stat.S_IREAD)
            file_path.unlink()
        except Exception:
            pass

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_evidence",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={"original_name": ev.original_name, "sha256": ev.sha256},
    )

    db.delete(ev)
    db.commit()

    return {"status": "deleted", "id": evidence_id, "case_id": case.id}
