import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.db.sql import ExtractedEntity, EvidenceFile
from backend.app.services.extraction.text import read_document_text
from backend.app.services.extraction.rules import extract_rule_entities
from backend.app.services.extraction.ner import extract_ner_entities, extract_cooccurrence_relationships

def run_document_extraction(
    db: Session,
    evidence_id: str,
    case_id: str,
    file_path: str
) -> Dict[str, Any]:
    """
    Executes the full document NLP pipeline:
    1. Extracts text per page/paragraph.
    2. Runs deterministic pattern rules.
    3. Runs NER and title heuristic person extraction.
    4. Computes sentence co-occurrence relationship candidates.
    5. Stages all findings with status='pending_review' in SQLite extracted_entities.
    """
    doc_res = read_document_text(file_path)
    if doc_res.get("error"):
        return {
            "status": "failed",
            "error": doc_res["error"],
            "total_extracted": 0,
            "entities": []
        }

    pages = doc_res.get("pages", [])
    all_extracted: List[Dict[str, Any]] = []

    # Clear previously pending extractions for this evidence file to prevent duplicates
    db.query(ExtractedEntity).filter(
        ExtractedEntity.evidence_id == evidence_id,
        ExtractedEntity.status == "pending_review"
    ).delete()
    db.commit()

    by_type_counts: Dict[str, int] = {}

    for page in pages:
        p_name = page["page_or_paragraph"]
        p_text = page["text"]
        p_offset = page["char_offset"]

        # 1. Deterministic Rule Extraction
        rule_items = extract_rule_entities(p_text, p_name, base_char_offset=p_offset)
        existing_spans = [(item["char_span_start"], item["char_span_end"]) for item in rule_items]

        # 2. NER & Heuristic Person Extraction
        ner_items = extract_ner_entities(p_text, p_name, base_char_offset=p_offset, existing_spans=existing_spans)

        # 2b. Gemini LLM Extraction (If GEMINI_API_KEY is configured)
        gemini_items = []
        try:
            from backend.app.services.ai.gemini_service import is_gemini_configured, extract_entities_with_gemini
            if is_gemini_configured():
                gemini_items = extract_entities_with_gemini(p_text, p_name)
        except Exception:
            gemini_items = []

        page_entities = rule_items + ner_items + gemini_items

        # 3. Candidate Relationships from Sentence Co-occurrence
        rel_items = extract_cooccurrence_relationships(p_text, page_entities, p_name, base_char_offset=p_offset)

        total_page_items = page_entities + rel_items

        for item in total_page_items:
            t = item["entity_type"]
            by_type_counts[t] = by_type_counts.get(t, 0) + 1

            ee = ExtractedEntity(
                evidence_id=evidence_id,
                case_id=case_id,
                entity_type=t,
                raw_value=item["raw_value"],
                normalized_value=item["normalized_value"],
                page_or_paragraph=item["page_or_paragraph"],
                char_span_start=item["char_span_start"],
                char_span_end=item["char_span_end"],
                confidence=item["confidence"],
                method=item["method"],
                status="pending_review"
            )
            db.add(ee)
            all_extracted.append(item)

    db.commit()

    return {
        "status": "completed",
        "evidence_id": evidence_id,
        "case_id": case_id,
        "total_extracted": len(all_extracted),
        "by_type": by_type_counts,
        "pages_count": len(pages),
        "warning": doc_res.get("warning"),
        "error": None
    }
