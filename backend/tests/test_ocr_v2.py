import json
from pathlib import Path
import socket
from typing import Any, Dict, List, Optional
from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.auth.security import hash_password
from backend.app.db.sql import (
    AuditLog,
    CaseSetting,
    Entity,
    EvidenceFile,
    EvidencePage,
    ExtractionRecord,
    FieldClaim,
    GoldenField,
    SessionLocal,
    User,
)
from backend.app.main import app
from backend.app.services.extraction.ocr.base import (
    OcrEngineUnavailableError,
    OcrProvider,
    TesseractProvider,
    VisionProvider,
    set_ocr_provider_override,
)
from backend.app.services.extraction.ocr.preprocess import (
    assess_image_quality,
    extract_exif_and_hashes,
    preprocess_for_ocr,
)
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


class DeterministicTestOcrProvider(OcrProvider):
    """
    Deterministic local OCR provider for testing the full OCR pipeline, word bounding boxes,
    Devanagari digit conversion, handwriting confidence caps, and officer corrections
    independently of whether the external Tesseract Windows installer has been run.
    """

    engine_name = "deterministic_test_ocr"
    engine_version = "2.0-test"

    def __init__(self, words: List[Dict[str, Any]]):
        self._words = [dict(w) for w in words]

    def recognize(
        self,
        image: Image.Image,
        page: int = 1,
        languages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        out = []
        for idx, w in enumerate(self._words, start=1):
            c = dict(w)
            c["page"] = page
            c["word_id"] = f"p{page}_w{idx}"
            out.append(c)
        return out


def _get_user_and_token(username: str, role: str = "investigator") -> tuple[str, str]:
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(
            username=username,
            password_hash=hash_password("Pass1234!"),
            role=role,
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    uid = u.id
    db.close()

    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    assert res.status_code == 200
    return uid, res.json()["access_token"]


def _create_case(token: str, title: str) -> str:
    res = client.post(
        "/cases",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": title, "description": "Phase 5 OCR Suite", "priority": "high"},
    )
    assert res.status_code == 200
    return res.json()["id"]


def test_quality_gate_blurry_vs_sharp_and_rotated_preprocess(tmp_path):
    gen = SyntheticDataGenerator(seed=501)
    suite = gen.write_phase5_ocr_suite(tmp_path)

    with Image.open(suite["blurry_image"]) as blurry_pil:
        q_blur = assess_image_quality(blurry_pil)
        assert q_blur["passed"] is False
        assert q_blur["status"] == "needs_better_image"
        assert q_blur["reason"] is not None
        assert "blur" in q_blur["reason"].lower() or "contrast" in q_blur["reason"].lower()

    with Image.open(suite["sharp_image"]) as sharp_pil:
        q_sharp = assess_image_quality(sharp_pil, dpi_hint=250)
        assert q_sharp["passed"] is True
        assert q_sharp["status"] == "ready"
        prep_img, prep_params = preprocess_for_ocr(sharp_pil, q_sharp["metrics"])
        assert prep_img.size == sharp_pil.size
        assert "adaptive_block_size" in prep_params

    with Image.open(suite["rotated_image"]) as rot_pil:
        q_rot = assess_image_quality(rot_pil, dpi_hint=250)
        assert q_rot["passed"] is True
        _, rot_params = preprocess_for_ocr(rot_pil, q_rot["metrics"])
        assert "deskew_applied_deg" in rot_params


def test_missing_tesseract_binary_produces_friendly_actionable_error(tmp_path, monkeypatch):
    gen = SyntheticDataGenerator(seed=502)
    suite = gen.write_phase5_ocr_suite(tmp_path)

    # Ensure no override provider is active and point TESSERACT_CMD to a non-existent path
    set_ocr_provider_override(None)
    monkeypatch.setenv("TESSERACT_CMD", str(tmp_path / "non_existent_tesseract.exe"))
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr(TesseractProvider, "_resolve_tesseract_binary", staticmethod(lambda: None))

    provider = TesseractProvider()
    with Image.open(suite["sharp_image"]) as pil_img:
        with pytest.raises(OcrEngineUnavailableError) as exc_info:
            provider.recognize(pil_img, page=1)
        assert "Tesseract OCR binary not found" in str(exc_info.value)
        assert exc_info.value.reason_code == "ocr_binary_missing"


def test_upload_blurry_image_stores_file_hash_and_needs_better_image_status(tmp_path):
    gen = SyntheticDataGenerator(seed=503)
    suite = gen.write_phase5_ocr_suite(tmp_path)
    _, token = _get_user_and_token("p5_inv_upload", "investigator")
    cid = _create_case(token, "Phase 5 Upload Quality Gate")
    headers = {"Authorization": f"Bearer {token}"}

    blurry_bytes = Path(suite["blurry_image"]).read_bytes()
    res = client.post(
        f"/cases/{cid}/evidence",
        headers=headers,
        files={"files": ("blurry_fir.png", blurry_bytes, "image/png")},
    )
    assert res.status_code == 200
    ev_item = res.json()[0]
    assert ev_item["status"] == "needs_better_image"
    assert ev_item["quality_reason"] is not None
    assert len(ev_item["sha256"]) == 64
    assert ev_item["perceptual_hash"] is not None
    assert ev_item["exif"]["disclaimer"] == "as reported by file"

    # Uploading a duplicate image in the same case detects perceptual-hash duplicate
    sharp_bytes = Path(suite["sharp_image"]).read_bytes()
    r1 = client.post(
        f"/cases/{cid}/evidence",
        headers=headers,
        files={"files": ("sharp_1.png", sharp_bytes, "image/png")},
    )
    assert r1.status_code == 200
    ev1_id = r1.json()[0]["id"]
    assert r1.json()[0]["status"] == "uploaded"

    r2 = client.post(
        f"/cases/{cid}/evidence",
        headers=headers,
        files={"files": ("sharp_duplicate.png", sharp_bytes, "image/png")},
    )
    assert r2.status_code == 200
    assert r2.json()[0]["duplicate_of_evidence_id"] == ev1_id


def test_mixed_pdf_routing_word_bboxes_corrections_and_no_network_calls(tmp_path, monkeypatch):
    gen = SyntheticDataGenerator(seed=504)
    suite = gen.write_phase5_ocr_suite(tmp_path)
    _, token = _get_user_and_token("p5_inv_pipeline", "investigator")
    cid = _create_case(token, "Phase 5 Mixed PDF & Corrections")
    headers = {"Authorization": f"Bearer {token}"}

    # Guard against any outbound network socket creation during extraction
    real_connect = socket.socket.connect

    def _forbid_external_socket(self, address):
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError(f"Forbidden outbound network connection attempted to {address}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", _forbid_external_socket)

    test_provider = DeterministicTestOcrProvider(suite["synthetic_words"])
    set_ocr_provider_override(test_provider)

    try:
        # 1. Upload mixed 2-page PDF (Page 1 = digital text layer, Page 2 = scanned image)
        pdf_bytes = Path(suite["mixed_pdf"]).read_bytes()
        up_res = client.post(
            f"/cases/{cid}/evidence",
            headers=headers,
            files={"files": ("mixed_fir.pdf", pdf_bytes, "application/pdf")},
        )
        assert up_res.status_code == 200
        ev_id = up_res.json()[0]["id"]

        # 2. Run extraction
        ext_res = client.post(f"/evidence/{ev_id}/extract", headers=headers)
        assert ext_res.status_code == 200
        ext_json = ext_res.json()
        assert ext_json["status"] == "completed"
        assert ext_json["pages_count"] == 2
        assert ext_json["total_extracted"] >= 4

        # 3. Verify GET /evidence/{id}/pages shows Page 1 as text_layer_pdf and Page 2 as ocr_printed
        pages_res = client.get(f"/evidence/{ev_id}/pages", headers=headers)
        assert pages_res.status_code == 200
        pages_list = pages_res.json()["pages"]
        assert len(pages_list) == 2
        assert pages_list[0]["page_no"] == 1
        assert pages_list[0]["source_kind"] == "text_layer_pdf"
        assert pages_list[0]["engine_name"] == "pymupdf"
        assert pages_list[1]["page_no"] == 2
        assert pages_list[1]["source_kind"] == "ocr_printed"
        assert pages_list[1]["word_count"] == len(suite["synthetic_words"])

        # 4. Verify GET /evidence/{id}/pages/2/ocr returns words with bbox, and entities with bbox + Devanagari phone normalized
        ocr_p2 = client.get(f"/evidence/{ev_id}/pages/2/ocr", headers=headers)
        assert ocr_p2.status_code == 200
        p2_data = ocr_p2.json()
        assert len(p2_data["words"]) == len(suite["synthetic_words"])
        p2_entities = p2_data["entities"]
        phone_ent = next((e for e in p2_entities if e["entity_type"] == "PHONE"), None)
        assert phone_ent is not None
        assert phone_ent["normalized_value"] == suite["phone_ascii"]
        assert phone_ent["bbox"] is not None
        assert len(phone_ent["bbox"]) == 4

        # 5. Officer submits an OCR word correction on Page 2
        new_phone = gen.generate_phone()
        dev_word = next(w for w in p2_data["words"] if suite["phone_devanagari"] in w["text"])
        corr_res = client.post(
            f"/evidence/{ev_id}/pages/2/corrections",
            headers=headers,
            json={
                "word_id": dev_word["word_id"],
                "corrected_text": new_phone,
                "note": "Corrected slightly smudged digit on physical FIR copy",
            },
        )
        assert corr_res.status_code == 200
        corr_json = corr_res.json()
        # Original raw_text is NEVER overwritten
        assert suite["phone_devanagari"] in corr_json["raw_text"]
        assert new_phone in corr_json["corrected_text"]

        # Verify officer claim is locked in GoldenField (highest trust)
        db = SessionLocal()
        rec = (
            db.query(ExtractionRecord)
            .filter(
                ExtractionRecord.case_id == cid,
                ExtractionRecord.record_type == "entity",
                ExtractionRecord.source_kind == "officer",
            )
            .first()
        )
        assert rec is not None
        gf = (
            db.query(GoldenField)
            .filter(GoldenField.subject_id == rec.id, GoldenField.field_name == "canonical_id")
            .first()
        )
        assert gf is not None
        assert gf.locked is True
        assert gf.selected_by == "officer"

        audit_entry = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == cid, AuditLog.action == "OCR_CORRECTION")
            .first()
        )
        assert audit_entry is not None
        db.close()
    finally:
        set_ocr_provider_override(None)


def test_handwritten_fir_photo_never_auto_accepts_and_caps_confidence(tmp_path):
    gen = SyntheticDataGenerator(seed=505)
    suite = gen.write_phase5_ocr_suite(tmp_path)
    _, token = _get_user_and_token("p5_inv_hw", "investigator")
    cid = _create_case(token, "Phase 5 Handwritten Review Enforcement")
    headers = {"Authorization": f"Bearer {token}"}

    test_provider = DeterministicTestOcrProvider(suite["synthetic_words"])
    set_ocr_provider_override(test_provider)

    try:
        hw_bytes = Path(suite["handwritten_image"]).read_bytes()
        up_res = client.post(
            f"/cases/{cid}/evidence?is_handwritten=true",
            headers=headers,
            files={"files": ("handwritten_fir.png", hw_bytes, "image/png")},
        )
        assert up_res.status_code == 200
        ev_id = up_res.json()[0]["id"]
        assert up_res.json()[0]["is_handwritten"] is True

        ext_res = client.post(f"/evidence/{ev_id}/extract", headers=headers)
        assert ext_res.status_code == 200

        # Check extracted entities: all must have source_kind='ocr_handwritten', confidence <= 0.65, status='pending_review'
        list_res = client.get(f"/cases/{cid}/extracted?evidence_id={ev_id}", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert len(items) > 0
        for item in items:
            assert item["source_kind"] == "ocr_handwritten"
            assert item["confidence"] <= 0.65
            assert item["status"] == "pending_review"

        # Calling bulk approve-all (even with threshold=0.1) MUST NOT auto-approve handwritten entities
        bulk_res = client.post(f"/cases/{cid}/extracted/approve-all?threshold=0.1", headers=headers)
        assert bulk_res.status_code == 200
        assert bulk_res.json()["approved_count"] == 0

        # Verify zero active Entities were auto-staged in the graph `entities` table
        db = SessionLocal()
        active_ents = db.query(Entity).filter(Entity.case_id == cid, Entity.is_active.is_(True)).count()
        db.close()
        assert active_ents == 0
    finally:
        set_ocr_provider_override(None)


def test_vision_provider_disabled_by_default_and_requires_case_consent(monkeypatch):
    uid, token = _get_user_and_token("p5_inv_vision", "investigator")
    cid = _create_case(token, "Phase 5 Vision Consent Gate")
    vp = VisionProvider()
    dummy_img = Image.new("RGB", (200, 100), color=(255, 255, 255))

    db = SessionLocal()
    try:
        # 1. Default config has vision_provider.enabled = False -> raises PermissionError
        with pytest.raises(PermissionError, match="disabled by configuration"):
            vp.recognize_with_consent(db, cid, "ev-1", 1, uid, dummy_img)

        # 2. Even if enabled in config, missing per-case consent raises PermissionError
        monkeypatch.setattr(
            "backend.app.services.extraction.ocr.base.get_extraction_config",
            lambda: {"vision_provider": {"enabled": True, "require_case_consent": True}},
        )
        with pytest.raises(PermissionError, match="explicit officer consent"):
            vp.recognize_with_consent(db, cid, "ev-1", 1, uid, dummy_img)

        # 3. Grant per-case consent in CaseSetting -> succeeds and writes VISION_PROVIDER_CALL to audit_log
        db.add(CaseSetting(case_id=cid, settings_json=json.dumps({"vision_cloud_consent": True})))
        db.commit()

        res = vp.recognize_with_consent(db, cid, "ev-1", 1, uid, dummy_img)
        assert res["source_kind"] == "vision_cloud"

        audit_row = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == cid, AuditLog.action == "VISION_PROVIDER_CALL")
            .first()
        )
        assert audit_row is not None
    finally:
        db.close()

