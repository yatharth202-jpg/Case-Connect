import json
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.sql import (
    SessionLocal, User, Case, EvidenceFile, ExtractedEntity, Entity, EntityLink
)
from backend.app.auth.security import hash_password
from backend.app.services.extraction.text import read_document_text
from backend.app.services.extraction.rules import extract_rule_entities
from backend.app.services.extraction.ner import (
    extract_ner_entities, extract_cooccurrence_relationships
)
from backend.app.services.extraction.pipeline import run_document_extraction

client = TestClient(app)

def get_token(username: str, role: str = "investigator") -> str:
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(username=username, password_hash=hash_password("Pass1234!"), role=role, is_active=True)
        db.add(u)
        db.commit()
    db.close()

    res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    return res.json()["access_token"]

def create_case(token: str, title: str) -> str:
    res = client.post("/cases", headers={"Authorization": f"Bearer {token}"}, json={"title": title, "priority": "high"})
    return res.json()["id"]

# ---------------------------------------------------------------------
# 1. Deterministic Rule Extraction & Phone Disambiguation
# ---------------------------------------------------------------------
def test_rule_extraction_phone_and_account_disambiguation():
    phone_digits = "98765" + "43210"
    account_digits = "91234" + "56789"

    # Standalone phone number
    text1 = f"Contact was established via mobile number +91 {phone_digits} on call."
    res1 = extract_rule_entities(text1, "Page 1")
    phones1 = [e for e in res1 if e["entity_type"] == "PHONE"]
    assert len(phones1) == 1
    assert phones1[0]["normalized_value"] == phone_digits
    assert phones1[0]["confidence"] == 0.95

    # 10-digit number following an account trigger keyword
    text2 = f"The victim was instructed to transfer money to beneficiary a/c {phone_digits} at state bank."
    res2 = extract_rule_entities(text2, "Page 1")
    accounts2 = [e for e in res2 if e["entity_type"] == "BANK_ACCOUNT"]
    phones2 = [e for e in res2 if e["entity_type"] == "PHONE"]
    assert len(accounts2) == 1
    assert accounts2[0]["normalized_value"] == phone_digits
    assert len(phones2) == 0

    # Account trigger keyword with 40-char context window
    text3 = f"Deposit funds into account no: {account_digits} immediately."
    res3 = extract_rule_entities(text3, "Page 1")
    accounts3 = [e for e in res3 if e["entity_type"] == "BANK_ACCOUNT"]
    assert len(accounts3) == 1
    assert accounts3[0]["normalized_value"] == account_digits

def test_rule_extraction_masked_account_suffix():
    masked_suffix = "7890"
    text = f"Payment notification showed card ending {masked_suffix} and account XXXXXX{masked_suffix}."
    res = extract_rule_entities(text, "Page 1")
    suffixes = [e for e in res if e["entity_type"] == "ACCOUNT_SUFFIX"]
    assert len(suffixes) >= 1
    for s in suffixes:
        assert s["confidence"] == 0.40
        assert s["normalized_value"] == f"ENDING_{masked_suffix}"

def test_rule_extraction_vehicle_amount_date_email_ip_upi_fir_ps():
    date_val = "15/08/" + "2024"
    text = (
        f"FIR No. 142/2024 registered at Police Station Cyber Crime, New Delhi. "
        f"Vehicle DL 01 AB 1234 was identified on date {date_val}. "
        f"Total fraudulent transaction was Rs. 2,50,000.00 transferred to upi test.user@oksbi. "
        f"Notification email was sent to officer.unitx@police.gov.in from IP 192.168.1.105."
    )
    res = extract_rule_entities(text, "Page 1")
    by_type = {e["entity_type"]: e for e in res}

    assert "FIR" in by_type
    assert by_type["FIR"]["normalized_value"] == "142/2024"
    assert by_type["FIR"]["confidence"] == 0.95

    assert "POLICE_STATION" in by_type
    assert "Cyber Crime" in by_type["POLICE_STATION"]["normalized_value"]

    assert "VEHICLE" in by_type
    assert by_type["VEHICLE"]["normalized_value"] == "DL01AB1234"

    assert "AMOUNT" in by_type
    assert by_type["AMOUNT"]["normalized_value"] == "25000000"

    assert "UPI" in by_type
    assert by_type["UPI"]["normalized_value"] == "test.user@oksbi"

    assert "EMAIL" in by_type
    assert by_type["EMAIL"]["normalized_value"] == "officer.unitx@police.gov.in"

    assert "IP" in by_type
    assert by_type["IP"]["normalized_value"] == "192.168.1.105"

# ---------------------------------------------------------------------
# 2. Document Reading: Scanned PDF & Devanagari Detection
# ---------------------------------------------------------------------
def test_read_document_text_plain_text(tmp_path):
    txt_file = tmp_path / "narrative.txt"
    txt_file.write_text("Paragraph one content.\n\nParagraph two content.", encoding="utf-8")
    doc = read_document_text(str(txt_file))

    assert doc["error"] is None
    assert len(doc["pages"]) == 2
    assert "Paragraph one content." in doc["full_text"]

def test_read_document_text_scanned_pdf_error(tmp_path):
    # Mock pdfplumber returning 0 selectable text
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_pdf.pages = [mock_page]

    dummy_pdf = tmp_path / "scanned_doc.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n")

    with patch("pdfplumber.open", return_value=MagicMock(__enter__=MagicMock(return_value=mock_pdf))):
        doc = read_document_text(str(dummy_pdf))
        assert doc["error"] == "failed: scanned PDF — OCR not supported in this version"
        assert len(doc["pages"]) == 0

def test_read_document_text_devanagari_warning(tmp_path):
    txt_file = tmp_path / "bilingual.txt"
    # Devanagari unicode characters
    txt_file.write_text("प्रथम सूचना रिपोर्ट FIR No. 99/2024 dated 12/04/2024", encoding="utf-8")
    doc = read_document_text(str(txt_file))

    assert doc["error"] is None
    assert doc["warning"] == "partially supported: Devanagari text ignored"

# ---------------------------------------------------------------------
# 3. NER and Co-occurrence Candidate Relationships
# ---------------------------------------------------------------------
def test_ner_person_extraction_and_rule_override():
    text = "Complainant Shri Ramesh Kumar reported to the police station."
    res = extract_ner_entities(text, "Page 1")
    persons = [e for e in res if e["entity_type"] == "PERSON"]
    assert len(persons) >= 1
    assert "ramesh kumar" in persons[0]["normalized_value"]

def test_cooccurrence_candidate_relationships():
    phone_digits = "98765" + "43210"
    account_digits = "112233" + "445566"
    text = (
        f"Shri Ramesh Kumar used mobile number +91 {phone_digits} for communication. "
        f"He was found to operate bank account {account_digits}."
    )

    entities = [
        {
            "entity_type": "PERSON",
            "raw_value": "Ramesh Kumar",
            "normalized_value": "ramesh kumar",
            "char_span_start": 5,
            "char_span_end": 17,
            "confidence": 0.70
        },
        {
            "entity_type": "PHONE",
            "raw_value": f"+91 {phone_digits}",
            "normalized_value": phone_digits,
            "char_span_start": 40,
            "char_span_end": 55,
            "confidence": 0.95
        },
        {
            "entity_type": "BANK_ACCOUNT",
            "raw_value": account_digits,
            "normalized_value": account_digits,
            "char_span_start": 105,
            "char_span_end": 117,
            "confidence": 0.90
        }
    ]

    rels = extract_cooccurrence_relationships(text, entities, "Page 1")
    assert len(rels) >= 1

    rel_types = set()
    for r in rels:
        assert r["entity_type"] == "RELATIONSHIP"
        data = json.loads(r["normalized_value"])
        rel_types.add(data["relationship_type"])

    assert "USES" in rel_types or "OWNS" in rel_types

# ---------------------------------------------------------------------
# 4. Pipeline Execution & Full Review Workflow via API
# ---------------------------------------------------------------------
def test_full_extraction_and_review_workflow(tmp_path):
    token = get_token("investigator_ext_1")
    case_id = create_case(token, "Extraction Full Pipeline Case")

    # 1. Setup a test evidence document
    phone_digits = "98765" + "43210"
    acc_digits = "554433" + "221100"
    doc_path = tmp_path / "fir_sample.txt"
    doc_path.write_text(
        f"FIRST INFORMATION REPORT\n"
        f"FIR No. 101/2024 registered at Police Station Connaught Place.\n\n"
        f"Complainant Shri Rajesh Sharma reported that an individual contacted him on mobile +91 {phone_digits}.\n"
        f"Funds were transferred to account no: {acc_digits}.\n"
        f"Vehicle HR 26 DK 8372 was seen leaving the spot.",
        encoding="utf-8"
    )

    db = SessionLocal()
    u1 = db.query(User).filter(User.username == "investigator_ext_1").first()
    ev = EvidenceFile(
        case_id=case_id,
        original_name="fir_sample.txt",
        stored_path=str(doc_path),
        file_size=doc_path.stat().st_size,
        sha256="dummy_hash_for_test_" + case_id[:16],
        detected_type="fir",
        uploader_id=u1.id,
        status="uploaded"
    )
    db.add(ev)
    db.commit()
    evidence_id = ev.id
    db.close()

    # 2. Trigger Extraction API: POST /evidence/{id}/extract
    ext_res = client.post(f"/evidence/{evidence_id}/extract", headers={"Authorization": f"Bearer {token}"})
    assert ext_res.status_code == 200
    ext_data = ext_res.json()
    assert ext_data["status"] == "completed"
    assert ext_data["total_extracted"] > 0

    # 3. List Extracted Entities: GET /cases/{id}/extracted
    list_res = client.get(f"/cases/{case_id}/extracted?status=pending_review", headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) > 0
    for it in items:
        assert it["status"] == "pending_review"

    # 4. Get Evidence Text with Highlight Spans: GET /evidence/{id}/text
    text_res = client.get(f"/evidence/{evidence_id}/text", headers={"Authorization": f"Bearer {token}"})
    assert text_res.status_code == 200
    t_data = text_res.json()
    assert len(t_data["pages"]) > 0
    assert len(t_data["entities"]) > 0

    # 5. Patch (Reject) an entity: PATCH /extracted/{id}
    first_item = items[0]
    rej_res = client.patch(
        f"/extracted/{first_item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "rejected"}
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"

    # 6. Patch (Approve) an entity: stages it into Entity table
    phone_item = next((it for it in items if it["entity_type"] == "PHONE"), None)
    assert phone_item is not None
    app_res = client.patch(
        f"/extracted/{phone_item['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "approved"}
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "approved"

    # Verify entity is committed to Entity table
    db = SessionLocal()
    staged = db.query(Entity).filter(
        Entity.case_id == case_id,
        Entity.label == "Phone",
        Entity.canonical_id == phone_item["normalized_value"]
    ).first()
    assert staged is not None
    assert staged.method == "document_nlp"
    db.close()

# ---------------------------------------------------------------------
# 5. FIR-Person Linking on Approval
# ---------------------------------------------------------------------
def test_fir_person_linking_on_approval(tmp_path):
    token = get_token("investigator_ext_2")
    case_id = create_case(token, "FIR Linking Test Case")

    doc_path = tmp_path / "fir_linking.txt"
    doc_path.write_text("FIR No. 888/2024. Complainant Shri Alok Verma was present.", encoding="utf-8")

    db = SessionLocal()
    u2 = db.query(User).filter(User.username == "investigator_ext_2").first()
    ev = EvidenceFile(
        case_id=case_id,
        original_name="fir_linking.txt",
        stored_path=str(doc_path),
        file_size=doc_path.stat().st_size,
        sha256="dummy_hash_fir_link_" + case_id[:16],
        detected_type="fir",
        uploader_id=u2.id,
        status="uploaded"
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id
    db.close()

    # Run extraction
    client.post(f"/evidence/{ev_id}/extract", headers={"Authorization": f"Bearer {token}"})

    db = SessionLocal()
    fir_item = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == ev_id, ExtractedEntity.entity_type == "FIR").first()
    person_item = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == ev_id, ExtractedEntity.entity_type == "PERSON").first()
    db.close()

    assert fir_item is not None
    assert person_item is not None

    # Approve FIR first
    client.patch(f"/extracted/{fir_item.id}", headers={"Authorization": f"Bearer {token}"}, json={"status": "approved"})

    # Approve Person second
    client.patch(f"/extracted/{person_item.id}", headers={"Authorization": f"Bearer {token}"}, json={"status": "approved"})

    # Check MENTIONED_IN link created in EntityLink
    db = SessionLocal()
    link = db.query(EntityLink).filter(
        EntityLink.case_id == case_id,
        EntityLink.relationship_type == "MENTIONED_IN"
    ).first()
    assert link is not None
    assert link.source_entity_id == person_item.normalized_value
    assert link.target_entity_id == fir_item.normalized_value
    db.close()

# ---------------------------------------------------------------------
# 6. Manual Officer Entity Entry & Bulk Approval
# ---------------------------------------------------------------------
def test_manual_officer_entry_and_bulk_approval(tmp_path):
    token = get_token("investigator_ext_3")
    case_id = create_case(token, "Manual Entry & Bulk Case")

    doc_path = tmp_path / "doc_bulk.txt"
    doc_path.write_text("A narrative document for testing.", encoding="utf-8")

    db = SessionLocal()
    u3 = db.query(User).filter(User.username == "investigator_ext_3").first()
    ev = EvidenceFile(
        case_id=case_id,
        original_name="doc_bulk.txt",
        stored_path=str(doc_path),
        file_size=doc_path.stat().st_size,
        sha256="dummy_hash_bulk_" + case_id[:16],
        detected_type="fir",
        uploader_id=u3.id,
        status="uploaded"
    )
    db.add(ev)
    db.commit()
    ev_id = ev.id
    db.close()

    # 1. Manual Entry: POST /cases/{id}/extracted
    manual_res = client.post(
        f"/cases/{case_id}/extracted",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "evidence_id": ev_id,
            "entity_type": "PERSON",
            "raw_value": "Officer Tagged Person",
            "normalized_value": "officer tagged person"
        }
    )
    assert manual_res.status_code == 200
    assert manual_res.json()["status"] == "created_and_approved"

    # Verify manual entity is immediately staged in Entity table
    db = SessionLocal()
    m_ent = db.query(Entity).filter(
        Entity.case_id == case_id,
        Entity.label == "Person",
        Entity.canonical_id == "officer tagged person"
    ).first()
    assert m_ent is not None
    assert m_ent.method == "document_nlp"

    # 2. Stage pending entities with varying confidence to test bulk approval threshold
    ee_high = ExtractedEntity(
        evidence_id=ev_id,
        case_id=case_id,
        entity_type="VEHICLE",
        raw_value="UP 16 AB 9999",
        normalized_value="UP16AB9999",
        page_or_paragraph="Paragraph 1",
        char_span_start=0,
        char_span_end=13,
        confidence=0.90,
        method="regex",
        status="pending_review"
    )
    ee_low = ExtractedEntity(
        evidence_id=ev_id,
        case_id=case_id,
        entity_type="ACCOUNT_SUFFIX",
        raw_value="ending 9999",
        normalized_value="ENDING_9999",
        page_or_paragraph="Paragraph 1",
        char_span_start=14,
        char_span_end=25,
        confidence=0.40,
        method="regex",
        status="pending_review"
    )
    db.add(ee_high)
    db.add(ee_low)
    db.commit()
    high_id = ee_high.id
    low_id = ee_low.id
    db.close()

    # 3. Bulk Approve with threshold 0.8: POST /cases/{id}/extracted/approve-all?threshold=0.8
    bulk_res = client.post(
        f"/cases/{case_id}/extracted/approve-all?threshold=0.8",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert bulk_res.status_code == 200
    bulk_data = bulk_res.json()
    assert bulk_data["status"] == "success"
    assert bulk_data["approved_count"] == 1

    # Verify high confidence entity is approved, low confidence remains pending
    db = SessionLocal()
    check_high = db.query(ExtractedEntity).filter(ExtractedEntity.id == high_id).first()
    check_low = db.query(ExtractedEntity).filter(ExtractedEntity.id == low_id).first()
    assert check_high.status == "approved"
    assert check_low.status == "pending_review"
    db.close()
