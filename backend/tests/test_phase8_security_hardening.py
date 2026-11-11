"""
Phase 8 Comprehensive Verification Suite — Security Hardening, Hostile File Defense,
PII Masking, Job Management & Logging Hygiene.
"""

import io
import json
import logging
import zipfile
from pathlib import Path

import fitz
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.auth.security import hash_password
from backend.app.config import get_extractor_version
from backend.app.audit.logging_sanitizer import (
    SensitiveDataSanitizerFilter,
    sanitize_log_message,
)
from backend.app.db.sql import AuditLog, Case, EvidenceFile, ExtractedEntity, Job, SessionLocal, User
from backend.app.main import app
from backend.app.services.extraction.masking import (
    can_user_reveal_pii,
    mask_aadhaar,
    mask_account,
    mask_extracted_entity_dict,
    mask_pan,
    mask_phone,
    mask_record_dict,
)
from backend.app.services.ingestion.jobs import (
    acquire_case_job_lock,
    cancel_job,
    is_job_cancelled,
    release_case_job_lock,
    reset_job_for_retry,
)
from backend.app.services.ingestion.malware import (
    EICAR_BYTE_SUBSTRING,
    MockMalwareScanner,
    NoOpMalwareScanner,
)
from backend.app.services.ingestion.safety import (
    defuse_xml_bytes,
    safe_inspect_docx,
    safe_inspect_pdf,
    safe_unpack_zip,
    sanitize_filename,
)
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _setup_p8_auth(username: str, role: str = "investigator"):
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
    db.close()
    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return u, headers


# ---------------------------------------------------------------------------
# 1. Filename Sanitization & Path Traversal Defense
# ---------------------------------------------------------------------------

def test_filename_sanitization_traversal():
    """Confirms path traversal sequences, null bytes, and unsafe characters are neutralized."""
    assert sanitize_filename("../../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("evidence\x00file.csv") == "evidence_file.csv"
    assert sanitize_filename("case<>:\"|?*data.xlsx") == "case_______data.xlsx"
    assert sanitize_filename("") == "evidence_file.bin"
    assert sanitize_filename("   .hidden_file.txt   ") == "hidden_file.txt"


# ---------------------------------------------------------------------------
# 2. Hostile Archive Defense (Zip Bomb, Ratio Limit, Max Files)
# ---------------------------------------------------------------------------

def test_zip_bomb_compression_ratio_rejected(tmp_path: Path):
    """
    Generates a high-compression synthetic zip bomb (10 MB of zeros compressing into < 15 KB).
    Compression ratio is ~700:1, which exceeds the max_ratio threshold of 100.0.
    """
    bomb_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zero_payload = b"\x00" * (10 * 1024 * 1024)
        zf.writestr("zero_flood.csv", zero_payload)

    allowed_map = {".csv": 200 * 1024 * 1024}
    with pytest.raises(HTTPException) as exc_info:
        safe_unpack_zip(
            zip_path=bomb_path,
            target_dir=tmp_path / "unpacked",
            allowed_extensions=allowed_map,
        )
    assert exc_info.value.status_code == 400
    assert "ZIP_BOMB_DETECTED" in exc_info.value.detail


def test_zip_max_files_exceeded_rejected(tmp_path: Path):
    """Generates an archive with 60 files exceeding the default max_files limit of 50."""
    too_many_path = tmp_path / "too_many.zip"
    with zipfile.ZipFile(too_many_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for idx in range(60):
            zf.writestr(f"item_{idx}.txt", f"Sample line {idx}\n".encode("utf-8"))

    allowed_map = {".txt": 20 * 1024 * 1024}
    with pytest.raises(HTTPException) as exc_info:
        safe_unpack_zip(
            zip_path=too_many_path,
            target_dir=tmp_path / "unpacked",
            allowed_extensions=allowed_map,
        )
    assert exc_info.value.status_code == 400
    assert "ZIP_MAX_FILES_EXCEEDED" in exc_info.value.detail


def test_zip_inner_path_traversal_stripped(tmp_path: Path):
    """
    Confirms that entries inside a zip containing path traversal components (zip-slip)
    have their paths stripped and unpack safely into target_dir.
    """
    slip_zip = tmp_path / "slip.zip"
    with zipfile.ZipFile(slip_zip, "w") as zf:
        zf.writestr("../../escape_attempt.txt", b"malicious content")

    allowed_map = {".txt": 20 * 1024 * 1024}
    unpack_dir = tmp_path / "safe_unpacked"
    entries = safe_unpack_zip(
        zip_path=slip_zip,
        target_dir=unpack_dir,
        allowed_extensions=allowed_map,
    )
    assert len(entries) == 1
    extracted_path = Path(entries[0]["stored_path"])
    assert extracted_path.parent.resolve() == unpack_dir.resolve()
    assert extracted_path.name.endswith("escape_attempt.txt")


# ---------------------------------------------------------------------------
# 3. XML Entity Attack (XXE & Billion Laughs) Defense via defusedxml
# ---------------------------------------------------------------------------

def test_xml_entity_expansion_rejected():
    """Detects and rejects XML Entity Expansion (Billion Laughs) attacks."""
    evil_xml = b"""<?xml version="1.0"?>
    <!DOCTYPE lolz [
      <!ENTITY lol "lol">
      <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
      <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    ]>
    <root>&lol3;</root>
    """
    with pytest.raises(HTTPException) as exc_info:
        defuse_xml_bytes(evil_xml, source_label="Test XML")
    assert exc_info.value.status_code == 400
    assert "MALICIOUS_XML_ENTITY_DETECTED" in exc_info.value.detail


def test_docx_with_malicious_xml_rejected(tmp_path: Path):
    """Verifies that a crafted DOCX archive containing XXE is safely rejected."""
    evil_docx = tmp_path / "evil_statement.docx"
    evil_xml = b"""<?xml version="1.0"?>
    <!DOCTYPE test [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>
    </w:document>
    """
    with zipfile.ZipFile(evil_docx, "w") as zf:
        zf.writestr("word/document.xml", evil_xml)
        zf.writestr("[Content_Types].xml", b"<Types></Types>")

    with pytest.raises(HTTPException) as exc_info:
        safe_inspect_docx(evil_docx)
    assert exc_info.value.status_code == 400
    assert "MALICIOUS_XML_ENTITY_DETECTED" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 4. Encrypted PDF Safety & Authentication
# ---------------------------------------------------------------------------

def test_encrypted_pdf_handling(tmp_path: Path):
    """
    Generates a password-protected PDF. Confirms:
      - Opening without password raises ENCRYPTED_FILE_REQUIRES_PASSWORD.
      - Opening with invalid password raises ENCRYPTED_FILE_INVALID_PASSWORD.
      - Opening with correct password succeeds and active features are inspected.
    """
    pdf_path = tmp_path / "protected_dossier.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Confidential investigation dossier content")

    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )
    encrypt_meth = fitz.PDF_ENCRYPT_AES_256
    doc.save(
        str(pdf_path),
        encryption=encrypt_meth,
        owner_pw="OwnerSecret99",
        user_pw="OfficerToken123",
        permissions=perm,
    )
    doc.close()

    # 1. No password provided -> rejected with clear message
    with pytest.raises(HTTPException) as exc_no_pw:
        safe_inspect_pdf(pdf_path, password=None)
    assert exc_no_pw.value.status_code == 400
    assert "ENCRYPTED_FILE_REQUIRES_PASSWORD" in exc_no_pw.value.detail

    # 2. Wrong password provided -> rejected
    with pytest.raises(HTTPException) as exc_wrong_pw:
        safe_inspect_pdf(pdf_path, password="WrongPassword!")
    assert exc_wrong_pw.value.status_code == 400
    assert "ENCRYPTED_FILE_INVALID_PASSWORD" in exc_wrong_pw.value.detail

    # 3. Correct password provided -> authenticated cleanly
    opened_doc, meta = safe_inspect_pdf(pdf_path, password="OfficerToken123")
    assert meta["is_encrypted"] is True
    assert len(opened_doc) == 1
    opened_doc.close()


# ---------------------------------------------------------------------------
# 5. Pluggable Malware Scanner Hook
# ---------------------------------------------------------------------------

def test_malware_scanner_eicar_detection(tmp_path: Path):
    """Confirms MockMalwareScanner detects standard test pattern."""
    clean_file = tmp_path / "clean.csv"
    clean_file.write_bytes(b"col1,col2\n10,20\n")

    infected_file = tmp_path / "eicar_sample.com"
    infected_file.write_bytes(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + EICAR_BYTE_SUBSTRING + b"!$H+H*")

    scanner = MockMalwareScanner()
    res_clean = scanner.scan(clean_file)
    assert res_clean.clean is True

    res_infected = scanner.scan(infected_file)
    assert res_infected.clean is False
    assert "EICAR" in res_infected.threat_name


# ---------------------------------------------------------------------------
# 6. PII Masking & Serializer Responses (Viewer vs Investigator)
# ---------------------------------------------------------------------------

def test_pii_masking_helpers():
    """Unit checks for last-4 masking across phone, account, PAN, and Aadhaar."""
    gen = SyntheticDataGenerator(seed=801)
    phone = gen.generate_phone()
    acct = gen.generate_account()

    m_phone = mask_phone(phone)
    assert m_phone.endswith(phone[-4:])
    assert "X" in m_phone
    assert phone[:4] not in m_phone

    m_acct = mask_account(acct)
    assert m_acct.endswith(acct[-4:])
    assert "X" in m_acct

    m_aadhaar = mask_aadhaar("9999 8888 7777")
    assert m_aadhaar == "XXXX-XXXX-7777"

    m_pan = mask_pan("ABCDE1234F")
    assert m_pan.endswith("234F")
    assert "X" in m_pan


def test_pii_masking_serializer_entities():
    """Verifies ExtractedEntity dictionary serializer applies masking unless reveal=True."""
    entity_payload = {
        "id": "ee-101",
        "entity_type": "PHONE",
        "raw_value": "+91 9876543210",
        "normalized_value": "9876543210",
    }
    masked = mask_extracted_entity_dict(entity_payload, reveal=False)
    assert masked["normalized_value"] == "XXXXXX3210"
    assert masked["raw_value"] == "XXXXXXXX3210"
    assert masked["is_masked"] is True

    unmasked = mask_extracted_entity_dict(entity_payload, reveal=True)
    assert unmasked["normalized_value"] == "9876543210"
    assert unmasked.get("is_masked") is not True


def test_pii_masking_serializer_records():
    """Verifies ExtractionRecord dictionary serializer applies masking."""
    rec_payload = {
        "id": "rec-202",
        "record_type": "transaction",
        "natural_key": "TXN9876543210",
        "data": {
            "account_number": "123456789012",
            "amount_paise": 500000,
            "phone": "9876543210",
        },
    }
    masked_rec = mask_record_dict(rec_payload, reveal=False)
    assert masked_rec["data"]["account_number"] == "XXXXXXXX9012"
    assert masked_rec["data"]["phone"] == "XXXXXX3210"
    assert masked_rec["data"]["amount_paise"] == 500000


# ---------------------------------------------------------------------------
# 7. Audited PII Reveal Endpoint (POST /cases/{case_id}/reveal)
# ---------------------------------------------------------------------------

def test_reveal_endpoint_viewer_forbidden():
    """Confirms viewer role is strictly forbidden (HTTP 403) from revealing unmasked PII."""
    gen = SyntheticDataGenerator(seed=802)
    case_title = f"Case {gen.generate_name()} Lead"

    _, admin_hdr = _setup_p8_auth("admin_p8_user", role="admin")
    viewer_user, viewer_hdr = _setup_p8_auth("viewer_p8_user", role="viewer")

    res_case = client.post("/cases", json={"title": case_title}, headers=admin_hdr)
    assert res_case.status_code == 200
    case_id = res_case.json()["id"]

    # Assign viewer to the case so case-level check passes
    client.post(
        f"/cases/{case_id}/members",
        json={"user_id": viewer_user.id, "role": "viewer"},
        headers=admin_hdr,
    )

    res_reveal = client.post(
        f"/cases/{case_id}/reveal",
        json={
            "object_type": "phone",
            "object_id": "9876543210",
            "justification": "Checking suspect phone lead",
        },
        headers=viewer_hdr,
    )
    assert res_reveal.status_code == 403
    assert "ACCESS_DENIED" in res_reveal.json()["detail"]


def test_reveal_endpoint_investigator_audited():
    """
    Confirms investigator role can reveal unmasked PII and that a cryptographic
    audit_log entry is immutably linked in SQLite.
    """
    gen = SyntheticDataGenerator(seed=803)
    case_title = f"Case {gen.generate_name()} Investigation"
    _, inv_hdr = _setup_p8_auth("inv_p8_user", role="investigator")

    res_case = client.post("/cases", json={"title": case_title}, headers=inv_hdr)
    assert res_case.status_code == 200
    case_id = res_case.json()["id"]

    # 1. Missing justification rejected with HTTP 400
    res_bad = client.post(
        f"/cases/{case_id}/reveal",
        json={"object_type": "phone", "object_id": "9876543210", "justification": ""},
        headers=inv_hdr,
    )
    assert res_bad.status_code == 400
    assert "JUSTIFICATION_REQUIRED" in res_bad.json()["detail"]

    # 2. Valid reveal call
    justification_text = "Verifying target phone against subscriber database under BSA Section 63"
    res_reveal = client.post(
        f"/cases/{case_id}/reveal",
        json={
            "object_type": "phone",
            "object_id": "9876543210",
            "justification": justification_text,
        },
        headers=inv_hdr,
    )
    assert res_reveal.status_code == 200
    payload = res_reveal.json()
    assert payload["ok"] is True
    assert payload["unmasked_value"] == "9876543210"
    assert payload["audited"] is True

    # 3. Assert cryptographic audit_log entry exists
    db = SessionLocal()
    try:
        audit_entry = (
            db.query(AuditLog)
            .filter(AuditLog.case_id == case_id, AuditLog.action == "reveal_pii")
            .order_by(AuditLog.ts.desc())
            .first()
        )
        assert audit_entry is not None
        details = json.loads(audit_entry.details_json)
        assert details["justification"] == justification_text
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 8. Jobs Concurrency Lock, Cancellation & Retry
# ---------------------------------------------------------------------------

def test_case_job_concurrency_lock():
    """Confirms per-case concurrency lock prevents multiple concurrent heavy jobs."""
    case_id = "test-case-lock-001"
    job1_id = "job-lock-1"
    job2_id = "job-lock-2"

    acquired1, _ = acquire_case_job_lock(case_id, job1_id, "ingest")
    assert acquired1 is True

    acquired2, conflict_id = acquire_case_job_lock(case_id, job2_id, "ingest")
    assert acquired2 is False
    assert conflict_id == job1_id

    release_case_job_lock(case_id, job1_id)
    acquired3, _ = acquire_case_job_lock(case_id, job2_id, "ingest")
    assert acquired3 is True
    release_case_job_lock(case_id, job2_id)


def test_job_cooperative_cancellation_and_retry():
    """Tests job cancel and retry lifecycle with status transitions and reason codes."""
    db = SessionLocal()
    try:
        case_id = "case-job-test-01"
        job = Job(
            case_id=case_id,
            job_type="ingest",
            status="running",
            progress=45,
            steps_json=json.dumps(["Step 1 complete", "Step 2 in progress"]),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # 1. Cancel running job
        canceled_job = cancel_job(
            db=db,
            job_id=job.id,
            user_id="officer-test",
            reason="Officer halted processing",
        )
        assert canceled_job.status == "cancelled"
        assert canceled_job.reason_code == "CANCELLED_BY_OFFICER"
        assert is_job_cancelled(db, job.id) is True

        # 2. Cannot cancel already cancelled job
        with pytest.raises(HTTPException):
            cancel_job(db=db, job_id=job.id, user_id="officer-test")

        # 3. Retry cancelled job
        retried_job = reset_job_for_retry(db=db, job_id=job.id, user_id="officer-test")
        assert retried_job.status == "queued"
        assert retried_job.progress == 0
        assert retried_job.reason_code is None
        assert is_job_cancelled(db, job.id) is False
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 9. Logging Hygiene (Grepping Captured Logs for Zero PII Leakage)
# ---------------------------------------------------------------------------

def test_logging_hygiene_scrubber_unit():
    """Unit test checking raw PII patterns are replaced with masked snippets in log messages."""
    raw_log = "Officer inspected MSISDN 9876543210 and account 123456789012 with Aadhaar 1111 2222 3333 and PAN ABCDE1234F"
    scrubbed = sanitize_log_message(raw_log)

    assert "9876543210" not in scrubbed
    assert "[PHONE:XXXXXX3210]" in scrubbed

    assert "123456789012" not in scrubbed
    assert "[ACCOUNT:XXXX9012]" in scrubbed

    assert "1111 2222 3333" not in scrubbed
    assert "[AADHAAR:XXXX-XXXX-3333]" in scrubbed

    assert "ABCDE1234F" not in scrubbed
    assert "[PAN:XXXXXX34F]" in scrubbed


def test_logging_filter_stream_hygiene(caplog):
    """
    Emits log records through Python's standard logging system with the SensitiveDataSanitizerFilter
    and asserts zero unmasked PII appears in the captured stream.
    """
    logger = logging.getLogger("backend.test_security")
    sanitizer = SensitiveDataSanitizerFilter()
    logger.addFilter(sanitizer)

    phone_sample = "9876543210"
    acct_sample = "123456789012"
    pan_sample = "ABCDE1234F"

    with caplog.at_level(logging.INFO):
        logger.info("Processing target caller %s for account %s with PAN %s", phone_sample, acct_sample, pan_sample)

    captured_text = caplog.text
    assert phone_sample not in captured_text
    assert acct_sample not in captured_text
    assert pan_sample not in captured_text
    assert "[PHONE:XXXXXX3210]" in captured_text


# ---------------------------------------------------------------------------
# 10. Centralized Extractor Version Provenance
# ---------------------------------------------------------------------------

def test_extractor_version_string_structure():
    """Confirms get_extractor_version() returns deterministic provenance string."""
    v_str = get_extractor_version()
    assert v_str.startswith("v2.0.0+cfg.")
    assert "fitz." in v_str
    assert "pn." in v_str
    assert "pyd." in v_str
    assert "sa." in v_str
