from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.config import get_extraction_config
from backend.app.db.sql import EvidenceFile, EvidencePage, ExtractedEntity
from backend.app.services.extraction.ner import (
    extract_cooccurrence_relationships,
    extract_ner_entities,
)
from backend.app.services.extraction.rules import (
    compute_fir_completeness,
    extract_incident_facts,
    extract_rule_entities,
)
from backend.app.services.extraction.text import compute_span_bbox, read_document_text
from backend.app.services.ingestion.validators import to_ascii_digits
from backend.app.services.merge.engine import apply_evidence_merge


def _extract_entities_for_page_text(
    p_text: str,
    p_name: str,
    p_offset: int,
    page_no: int,
    page_words: List[Dict[str, Any]],
    source_kind: str,
    is_handwritten: bool,
    hw_conf_cap: float,
) -> List[Dict[str, Any]]:
    """
    Runs deterministic rules, spaCy NER (with Devanagari digit conversion), and
    co-occurrence relationship extraction on a single page's text, attaching
    `page_no`, `bbox`, `source_kind`, and handwriting confidence caps.
    """
    if not p_text or not p_text.strip():
        return []

    rule_items = extract_rule_entities(p_text, p_name, base_char_offset=p_offset)
    existing_spans = [(item["char_span_start"], item["char_span_end"]) for item in rule_items]

    ner_items = extract_ner_entities(
        to_ascii_digits(p_text),
        p_name,
        base_char_offset=p_offset,
        existing_spans=existing_spans,
    )

    page_entities = rule_items + ner_items
    rel_items = extract_cooccurrence_relationships(
        p_text,
        page_entities,
        p_name,
        base_char_offset=p_offset,
    )
    total_page_items = page_entities + rel_items

    enriched: List[Dict[str, Any]] = []
    for item in total_page_items:
        rel_start = max(0, int(item.get("char_span_start", p_offset)) - p_offset)
        rel_end = max(rel_start, int(item.get("char_span_end", p_offset)) - p_offset)
        bbox = compute_span_bbox(page_words, rel_start, rel_end)

        conf = float(item.get("confidence", 0.5))
        if is_handwritten or source_kind == "ocr_handwritten":
            conf = round(min(conf, hw_conf_cap), 4)

        item_copy = dict(item)
        item_copy["confidence"] = conf
        item_copy["page_no"] = page_no
        item_copy["bbox"] = bbox
        item_copy["source_kind"] = "ocr_handwritten" if is_handwritten else source_kind
        item_copy["status"] = "pending_review"
        enriched.append(item_copy)

    return enriched


def _build_merge_records_from_extracted(
    items: List[Dict[str, Any]],
    override_source_kind: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Converts extracted document entities into Phase 3 Merge Engine record dicts."""
    label_map = {
        "PERSON": "Person",
        "PHONE": "Phone",
        "BANK_ACCOUNT": "BankAccount",
        "ACCOUNT_SUFFIX": "BankAccount",
        "VEHICLE": "Vehicle",
        "FIR": "FIR",
        "ORGANIZATION": "Organization",
        "AADHAAR": "Aadhaar",
        "PAN": "PAN",
        "IFSC": "IFSC",
        "UPI": "UPI",
        "IMEI": "IMEI",
        "EMAIL": "Email",
        "IP": "IP",
        "LEGAL_SECTION": "LegalSection",
        "POLICE_STATION": "PoliceStation",
    }
    merge_records: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        etype = str(item.get("entity_type") or "ENTITY").upper()
        if etype == "RELATIONSHIP":
            continue
        norm_val = str(item.get("normalized_value") or "").strip()
        raw_val = str(item.get("raw_value") or norm_val).strip()
        if not norm_val:
            continue
        src_kind = override_source_kind or str(item.get("source_kind") or "text_layer_pdf")
        conf = 1.0 if src_kind == "officer" else float(item.get("confidence", 0.5))
        page_no = item.get("page_no")
        bbox = item.get("bbox")
        label = label_map.get(etype, etype.title())
        meta = item.get("meta") or {}

        rec: Dict[str, Any] = {
            "label": label,
            "entity_type": etype,
            "canonical_id": norm_val,
            "normalized_value": norm_val,
            "display_name": raw_val if label in ("Person", "Organization", "FIR") else norm_val,
            "raw_value": raw_val,
            "review_status": "approved" if src_kind == "officer" else "pending_review",
            "_source_ref": f"p{page_no}:{item.get('char_span_start', idx)}" if page_no else str(idx),
            "_page_no": page_no,
            "_bbox": bbox,
            "_source_kind": src_kind,
            "_method": "officer" if src_kind == "officer" else str(item.get("method") or "document_nlp"),
            "_confidence": conf,
            "_raw": {
                "raw_value": raw_val,
                "page_or_paragraph": item.get("page_or_paragraph"),
                "bbox": bbox,
                "meta": meta,
            },
        }
        if item.get("role"):
            rec["role"] = item["role"]
        if meta.get("candidate_variants"):
            rec["candidate_variants"] = json.dumps(meta["candidate_variants"])
        if meta.get("kinship_marker"):
            rec["kinship_marker"] = meta["kinship_marker"]
        if meta.get("residence"):
            rec["address"] = meta["residence"]
        if etype == "LEGAL_SECTION" and meta:
            rec["act"] = meta.get("act")
            rec["section_code"] = meta.get("section")
            rec["mapped_act"] = meta.get("mapped_act")
            rec["mapped_section"] = meta.get("mapped_section")
            rec["mapping_status"] = meta.get("mapping_status")
            rec["disclaimer"] = meta.get("disclaimer")

        merge_records.append(rec)
    return merge_records


def _build_document_fact_merge_records(
    facts: List[Dict[str, Any]],
    source_kind: str = "text_layer_pdf",
) -> List[Dict[str, Any]]:
    """Converts extracted FIR incident facts (`document_fact`) into Phase 3 Merge Engine records."""
    out: List[Dict[str, Any]] = []
    for idx, f in enumerate(facts, start=1):
        f_key = str(f.get("fact_key") or "fact").strip()
        f_val = str(f.get("normalized_value") or "").strip()
        raw_val = str(f.get("raw_value") or f_val).strip()
        if not f_val:
            continue
        rec: Dict[str, Any] = {
            "fact_type": "fir_incident_fact",
            "fact_key": f_key,
            "fact_value": f_val,
            "raw_value": raw_val,
            "char_span_start": f.get("char_span_start", 0),
            "char_span_end": f.get("char_span_end", 0),
            "page_or_paragraph": f.get("page_or_paragraph", "Page 1"),
            "review_status": "pending_review",
            "_source_ref": f"fact:{f_key}:{f.get('char_span_start', idx)}",
            "_source_kind": source_kind,
            "_method": str(f.get("method") or "regex"),
            "_confidence": float(f.get("confidence", 0.90)),
            "_raw": f,
        }
        if f_key == "incident_date":
            rec["date_iso"] = f_val
        elif f_key == "incident_place":
            rec["place"] = f_val
        elif f_key == "sections":
            rec["section_code"] = f_val
        out.append(rec)
    return out


def run_document_extraction(
    db: Session,
    evidence_id: str,
    case_id: str,
    file_path: str,
    user_id: str = "system",
    officer_marked_handwritten: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Executes the full document/image/PDF extraction pipeline:
    1. Routes PDFs page-by-page (PyMuPDF text layer vs OpenCV quality gate + OCR) or images through quality gate + OCR.
    2. Persists per-page metadata, raw OCR text, word boxes, hashes, and EXIF in `evidence_pages`.
    3. Runs deterministic rules (with Devanagari digit conversion), spaCy NER, and relationship extraction.
    4. Stages all findings with `status='pending_review'` (never auto-accepting handwritten items) in `extracted_entities`
       and feeds them into the Phase 3 Merge Engine (`extraction_records` + `field_claims`).
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    is_hw_flag = (
        bool(officer_marked_handwritten)
        if officer_marked_handwritten is not None
        else bool(ev.is_handwritten if ev else False)
    )
    if ev and officer_marked_handwritten is not None:
        ev.is_handwritten = bool(officer_marked_handwritten)
        db.flush()

    doc_res = read_document_text(file_path, officer_marked_handwritten=is_hw_flag)
    pages = doc_res.get("pages", [])

    # Persist EvidencePage rows even if status is needs_better_image or ocr_unavailable
    for pg in pages:
        p_no = int(pg.get("page_no", 1))
        ep = (
            db.query(EvidencePage)
            .filter(EvidencePage.evidence_id == evidence_id, EvidencePage.page_no == p_no)
            .first()
        )
        if not ep:
            ep = EvidencePage(
                case_id=case_id,
                evidence_id=evidence_id,
                page_no=p_no,
            )
            db.add(ep)

        ep.source_kind = str(pg.get("source_kind") or "text_layer_pdf")
        ep.status = str(pg.get("status") or "ready")
        ep.quality_reason = pg.get("quality_reason")
        ep.quality_metrics_json = json.dumps(pg.get("quality_metrics") or {}, default=str)
        ep.preprocess_params_json = json.dumps(pg.get("preprocess_params") or {}, default=str)
        ep.raw_text = str(pg.get("text") or "")
        ep.words_json = json.dumps(pg.get("words") or [], default=str)
        ep.page_image_sha256 = pg.get("page_image_sha256")
        ep.perceptual_hash = pg.get("perceptual_hash")
        ep.exif_json = json.dumps(pg.get("exif") or {"disclaimer": "as reported by file"}, default=str)
        ep.engine_name = str(pg.get("engine_name") or "pymupdf")
        ep.engine_version = str(pg.get("engine_version") or "1.0")
        ep.mean_confidence = float(pg.get("mean_confidence", 1.0))
        ep.is_handwritten = bool(pg.get("is_handwritten", False))
        ep.updated_at = datetime.now(timezone.utc)

    # Update EvidenceFile image metadata / status
    if ev and pages:
        first_pg = pages[0]
        if first_pg.get("perceptual_hash"):
            ev.perceptual_hash = first_pg["perceptual_hash"]
        if first_pg.get("exif"):
            ev.exif_json = json.dumps(first_pg["exif"], default=str)
        ev.quality_json = json.dumps(
            {
                "status": doc_res.get("status", "ready"),
                "pages": [
                    {
                        "page_no": p.get("page_no"),
                        "status": p.get("status"),
                        "quality_reason": p.get("quality_reason"),
                        "mean_confidence": p.get("mean_confidence"),
                    }
                    for p in pages
                ],
            },
            default=str,
        )
        if doc_res.get("status") == "needs_better_image":
            ev.status = "needs_better_image"
    db.commit()

    if doc_res.get("status") == "needs_better_image":
        return {
            "status": "needs_better_image",
            "evidence_id": evidence_id,
            "case_id": case_id,
            "reason": doc_res.get("warning") or "Image quality below minimum threshold",
            "pages_count": len(pages),
            "total_extracted": 0,
            "by_type": {},
            "entities": [],
            "error": None,
        }

    if doc_res.get("error"):
        return {
            "status": "failed",
            "error": doc_res["error"],
            "total_extracted": 0,
            "entities": [],
        }

    # Clear previously pending extractions for this evidence file to prevent duplicates
    db.query(ExtractedEntity).filter(
        ExtractedEntity.evidence_id == evidence_id,
        ExtractedEntity.status == "pending_review",
    ).delete()
    db.commit()

    ext_cfg = get_extraction_config()
    hw_conf_cap = float(ext_cfg.get("ocr", {}).get("handwritten_conf_cap", 0.65))

    all_extracted: List[Dict[str, Any]] = []
    by_type_counts: Dict[str, int] = {}

    for page in pages:
        p_name = page["page_or_paragraph"]
        p_text = page.get("text") or ""
        p_offset = int(page.get("char_offset", 0))
        p_no = int(page.get("page_no", 1))
        p_words = page.get("words") or []
        p_source_kind = str(page.get("source_kind") or "text_layer_pdf")
        p_is_hw = bool(page.get("is_handwritten", False))

        page_items = _extract_entities_for_page_text(
            p_text=p_text,
            p_name=p_name,
            p_offset=p_offset,
            page_no=p_no,
            page_words=p_words,
            source_kind=p_source_kind,
            is_handwritten=p_is_hw,
            hw_conf_cap=hw_conf_cap,
        )

        for item in page_items:
            t = item["entity_type"]
            by_type_counts[t] = by_type_counts.get(t, 0) + 1

            ee = ExtractedEntity(
                evidence_id=evidence_id,
                case_id=case_id,
                entity_type=t,
                raw_value=item["raw_value"],
                normalized_value=item["normalized_value"],
                page_or_paragraph=item["page_or_paragraph"],
                page_no=item.get("page_no"),
                bbox_json=json.dumps(item["bbox"]) if item.get("bbox") is not None else None,
                source_kind=item.get("source_kind"),
                char_span_start=item["char_span_start"],
                char_span_end=item["char_span_end"],
                confidence=item["confidence"],
                method=item["method"],
                status="pending_review",
            )
            db.add(ee)
            all_extracted.append(item)

    db.commit()

    # Feed extracted entities into Phase 3 Merge Engine (records + claims)
    merge_records = _build_merge_records_from_extracted(all_extracted)
    primary_source_kind = (
        merge_records[0].get("_source_kind", "text_layer_pdf")
        if merge_records
        else (str(pages[0].get("source_kind")) if pages else "text_layer_pdf")
    )
    if merge_records:
        apply_evidence_merge(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            record_type="entity",
            records=merge_records,
            user_id=user_id,
            source_kind=primary_source_kind,
            method="document_nlp",
            default_confidence=0.80,
            preview=False,
            source_file_name=ev.original_name if ev else evidence_id,
        )

    # Extract FIR incident facts, IPC<->BNS section mappings, timeline, and completeness
    full_text = doc_res.get("full_text") or "\n".join(str(p.get("text") or "") for p in pages)
    facts_res = extract_incident_facts(
        text=full_text,
        page_or_para="Document",
        base_char_offset=0,
        extracted_entities=all_extracted,
    )
    completeness_res = compute_fir_completeness(facts_res, all_extracted)

    doc_fact_records = _build_document_fact_merge_records(
        facts_res.get("facts", []),
        source_kind=primary_source_kind,
    )
    if doc_fact_records:
        apply_evidence_merge(
            db=db,
            case_id=case_id,
            evidence_id=evidence_id,
            record_type="document_fact",
            records=doc_fact_records,
            user_id=user_id,
            source_kind=primary_source_kind,
            method="regex",
            default_confidence=0.90,
            preview=False,
            source_file_name=ev.original_name if ev else evidence_id,
        )

    return {
        "status": "completed",
        "evidence_id": evidence_id,
        "case_id": case_id,
        "total_extracted": len(all_extracted),
        "by_type": by_type_counts,
        "pages_count": len(pages),
        "fir_analysis": {
            "facts": facts_res.get("facts", []),
            "sections": facts_res.get("sections", []),
            "timeline": facts_res.get("timeline", []),
            "completeness": completeness_res,
        },
        "warning": doc_res.get("warning"),
        "error": None,
    }


def apply_page_ocr_correction(
    db: Session,
    evidence_id: str,
    page_no: int,
    user_id: str,
    corrected_text: str,
    word_id: Optional[str] = None,
    span: Optional[Tuple[int, int]] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Applies an officer correction to an OCR/document page:
    - Never overwrites `EvidencePage.raw_text`.
    - Updates `words_json` (`corrected_text`, `corrected_by`) and `EvidencePage.corrected_text`.
    - Re-runs extraction on the corrected page text.
    - Stores corrected entities as officer claims (`source_kind='officer'`, highest trust, locked=True)
      via the Phase 3 Merge Engine and logs `OCR_CORRECTION` to `audit_log`.
    """
    ep = (
        db.query(EvidencePage)
        .filter(EvidencePage.evidence_id == evidence_id, EvidencePage.page_no == page_no)
        .first()
    )
    if not ep:
        raise ValueError(f"Page {page_no} not found for evidence {evidence_id}")

    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    words: List[Dict[str, Any]] = json.loads(ep.words_json or "[]")
    base_text = ep.corrected_text if ep.corrected_text is not None else ep.raw_text

    corrected_char_range: Optional[Tuple[int, int]] = None

    if word_id:
        target_word = next((w for w in words if str(w.get("word_id")) == str(word_id)), None)
        if not target_word:
            raise ValueError(f"Word ID '{word_id}' not found on page {page_no}")
        target_word["corrected_text"] = corrected_text
        target_word["corrected_by"] = user_id
        target_word["conf"] = 1.0

        # Reconstruct corrected page text from words while updating char_start/char_end
        lines_out: List[str] = []
        current_line_id = None
        cursor = 0
        for w in words:
            tok = str(w.get("corrected_text") if w.get("corrected_text") is not None else w.get("text", "")).strip()
            if not tok:
                continue
            line_id = w.get("line_id", "1_1_1")
            if current_line_id is not None and line_id != current_line_id:
                lines_out.append("\n")
                cursor += 1
            elif current_line_id is not None:
                lines_out.append(" ")
                cursor += 1
            current_line_id = line_id

            s_pos = cursor
            lines_out.append(tok)
            cursor += len(tok)
            e_pos = cursor
            w["char_start"] = s_pos
            w["char_end"] = e_pos
            if str(w.get("word_id")) == str(word_id):
                corrected_char_range = (s_pos, e_pos)

        new_page_text = "".join(lines_out)
    elif span is not None:
        s_idx, e_idx = int(span[0]), int(span[1])
        if s_idx < 0 or e_idx < s_idx or e_idx > len(base_text):
            raise ValueError("Invalid character span for correction")
        new_page_text = base_text[:s_idx] + corrected_text + base_text[e_idx:]
        corrected_char_range = (s_idx, s_idx + len(corrected_text))
    else:
        new_page_text = corrected_text
        corrected_char_range = (0, len(corrected_text))

    # Never overwrite ep.raw_text; store in ep.corrected_text
    ep.corrected_text = new_page_text
    ep.words_json = json.dumps(words, default=str)
    ep.updated_at = datetime.now(timezone.utc)
    db.flush()

    ext_cfg = get_extraction_config()
    hw_conf_cap = float(ext_cfg.get("ocr", {}).get("handwritten_conf_cap", 0.65))
    p_name = f"Page {page_no} (Officer Corrected)"

    # Remove old pending entities on this page and re-extract
    db.query(ExtractedEntity).filter(
        ExtractedEntity.evidence_id == evidence_id,
        ExtractedEntity.page_no == page_no,
        ExtractedEntity.status == "pending_review",
    ).delete()
    db.flush()

    reextracted_items = _extract_entities_for_page_text(
        p_text=new_page_text,
        p_name=p_name,
        p_offset=0,
        page_no=page_no,
        page_words=words,
        source_kind=ep.source_kind,
        is_handwritten=ep.is_handwritten,
        hw_conf_cap=hw_conf_cap,
    )

    officer_touched_items: List[Dict[str, Any]] = []
    other_items: List[Dict[str, Any]] = []

    for item in reextracted_items:
        i_start = int(item.get("char_span_start", 0))
        i_end = int(item.get("char_span_end", 0))
        is_touched = bool(
            corrected_char_range
            and max(i_start, corrected_char_range[0]) < min(i_end, max(corrected_char_range[1], corrected_char_range[0] + 1))
        )
        if is_touched:
            item["confidence"] = 1.0
            item["method"] = "officer"
            item["source_kind"] = "officer"
            officer_touched_items.append(item)
        else:
            other_items.append(item)

        ee = ExtractedEntity(
            evidence_id=evidence_id,
            case_id=ep.case_id,
            entity_type=item["entity_type"],
            raw_value=item["raw_value"],
            normalized_value=item["normalized_value"],
            page_or_paragraph=item["page_or_paragraph"],
            page_no=page_no,
            bbox_json=json.dumps(item["bbox"]) if item.get("bbox") is not None else None,
            source_kind=item["source_kind"],
            char_span_start=i_start,
            char_span_end=i_end,
            confidence=item["confidence"],
            method=item["method"],
            status="approved" if is_touched else "pending_review",
            reviewed_by=user_id if is_touched else None,
        )
        db.add(ee)

    db.commit()

    # Feed officer-corrected entities as highest-trust locked officer claims
    officer_merge_recs = _build_merge_records_from_extracted(
        officer_touched_items if officer_touched_items else reextracted_items,
        override_source_kind="officer",
    )
    merge_res = None
    if officer_merge_recs:
        merge_res = apply_evidence_merge(
            db=db,
            case_id=ep.case_id,
            evidence_id=evidence_id,
            record_type="entity",
            records=officer_merge_recs,
            user_id=user_id,
            source_kind="officer",
            method="officer",
            default_confidence=1.0,
            preview=False,
            source_file_name=ev.original_name if ev else evidence_id,
        )

    record_audit_log(
        db=db,
        user_id=user_id,
        action="OCR_CORRECTION",
        case_id=ep.case_id,
        object_type="evidence_page",
        object_id=f"{evidence_id}:p{page_no}",
        details={
            "word_id": word_id,
            "span": list(span) if span else None,
            "note": note,
            "reextracted_count": len(reextracted_items),
            "officer_claims_count": len(officer_merge_recs),
        },
    )

    return {
        "evidence_id": evidence_id,
        "page_no": page_no,
        "raw_text": ep.raw_text,
        "corrected_text": ep.corrected_text,
        "reextracted_count": len(reextracted_items),
        "officer_locked_entities": [
            {
                "entity_type": it["entity_type"],
                "normalized_value": it["normalized_value"],
                "bbox": it.get("bbox"),
                "confidence": 1.0,
                "source_kind": "officer",
            }
            for it in (officer_touched_items if officer_touched_items else reextracted_items)
        ],
        "merge_counts": merge_res["counts"] if merge_res else {},
    }
