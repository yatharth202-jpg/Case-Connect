import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.auth.security import hash_password
from backend.app.db.sql import (
    Case,
    CaseMember,
    Entity,
    EntityLink,
    EvidenceFile,
    ExtractedEntity,
    ExtractionRecord,
    SessionLocal,
    User,
)
from backend.app.main import app
from backend.app.services.extraction.ner import (
    extract_cooccurrence_relationships,
    extract_ner_entities,
    normalize_indian_person_candidates,
)
from backend.app.services.extraction.rules import (
    compute_fir_completeness,
    extract_incident_facts,
    extract_legal_sections,
    extract_rule_entities,
    resolve_legal_section_mapping,
)
from scripts.generate_data import SyntheticDataGenerator

client = TestClient(app)


def _setup_user_and_case(username: str, title: str):
    db = SessionLocal()
    u = db.query(User).filter(User.username == username).first()
    if not u:
        u = User(
            username=username,
            password_hash=hash_password("Pass1234!"),
            role="investigator",
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)

    c = Case(title=title, description="Phase 6 FIR V2 test case", status="active", created_by=u.id)
    db.add(c)
    db.commit()
    db.refresh(c)

    cm = CaseMember(case_id=c.id, user_id=u.id, role="lead")
    db.add(cm)
    db.commit()
    case_id = c.id
    user_id = u.id
    db.close()

    login_res = client.post("/auth/login", json={"username": username, "password": "Pass1234!"})
    token = login_res.json()["access_token"]
    return token, user_id, case_id


def test_indian_name_candidates_never_auto_merge(tmp_path: Path):
    """
    Task 2: Indian-name normalization helper for honorifics/initials (Mohd./Md./Mohammad, Shri/Smt, initials)
    must ONLY produce candidate claims and must NEVER merge people automatically.
    """
    c1 = normalize_indian_person_candidates("Shri Mohd. Imran")
    c2 = normalize_indian_person_candidates("Mohammad Imran")
    c3 = normalize_indian_person_candidates("R. K. Sharma")

    assert c1["primary_normalized"] == "mohd imran"
    assert "mohammad imran" in c1["candidate_variants"]
    assert c2["primary_normalized"] == "mohammad imran"
    # Primary normalized keys remain distinct so they are never auto-merged!
    assert c1["primary_normalized"] != c2["primary_normalized"]

    assert c3["initials"] == ["R", "K"]
    assert c3["surname"] == "sharma"

    # Verify in full NER extraction on generated FIR containing both Mohd. Imran and Mohammad Imran
    gen = SyntheticDataGenerator(seed=601)
    suite = gen.write_phase6_fir_suite(tmp_path)
    fir_text = Path(suite["complete_fir_path"]).read_text(encoding="utf-8")

    ner_ents = extract_ner_entities(fir_text, "Page 1")
    person_norms = {e["normalized_value"]: e for e in ner_ents if e["entity_type"] == "PERSON"}

    assert "mohd imran" in person_norms
    assert "mohammad imran" in person_norms
    assert "mohammad imran" in person_norms["mohd imran"]["meta"].get("candidate_variants", [])


def test_role_aware_rules_and_kinship_residence_extraction(tmp_path: Path):
    """
    Task 1: Role-aware rules (complainant, accused, witness, police_officer, S/o, W/o, R/o)
    loaded from backend/config/reference/fir_patterns.yaml.
    """
    gen = SyntheticDataGenerator(seed=602)
    suite = gen.write_phase6_fir_suite(tmp_path)
    fir_text = Path(suite["complete_fir_path"]).read_text(encoding="utf-8")

    ner_ents = extract_ner_entities(fir_text, "Page 1")
    by_norm = {e["normalized_value"]: e for e in ner_ents if e["entity_type"] == "PERSON"}

    assert "rajesh verma" in by_norm
    assert by_norm["rajesh verma"]["role"] == "complainant"
    assert by_norm["rajesh verma"]["meta"].get("kinship_marker") == "S/O"
    assert "mohan verma" in by_norm["rajesh verma"]["meta"].get("relative_name", "").lower()
    assert "civil lines" in by_norm["rajesh verma"]["meta"].get("residence", "").lower()

    assert "mohd imran" in by_norm
    assert by_norm["mohd imran"]["role"] == "accused"
    assert by_norm["mohd imran"]["meta"].get("kinship_marker") == "S/O"

    assert "sunita devi" in by_norm
    assert by_norm["sunita devi"]["role"] == "witness"
    assert by_norm["sunita devi"]["meta"].get("kinship_marker") == "W/O"

    assert "vikram rathore" in by_norm
    assert by_norm["vikram rathore"]["role"] == "police_officer"

    # Assert valid non-zero spans for every person entity
    for p in by_norm.values():
        assert p["char_span_end"] > p["char_span_start"] >= 0


def test_sentence_relations_and_money_transfer_proposals(tmp_path: Path):
    """
    Task 3: Sentence-level relation extraction linking person-phone, person-account,
    person-vehicle, person-person kinship, and money transfers with from/to.
    Outputs are proposals (`status='pending_review'`) with method in {'regex', 'ner'} and spans.
    """
    gen = SyntheticDataGenerator(seed=603)
    suite = gen.write_phase6_fir_suite(tmp_path)
    fir_text = Path(suite["complete_fir_path"]).read_text(encoding="utf-8")

    rule_ents = extract_rule_entities(fir_text, "Page 1")
    ner_ents = extract_ner_entities(
        fir_text,
        "Page 1",
        existing_spans=[(e["char_span_start"], e["char_span_end"]) for e in rule_ents],
    )
    all_ents = rule_ents + ner_ents
    rels = extract_cooccurrence_relationships(fir_text, all_ents, "Page 1")

    assert len(rels) > 0
    parsed_rels = []
    for r in rels:
        assert r["entity_type"] == "RELATIONSHIP"
        assert r["status"] == "pending_review"
        assert r["method"] in ("regex", "ner")
        assert r["char_span_end"] > r["char_span_start"] >= 0
        payload = json.loads(r["normalized_value"])
        parsed_rels.append(payload)

    # Check person-phone ("mobile no. X of Mohd. Imran")
    assert any(
        pr["relationship_type"] == "USES"
        and pr["source"] == "mohd imran"
        and pr["target"] == suite["phone_1"]
        for pr in parsed_rels
    )

    # Check person-account ("account no. X held by Mohd. Imran")
    assert any(
        pr["relationship_type"] in ("OWNS", "OPERATES")
        and pr["source"] == "mohd imran"
        and pr["target"] == suite["account_1"]
        for pr in parsed_rels
    )

    # Check person-vehicle ("vehicle no. X driven by R. K. Sharma")
    assert any(
        pr["relationship_type"] == "DRIVES"
        and "sharma" in pr["source"]
        and pr["target"] == suite["vehicle_1"]
        for pr in parsed_rels
    )

    # Check kinship SON_OF / WIFE_OF
    assert any(pr["relationship_type"] == "SON_OF" and pr["source"] == "rajesh verma" for pr in parsed_rels)
    assert any(pr["relationship_type"] == "WIFE_OF" and pr["source"] == "sunita devi" for pr in parsed_rels)

    # Check money transfer with integer amount_paise and from/to
    money_rels = [pr for pr in parsed_rels if pr["relationship_type"] == "TRANSFERRED_TO" and pr.get("amount_paise")]
    assert len(money_rels) >= 1
    assert money_rels[0]["amount_paise"] == 45000000
    assert money_rels[0]["from_party"] == "rajesh verma"
    assert money_rels[0]["to_party"] == suite["account_1"]


def test_legal_sections_ipc_bns_mapping_and_missing_behavior(tmp_path: Path):
    """
    Task 5: Parse IPC/BNS/BNSS/IT Act mentions; load reference mapping from ipc_bns_map.json
    marked 'reference — verify against the official gazette'; show both when mapped and
    'mapping unavailable' when unmapped. Never invent mappings.
    """
    gen = SyntheticDataGenerator(seed=604)
    suite = gen.write_phase6_fir_suite(tmp_path)
    fir_text = Path(suite["complete_fir_path"]).read_text(encoding="utf-8")

    sections = extract_legal_sections(fir_text, "Page 1")
    by_norm = {s["normalized_value"]: s["meta"] for s in sections}

    assert "IPC 420" in by_norm
    assert by_norm["IPC 420"]["mapped_act"] == "BNS"
    assert by_norm["IPC 420"]["mapped_section"] == "318(4)"
    assert by_norm["IPC 420"]["mapping_status"] == "mapped"
    assert by_norm["IPC 420"]["disclaimer"] == "reference — verify against the official gazette"

    assert "IPC 406" in by_norm
    assert by_norm["IPC 406"]["mapped_section"] == "316(2)"

    assert "IPC 120B" in by_norm
    assert by_norm["IPC 120B"]["mapped_section"] == "61(2)"

    assert "IT Act 66D" in by_norm
    assert by_norm["IT Act 66D"]["mapping_status"] == "known_statute"

    # Unmapped section (IPC 999) must explicitly say "mapping unavailable" and never invent a BNS section
    assert "IPC 999" in by_norm
    assert by_norm["IPC 999"]["mapped_section"] is None
    assert by_norm["IPC 999"]["mapping_status"] == "mapping unavailable"
    assert "mapping unavailable" in by_norm["IPC 999"]["display_label"]
    assert by_norm["IPC 999"]["disclaimer"] == "reference — verify against the official gazette"

    # Reverse BNS -> IPC lookup check
    rev = resolve_legal_section_mapping("BNS", "318(4)")
    assert rev["mapped_act"] == "IPC"
    assert rev["mapped_section"] == "420"


def test_hinglish_and_devanagari_fir_extraction(tmp_path: Path):
    """
    Task 8: Hinglish and Devanagari-digit FIR variants extract roles, phones, dates,
    IPC/BNS sections, and sentence relations accurately.
    """
    gen = SyntheticDataGenerator(seed=605)
    suite = gen.write_phase6_fir_suite(tmp_path)
    hinglish_text = Path(suite["hinglish_fir_path"]).read_text(encoding="utf-8")

    rule_ents = extract_rule_entities(hinglish_text, "Page 1")
    ner_ents = extract_ner_entities(
        hinglish_text,
        "Page 1",
        existing_spans=[(e["char_span_start"], e["char_span_end"]) for e in rule_ents],
    )
    all_ents = rule_ents + ner_ents
    rels = extract_cooccurrence_relationships(hinglish_text, all_ents, "Page 1")

    phones = [e for e in rule_ents if e["entity_type"] == "PHONE"]
    assert any(p["normalized_value"] == suite["phone_2"] for p in phones)

    sections = [e for e in rule_ents if e["entity_type"] == "LEGAL_SECTION"]
    sec_norms = {s["normalized_value"] for s in sections}
    assert "IPC 420" in sec_norms
    assert "BNS 318(4)" in sec_norms

    persons = {e["normalized_value"]: e for e in ner_ents if e["entity_type"] == "PERSON"}
    assert "alok tiwari" in persons
    assert persons["alok tiwari"]["role"] == "complainant"
    assert "ramesh chauhan" in persons
    assert persons["ramesh chauhan"]["role"] == "accused"

    # Hinglish relation: "Ramesh Chauhan ka mobile number <devanagari_phone> hai"
    rel_payloads = [json.loads(r["normalized_value"]) for r in rels]
    assert any(
        rp["source"] == "ramesh chauhan" and rp["target"] == suite["phone_2"] and rp["relationship_type"] == "USES"
        for rp in rel_payloads
    )


def test_incident_facts_timeline_completeness_and_merge_pipeline(tmp_path: Path):
    """
    Tasks 4, 6, 7: Incident facts (`document_fact` records in Merge Engine), chronological timeline,
    per-FIR completeness (complete vs incomplete FIR), and review workflow with zero auto-approval.
    """
    token, user_id, case_id = _setup_user_and_case("fir_v2_inv", "FIR V2 Pipeline Case")
    gen = SyntheticDataGenerator(seed=606)
    suite = gen.write_phase6_fir_suite(tmp_path)

    db = SessionLocal()
    ev_complete = EvidenceFile(
        case_id=case_id,
        original_name="fir_complete_english.txt",
        stored_path=suite["complete_fir_path"],
        file_size=Path(suite["complete_fir_path"]).stat().st_size,
        sha256="sha_fir_complete_" + case_id[:12],
        detected_type="fir",
        uploader_id=user_id,
        status="uploaded",
    )
    ev_incomplete = EvidenceFile(
        case_id=case_id,
        original_name="fir_incomplete.txt",
        stored_path=suite["incomplete_fir_path"],
        file_size=Path(suite["incomplete_fir_path"]).stat().st_size,
        sha256="sha_fir_incomplete_" + case_id[:12],
        detected_type="fir",
        uploader_id=user_id,
        status="uploaded",
    )
    db.add(ev_complete)
    db.add(ev_incomplete)
    db.commit()
    ev_complete_id = ev_complete.id
    ev_incomplete_id = ev_incomplete.id
    db.close()

    # 1. Extract complete FIR
    res1 = client.post(
        f"/evidence/{ev_complete_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["status"] == "completed"
    fir_analysis = body1["fir_analysis"]

    assert fir_analysis["completeness"]["is_complete"] is True
    assert fir_analysis["completeness"]["missing_fields"] == []
    assert len(fir_analysis["timeline"]) >= 3
    # Timeline is sorted chronologically (13/08 -> 14/08 -> 15/08)
    ts_list = [t["timestamp_iso"] for t in fir_analysis["timeline"]]
    assert ts_list == sorted(ts_list)

    # Verify GET /evidence/{id}/fir-analysis endpoint
    analysis_res = client.get(
        f"/evidence/{ev_complete_id}/fir-analysis",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analysis_res.status_code == 200
    analysis_json = analysis_res.json()
    fact_keys = {f["fact_key"] for f in analysis_json["facts"]}
    assert {"fir_no", "police_station", "incident_date", "incident_place", "complainant", "sections"}.issubset(fact_keys)
    assert len(analysis_json["relationship_proposals"]) >= 4
    for prop in analysis_json["relationship_proposals"]:
        assert prop["status"] == "pending_review"

    # Verify Phase 3 Merge Engine received both `entity` and `document_fact` records,
    # and that Mohd. Imran and Mohammad Imran were NOT merged into one Person record!
    db = SessionLocal()
    doc_fact_recs = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.record_type == "document_fact")
        .all()
    )
    assert len(doc_fact_recs) >= 6

    person_recs = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.record_type == "entity")
        .all()
    )
    person_names_in_store = {
        json.loads(r.data_json).get("canonical_id")
        for r in person_recs
        if json.loads(r.data_json).get("label") == "Person"
    }
    assert "mohd imran" in person_names_in_store
    assert "mohammad imran" in person_names_in_store

    # Verify zero auto-approved EntityLinks before officer approval
    links_before = db.query(EntityLink).filter(EntityLink.case_id == case_id).all()
    assert len(links_before) == 0
    db.close()

    # 2. Extract incomplete FIR and verify missing required fields are reported
    res2 = client.post(
        f"/evidence/{ev_incomplete_id}/extract",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    comp2 = res2.json()["fir_analysis"]["completeness"]
    assert comp2["is_complete"] is False
    assert "incident_place" in comp2["missing_fields"]
    assert "sections" in comp2["missing_fields"]
    assert "identifier" in comp2["missing_fields"]

