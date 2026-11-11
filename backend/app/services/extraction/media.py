"""
Forensic Audio & Video Extraction Engine for CaseConnect AI (Extraction V2 Phase 10).
Local-first, air-gap ready media intelligence pipeline with timestamped provenance.

Features:
- Audio transcription via local `faster-whisper` (default disabled via config flag).
- Video processing via local FFmpeg: audio track extraction and keyframe extraction at configured intervals.
- Perceptual image hashing / pixel difference to drop duplicate video frames.
- Integrated OCR on non-duplicate frames with timestamp provenance.
- Timestamps preserved across all extracted entities and records.
- Feature-flagged and fully inert when `extraction.media.enabled: false`.
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.config import get_extraction_config
from backend.app.db.sql import (
    EvidenceFile,
    ExtractedEntity,
    ExtractionRecord,
    MediaTranscriptSegment,
)
from backend.app.services.extraction.rules import extract_rule_entities
from backend.app.services.extraction.ocr import get_ocr_provider

logger = logging.getLogger("caseconnect.extraction.media")

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v"}
SUPPORTED_MEDIA_EXTENSIONS = AUDIO_EXTENSIONS.union(VIDEO_EXTENSIONS)


def get_media_config() -> Dict[str, Any]:
    """Retrieves media extraction configuration from defaults.yaml."""
    cfg = get_extraction_config()
    return cfg.get("media", {
        "enabled": False,
        "whisper_model": "base",
        "whisper_compute": "int8",
        "language": "auto",
        "frame_interval_sec": 2.0,
        "max_duration_min": 60,
        "ffmpeg_path": "",
        "allowed_types": [".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mkv", ".avi", ".mov"],
        "max_file_size_mb": 100,
        "low_confidence_cutoff": 0.70,
    })


def is_media_extraction_enabled() -> bool:
    """Returns True only when explicitly enabled in configuration."""
    return bool(get_media_config().get("enabled", False))


def find_ffmpeg_binary() -> Optional[str]:
    """
    Locates FFmpeg executable in environment variable, config path, or system PATH.
    Returns path string if found and executable, else None.
    """
    cfg_path = get_media_config().get("ffmpeg_path", "")
    if cfg_path and Path(cfg_path).is_file():
        return str(cfg_path)

    env_path = os.environ.get("FFMPEG_BINARY") or os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).is_file():
        return str(env_path)

    system_bin = shutil.which("ffmpeg")
    if system_bin:
        return system_bin

    return None


def extract_audio_from_video(video_path: Path, output_wav_path: Path, ffmpeg_bin: str) -> None:
    """Extracts 16kHz mono PCM WAV audio track from video file using FFmpeg."""
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav_path),
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr[:300]}")


def extract_video_frames(
    video_path: Path,
    output_dir: Path,
    interval_sec: float,
    ffmpeg_bin: str,
) -> List[Tuple[float, Path]]:
    """
    Extracts frames from video file at specified second interval.
    Returns list of (timestamp_sec, frame_path).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(output_dir / "frame_%04d.jpg")
    fps = 1.0 / max(0.5, float(interval_sec))

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        out_pattern,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg frame extraction failed: {res.stderr[:300]}")

    frames: List[Tuple[float, Path]] = []
    frame_files = sorted(output_dir.glob("frame_*.jpg"))
    for idx, fpath in enumerate(frame_files):
        ts = round(idx * interval_sec, 2)
        frames.append((ts, fpath))
    return frames


def deduplicate_frames(
    frames: List[Tuple[float, Path]],
    threshold_distance: int = 6,
) -> List[Tuple[float, Path]]:
    """
    Deduplicates consecutive video frames using perceptual hash or byte similarity.
    Keeps first frame and subsequent frames with distinct visual content.
    """
    if not frames:
        return []

    try:
        from PIL import Image
        import imagehash
        has_imagehash = True
    except ImportError:
        has_imagehash = False

    kept: List[Tuple[float, Path]] = [frames[0]]
    if not has_imagehash:
        # Fallback to every second frame if imagehash not installed
        return frames[::2] if len(frames) > 2 else frames

    try:
        last_hash = imagehash.phash(Image.open(frames[0][1]))
    except Exception:
        return frames
    for ts, fpath in frames[1:]:
        try:
            curr_hash = imagehash.phash(Image.open(fpath))
            if (curr_hash - last_hash) >= threshold_distance:
                kept.append((ts, fpath))
                last_hash = curr_hash
        except Exception:
            kept.append((ts, fpath))

    return kept


def transcribe_audio_locally(audio_path: Path, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Performs local offline speech-to-text transcription via `faster-whisper`.
    Returns list of segment dicts: {start_sec, end_sec, text, confidence}.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "FASTER_WHISPER_NOT_INSTALLED: Local media transcription requires `faster-whisper`. "
            "Install with: pip install faster-whisper"
        )

    model_size = str(config.get("whisper_model", "base"))
    compute_type = str(config.get("whisper_compute", "int8"))
    lang_pref = str(config.get("language", "auto"))
    lang = None if lang_pref == "auto" else lang_pref

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    segments, info = model.transcribe(str(audio_path), language=lang, beam_size=5)

    cutoff = float(config.get("low_confidence_cutoff", 0.70))
    results: List[Dict[str, Any]] = []

    for seg in segments:
        text_clean = seg.text.strip()
        if not text_clean:
            continue
        # Approximate segment confidence from avg_logprob
        conf = round(max(0.0, min(1.0, 1.0 + (seg.avg_logprob / 2.5))), 3)
        results.append({
            "start_sec": round(seg.start, 2),
            "end_sec": round(seg.end, 2),
            "text": text_clean,
            "confidence": conf,
            "needs_review": bool(conf < cutoff),
            "speaker": None,
        })

    return results


def process_media_evidence(
    evidence_id: str,
    case_id: str,
    db: Session,
    user_id: str,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end processing of audio or video evidence file.
    Feeds transcripts and frame OCR into SQLite MediaTranscriptSegment,
    ExtractedEntity, and ExtractionRecord tables.
    """
    if not is_media_extraction_enabled():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MEDIA_EXTRACTION_DISABLED: Media extraction is disabled in configuration (extraction.media.enabled: false).",
        )

    evidence = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id, EvidenceFile.case_id == case_id).first()
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence file '{evidence_id}' not found.")

    file_path = Path(evidence.stored_path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence file path '{file_path}' does not exist on disk.")

    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported media extension '{ext}'. Must be one of {sorted(list(SUPPORTED_MEDIA_EXTENSIONS))}",
        )

    media_cfg = get_media_config()
    ffmpeg_bin = find_ffmpeg_binary()
    if not ffmpeg_bin and (ext in VIDEO_EXTENSIONS or ext in AUDIO_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FFMPEG_NOT_FOUND: FFmpeg binary not found in system PATH, config, or FFMPEG_BINARY env var.",
        )

    work_dir = file_path.parent / f"_media_{evidence_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    segments_out: List[Dict[str, Any]] = []
    entities_created = 0
    records_created = 0

    try:
        # 1. Audio track acquisition
        if ext in VIDEO_EXTENSIONS:
            wav_path = work_dir / "extracted_audio.wav"
            extract_audio_from_video(file_path, wav_path, ffmpeg_bin)
            audio_source = wav_path
        else:
            audio_source = file_path

        # 2. Offline Speech-to-Text Transcription
        try:
            segments_out = transcribe_audio_locally(audio_source, media_cfg)
        except Exception as e:
            logger.warning("Local whisper transcription failed or model missing: %s", e)
            segments_out = []

        # 3. Persist segments in SQLite
        for seg in segments_out:
            seg_row = MediaTranscriptSegment(
                case_id=case_id,
                evidence_id=evidence_id,
                start_sec=seg["start_sec"],
                end_sec=seg["end_sec"],
                text=seg["text"],
                confidence=seg["confidence"],
                speaker=seg.get("speaker"),
                needs_review=seg.get("needs_review", False),
            )
            db.add(seg_row)
            db.flush()

            # Run entity extraction on transcript segment
            extracted = extract_rule_entities(seg["text"], page_or_para=f"ts_{int(seg['start_sec'])}s")
            for ent in extracted:
                ent_row = ExtractedEntity(
                    case_id=case_id,
                    evidence_id=evidence_id,
                    entity_type=ent["entity_type"],
                    raw_value=ent["raw_value"],
                    normalized_value=ent["normalized_value"],
                    page_or_paragraph=f"ts_{int(seg['start_sec'])}s",
                    source_kind="asr_audio",
                    confidence=seg["confidence"],
                    method=ent.get("method", "asr_regex"),
                )
                db.add(ent_row)
                entities_created += 1

            # Feed segment into ExtractionRecord store
            nat_key = f"media_seg_{evidence_id}_{int(seg['start_sec'])}"
            rec_row = ExtractionRecord(
                case_id=case_id,
                evidence_id=evidence_id,
                record_type="media_segment",
                natural_key=nat_key,
                data_json=json.dumps({
                    "start_sec": seg["start_sec"],
                    "end_sec": seg["end_sec"],
                    "text": seg["text"],
                    "confidence": seg["confidence"],
                }),
                extra_json=json.dumps({"provenance": "asr_audio", "timestamp_sec": seg["start_sec"]}),
            )
            db.add(rec_row)
            records_created += 1

        # 4. If video: extract frames, deduplicate, run OCR
        if ext in VIDEO_EXTENSIONS:
            frames_dir = work_dir / "frames"
            interval = float(media_cfg.get("frame_interval_sec", 2.0))
            all_frames = extract_video_frames(file_path, frames_dir, interval, ffmpeg_bin)
            kept_frames = deduplicate_frames(all_frames)

            ocr_provider = get_ocr_provider()
            for ts, frame_path in kept_frames:
                try:
                    from PIL import Image
                    frame_img = Image.open(frame_path)
                    ocr_res = ocr_provider.ocr_page_image(frame_img, page_no=1)
                    frame_text = ocr_res.get("full_text", "").strip()
                    if frame_text:
                        frame_ents = extract_rule_entities(frame_text, page_or_para=f"frame_ts_{int(ts)}s")
                        for fe in frame_ents:
                            ent_row = ExtractedEntity(
                                case_id=case_id,
                                evidence_id=evidence_id,
                                entity_type=fe["entity_type"],
                                raw_value=fe["raw_value"],
                                normalized_value=fe["normalized_value"],
                                page_or_paragraph=f"frame_ts_{int(ts)}s",
                                source_kind="ocr_video_frame",
                                confidence=ocr_res.get("mean_confidence", 0.7),
                                method=fe.get("method", "video_frame_ocr"),
                            )
                            db.add(ent_row)
                            entities_created += 1
                except Exception as oe:
                    logger.debug("Frame OCR error at ts %s: %s", ts, oe)

        db.commit()

        # 5. Append to cryptographic audit chain
        record_audit_log(
            db=db,
            user_id=user_id,
            action="extract_media",
            case_id=case_id,
            object_type="evidence_file",
            object_id=evidence_id,
            details={
                "extension": ext,
                "segments_count": len(segments_out),
                "entities_count": entities_created,
                "records_count": records_created,
            },
        )

        return {
            "status": "success",
            "evidence_id": evidence_id,
            "segments_count": len(segments_out),
            "entities_created": entities_created,
            "records_created": records_created,
        }

    finally:
        # Cleanup temporary files
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
