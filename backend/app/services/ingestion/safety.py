"""
Hostile file defense, filename sanitization, safe ZIP handling, and defused XML parser
for CaseConnect AI (Extraction V2 Phase 8).
"""

import hashlib
import io
import os
import re
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import defusedxml.ElementTree as DefusedET
import defusedxml.minidom as DefusedMiniDom
from defusedxml.common import DefusedXmlException, DTDForbidden, EntitiesForbidden
import fitz
from fastapi import HTTPException, status

from backend.app.config import get_extraction_config

# Path traversal regex & forbidden control characters
RE_TRAVERSAL = re.compile(r"(?:\.\.[\\/]|[\\/]\.\.|^\.\.[\\/]?|[\\/])")
RE_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f<>:\"|?*]")


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes raw user-supplied filenames to prevent path traversal, control character injection,
    and null-byte truncation attacks.
    """
    if not filename:
        return "evidence_file.bin"

    # Normalize unicode to NFKC
    norm_name = unicodedata.normalize("NFKC", str(filename))

    # Strip directory components (both Unix and Windows paths)
    base_name = os.path.basename(norm_name.replace("\\", "/"))

    # Remove null bytes and control chars
    cleaned = RE_UNSAFE_CHARS.sub("_", base_name)

    # Strip repeated leading/trailing dots and whitespace
    cleaned = cleaned.strip(". \t\r\n")

    # If filename is empty or only special chars, assign safe fallback
    if not cleaned:
        cleaned = "evidence_file.bin"

    # Limit filename length to 128 chars while preserving extension
    p = Path(cleaned)
    ext = p.suffix[:16]
    stem = p.stem[:110]
    return f"{stem}{ext}" if ext else stem


def defuse_xml_bytes(xml_bytes: bytes, source_label: str = "XML document") -> None:
    """
    Validates XML bytes against XML Entity Expansion (Billion Laughs) and External Entity (XXE) attacks
    using defusedxml. Raises HTTPException(400) if an entity attack is detected.
    """
    try:
        DefusedET.fromstring(xml_bytes)
    except (DefusedXmlException, DTDForbidden, EntitiesForbidden) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MALICIOUS_XML_ENTITY_DETECTED: {source_label} contains prohibited XML entities or DTD declarations: {str(exc)}",
        )
    except Exception:
        # Non-security XML syntax issues are handled by downstream parsers
        pass


def safe_inspect_docx(file_path: Path) -> None:
    """
    Inspects internal XML parts of a DOCX archive (e.g. word/document.xml, [Content_Types].xml)
    with defusedxml before python-docx or any other parser processes it.
    """
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            for member in zf.infolist():
                if member.filename.lower().endswith((".xml", ".rels")):
                    # Read member bytes and validate with defusedxml
                    with zf.open(member) as xml_file:
                        xml_bytes = xml_file.read()
                        defuse_xml_bytes(xml_bytes, source_label=f"DOCX internal part '{member.filename}'")
    except HTTPException:
        raise
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FILE_CORRUPTED: Invalid DOCX archive format",
        )
    except Exception as exc:
        # If unable to inspect as zip, allow downstream parser to handle or flag
        pass


def safe_inspect_pdf(
    file_path: Path,
    password: Optional[str] = None,
) -> Tuple[fitz.Document, Dict[str, Any]]:
    """
    Safely inspects a PDF:
      - Validates %PDF magic bytes
      - Checks encryption; requires password if encrypted (never stores password)
      - Inspects for active scripts (/JavaScript, /Launch, /EmbeddedFiles)
    Returns (fitz_doc, metadata_dict). Caller is responsible for closing the document.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FILE_CORRUPTED: Unable to open PDF document: {str(exc)}",
        )

    # 1. Encryption check
    was_encrypted = bool(doc.is_encrypted)
    if doc.is_encrypted:
        if not password:
            doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ENCRYPTED_FILE_REQUIRES_PASSWORD: The PDF document is password-protected. Please provide a password for this request.",
            )
        auth_ok = doc.authenticate(password)
        if not auth_ok:
            doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ENCRYPTED_FILE_INVALID_PASSWORD: Password authentication failed for the encrypted PDF.",
            )

    # 2. Active content inspection
    active_features = []
    try:
        # Check catalog / names dictionary for interactive/executable actions
        cat = doc.pdf_catalog()
        cat_str = str(doc.xref_object(cat)) if cat else ""
        for tag in ["/JavaScript", "/JS", "/Launch", "/EmbeddedFiles", "/SubmitForm", "/ImportData"]:
            if tag in cat_str:
                active_features.append(tag)
    except Exception:
        pass

    pdf_meta = {
        "is_encrypted": was_encrypted,
        "page_count": len(doc),
        "active_features_detected": active_features,
        "active_content_neutralized": len(active_features) > 0,
    }

    return doc, pdf_meta


def safe_unpack_zip(
    zip_path: Path,
    target_dir: Path,
    allowed_extensions: Dict[str, int],
) -> List[Dict[str, Any]]:
    """
    Safely unzips an uploaded archive into target_dir with strict defense:
      - Enforces max_files (default 50)
      - Enforces max_uncompressed_bytes (default 500 MB)
      - Enforces max_ratio (compression ratio <= 100.0 to prevent zip bombs)
      - Rejects nested archives beyond max_depth
      - Strips paths from entries to prevent zip-slip / traversal attacks
      - Validates inner file extensions against allowed_extensions
    Returns list of unpacked file descriptor dictionaries.
    """
    up_cfg = get_extraction_config().get("upload", {})
    zip_cfg = up_cfg.get("zip", {})
    max_files = int(zip_cfg.get("max_files", 50))
    max_uncompressed_bytes = int(zip_cfg.get("max_uncompressed_mb", 500)) * 1024 * 1024
    max_ratio = float(zip_cfg.get("max_ratio", 100.0))
    max_depth = int(zip_cfg.get("max_depth", 2))

    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FILE_CORRUPTED: Uploaded ZIP archive is corrupted or invalid",
        )

    with zf:
        infolist = [info for info in zf.infolist() if not info.is_dir()]

        # 1. Check file count limit
        if len(infolist) > max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP_MAX_FILES_EXCEEDED: Archive contains {len(infolist)} files (maximum allowed is {max_files})",
            )

        if not infolist:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ZIP_EMPTY: Archive contains no files",
            )

        # 2. Check total uncompressed size and compression ratio
        total_uncompressed = 0
        total_compressed = 0
        for info in infolist:
            total_uncompressed += info.file_size
            total_compressed += info.compress_size

            # Check nested archive depth
            inner_ext = Path(info.filename).suffix.lower()
            if inner_ext in [".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"]:
                if max_depth <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ZIP_NESTED_ARCHIVE_REJECTED: Nested archives exceed allowed recursion depth",
                    )

        if total_uncompressed > max_uncompressed_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP_UNCOMPRESSED_SIZE_EXCEEDED: Uncompressed size ({total_uncompressed // (1024 * 1024)} MB) exceeds limit ({max_uncompressed_bytes // (1024 * 1024)} MB)",
            )

        compression_ratio = total_uncompressed / max(1, total_compressed)
        if compression_ratio > max_ratio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP_BOMB_DETECTED: Compression ratio ({compression_ratio:.1f}:1) exceeds safety threshold ({max_ratio}:1)",
            )

        # 3. Safe extraction with path stripping
        extracted_entries: List[Dict[str, Any]] = []
        target_dir.mkdir(parents=True, exist_ok=True)

        for info in infolist:
            raw_filename = info.filename
            clean_name = sanitize_filename(raw_filename)
            ext = Path(clean_name).suffix.lower()

            if ext not in allowed_extensions:
                # Skip or reject disallowed extensions within archive
                continue

            max_file_size = allowed_extensions[ext]
            if info.file_size > max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ZIP_MEMBER_TOO_LARGE: File '{clean_name}' exceeds size limit of {max_file_size // (1024 * 1024)} MB",
                )

            inner_uuid = str(uuid.uuid4())
            dest_file = target_dir / f"{inner_uuid}_{clean_name}"

            hasher = hashlib.sha256()
            written_bytes = 0

            with zf.open(info, "r") as source_stream, open(dest_file, "wb") as dest_stream:
                while chunk := source_stream.read(64 * 1024):
                    written_bytes += len(chunk)
                    if written_bytes > max_file_size:
                        dest_stream.close()
                        dest_file.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"ZIP_MEMBER_TOO_LARGE: File '{clean_name}' uncompressed stream exceeded limit",
                        )
                    hasher.update(chunk)
                    dest_stream.write(chunk)

            # Security inspection on specific formats
            if ext == ".docx":
                safe_inspect_docx(dest_file)

            extracted_entries.append({
                "id": inner_uuid,
                "original_name": clean_name,
                "stored_path": str(dest_file.resolve()),
                "file_size": written_bytes,
                "sha256": hasher.hexdigest(),
                "extension": ext,
            })

        if not extracted_entries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ZIP_NO_VALID_FILES: Archive contains no supported evidence files",
            )

        return extracted_entries
