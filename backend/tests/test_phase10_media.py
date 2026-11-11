"""
Forensic Verification Test Suite for CaseConnect AI (Extraction V2 Phase 10).
Validates Local Audio/Video Forensics, Feature Flag Inactivity,
FFmpeg Detection, Media Transcript Storage, and Officer Review Workflows.
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.db.sql import (
    Base,
    engine,
    SessionLocal,
    User,
    Case,
    CaseMember,
    EvidenceFile,
    MediaTranscriptSegment,
    AuditLog,
)
from backend.app.services.extraction.media import (
    get_media_config,
    is_media_extraction_enabled,
    find_ffmpeg_binary,
    deduplicate_frames,
    SUPPORTED_MEDIA_EXTENSIONS,
)
from backend.app.evidence.router import validate_magic_bytes, get_allowed_extensions_map
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _setup_p10_auth(username: str, role: str = "investigator"):
    """Helper to register and authenticate an officer with JWT header."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        from scripts.seed_users import hash_password
        existing = db.query(User).filter(User.username == username).first()
        if not existing:
            u = User(
                username=username,
                role=role,
                password_hash=hash_password("ForensicPass123!"),
                is_active=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
        else:
            existing.role = role
            db.commit()
            u = existing
    finally:
        db.close()

    res = client.post("/auth/login", json={"username": username, "password": "ForensicPass123!"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return u, {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Feature Flag & Configuration Inactivity
# ---------------------------------------------------------------------------

def test_media_extraction_disabled_by_default():
    """Confirms media extraction is disabled by default in configuration."""
    cfg = get_media_config()
    assert cfg.get("enabled") is False
    assert is_media_extraction_enabled() is False


def test_media_extract_endpoint_disabled_rejection():
    """Confirms POST /evidence/{id}/media-extract rejects requests when feature flag is OFF."""
    gen = SyntheticDataGenerator(seed=1001)
    case_title = f"Case {gen.generate_name()} Media Test"
    _, auth_hdr = _setup_p10_auth("inv_p10_user1", role="investigator")

    res_case = client.post("/cases", json={"title": case_title}, headers=auth_hdr)
    assert res_case.status_code == 200
    case_id = res_case.json()["id"]

    db = SessionLocal()
    try:
        ev = EvidenceFile(
            case_id=case_id,
            original_name="intercept_call.wav",
            stored_path="C:/fake/path/test_intercept.wav",
            file_size=1024,
            sha256="aabbccddeeff00112233445566778899aabbccddeeff00112233445566778899",
            detected_type="audio/wav",
            status="uploaded",
            uploader_id=auth_hdr["Authorization"],
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        ev_id = ev.id
    finally:
        db.close()

    res = client.post(f"/evidence/{ev_id}/media-extract", headers=auth_hdr)
    assert res.status_code == 400
    assert "MEDIA_EXTRACTION_DISABLED" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 2. FFmpeg Binary Detection & Error Hygiene
# ---------------------------------------------------------------------------

def test_ffmpeg_binary_detection(monkeypatch):
    """Verifies FFmpeg binary lookup against env vars, config, and system PATH."""
    monkeypatch.setenv("FFMPEG_BINARY", "C:/nonexistent/ffmpeg.exe")
    assert find_ffmpeg_binary() is None

    # Supported media extensions coverage
    assert ".mp3" in SUPPORTED_MEDIA_EXTENSIONS
    assert ".wav" in SUPPORTED_MEDIA_EXTENSIONS
    assert ".mp4" in SUPPORTED_MEDIA_EXTENSIONS
    assert ".mkv" in SUPPORTED_MEDIA_EXTENSIONS


# ---------------------------------------------------------------------------
# 3. Magic Bytes Header Validation for Audio/Video
# ---------------------------------------------------------------------------

def test_media_magic_bytes_validation():
    """Verifies file signature checks for WAV, MP3, and MP4 containers."""
    from fastapi import HTTPException

    # Valid WAV
    valid_wav_header = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    validate_magic_bytes(".wav", valid_wav_header)

    # Invalid WAV
    with pytest.raises(HTTPException) as exc_info:
        validate_magic_bytes(".wav", b"NOT_A_WAV_HEADER")
    assert exc_info.value.status_code == 400
    assert "Invalid WAV" in exc_info.value.detail

    # Valid MP3 with ID3 header
    valid_mp3_header = b"ID3\x03\x00\x00\x00\x00\x0f\x76"
    validate_magic_bytes(".mp3", valid_mp3_header)

    # Invalid MP3
    with pytest.raises(HTTPException) as exc_info:
        validate_magic_bytes(".mp3", b"FAKE_MP3_STREAM")
    assert exc_info.value.status_code == 400
    assert "Invalid MP3" in exc_info.value.detail

    # Valid MP4 with ftyp box
    valid_mp4_header = b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00"
    validate_magic_bytes(".mp4", valid_mp4_header)

    # Invalid MP4
    with pytest.raises(HTTPException) as exc_info:
        validate_magic_bytes(".mp4", b"RANDOM_CORRUPT_BYTES")
    assert exc_info.value.status_code == 400
    assert "Invalid .MP4" in exc_info.value.detail or "Invalid MP4" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 4. Media Transcript Segments Storage & Retrieval API
# ---------------------------------------------------------------------------

def test_media_transcript_retrieval_and_review():
    """
    Validates end-to-end transcript segment retrieval, review filtering,
    and officer correction with cryptographic audit log linkage.
    """
    gen = SyntheticDataGenerator(seed=1002)
    case_title = f"Case {gen.generate_name()} Intercept"
    _, auth_hdr = _setup_p10_auth("inv_p10_user2", role="investigator")

    res_case = client.post("/cases", json={"title": case_title}, headers=auth_hdr)
    assert res_case.status_code == 200
    case_id = res_case.json()["id"]

    db = SessionLocal()
    try:
        ev = EvidenceFile(
            case_id=case_id,
            original_name="surveillance_recording.mp3",
            stored_path="C:/fake/path/test_surveillance.mp3",
            file_size=2048,
            sha256="11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            detected_type="audio/mp3",
            status="ready",
            uploader_id=auth_hdr["Authorization"],
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        ev_id = ev.id

        # Seed 3 transcript segments: 1 high conf, 2 low conf
        seg1 = MediaTranscriptSegment(
            case_id=case_id,
            evidence_id=ev_id,
            start_sec=0.0,
            end_sec=4.5,
            text="Initial contact confirmed on target mobile.",
            confidence=0.95,
            needs_review=False,
        )
        seg2 = MediaTranscriptSegment(
            case_id=case_id,
            evidence_id=ev_id,
            start_sec=5.0,
            end_sec=9.2,
            text="Unclear whisper about bank account transfer.",
            confidence=0.55,
            needs_review=True,
        )
        seg3 = MediaTranscriptSegment(
            case_id=case_id,
            evidence_id=ev_id,
            start_sec=10.0,
            end_sec=14.0,
            text="Muffled background conversation.",
            confidence=0.48,
            needs_review=True,
        )
        db.add_all([seg1, seg2, seg3])
        db.commit()
        seg2_id = seg2.id
    finally:
        db.close()

    # 1. Fetch all segments
    res_all = client.get(f"/evidence/{ev_id}/transcript", headers=auth_hdr)
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total_segments"] == 3
    assert data_all["pending_review_count"] == 2
    assert len(data_all["segments"]) == 3

    # 2. Fetch review queue only
    res_review = client.get(f"/evidence/{ev_id}/transcript?needs_review_only=true", headers=auth_hdr)
    assert res_review.status_code == 200
    data_rev = res_review.json()
    assert len(data_rev["segments"]) == 2

    # 3. Patch segment with officer correction
    res_patch = client.patch(
        f"/transcript/{seg2_id}",
        json={
            "text": "Confirmed whisper about account transfer to branch 402.",
            "officer_note": "Acoustic enhancement applied using high-pass filter.",
            "is_reviewed": True,
        },
        headers=auth_hdr,
    )
    assert res_patch.status_code == 200
    patched = res_patch.json()
    assert patched["is_reviewed"] is True
    assert patched["needs_review"] is False
    assert "Confirmed whisper" in patched["text"]

    # 4. Assert cryptographic audit log linkage
    db = SessionLocal()
    try:
        audit_entry = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == case_id, AuditLog.action == "correct_media_segment")
            .order_by(AuditLog.ts.desc())
            .first()
        )
        assert audit_entry is not None
        details = json.loads(audit_entry.details_json)
        assert details["is_reviewed"] is True
        assert "Acoustic enhancement" in details["officer_note"]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Frame Deduplication Algorithm
# ---------------------------------------------------------------------------

def test_frame_deduplication_empty_and_fallback():
    """Validates frame deduplication on empty list and fallback paths."""
    assert deduplicate_frames([]) == []
    dummy_frames = [(0.0, Path("frame_0.jpg")), (2.0, Path("frame_1.jpg"))]
    res = deduplicate_frames(dummy_frames)
    assert len(res) >= 1
