import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.audit.service import record_audit_log
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.config import get_extraction_config
from backend.app.db.sql import (
    Case,
    Entity,
    EntityLink,
    EvidenceFile,
    EvidencePage,
    ExtractedEntity,
    User,
    get_db,
)
from backend.app.services.extraction.ocr.preprocess import phash_distance
from backend.app.services.extraction.pipeline import (
    apply_page_ocr_correction,
    run_document_extraction,
)
from backend.app.services.extraction.rules import (
    compute_fir_completeness,
    extract_incident_facts,
)
from backend.app.services.extraction.text import read_document_text
from backend.app.services.graph.builder import invalidate_case_graph

router = APIRouter()


class PatchExtractedRequest(BaseModel):
    status: Optional[str] = None  # "approved", "rejected", "pending_review"
    normalized_value: Optional[str] = None


class CreateManualExtractedRequest(BaseModel):
    evidence_id: str
    entity_type: str
    raw_value: str
    normalized_value: str
    page_or_paragraph: str = "Manual Entry"
    confidence: float = 1.0


class PageCorrectionRequest(BaseModel):
    word_id: Optional[str] = None
    span: Optional[List[int]] = None
    corrected_text: str
    note: Optional[str] = None


class MarkHandwrittenRequest(BaseModel):
    is_handwritten: bool = True


def _commit_approved_entity(db: Session, ee: ExtractedEntity, user_id: str):
    """
    Commits an approved extracted entity to the official staging tables (Entity / EntityLink)
    and creates MENTIONED_IN FIR links when applicable.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == ee.evidence_id).first()
    src_file = ev.original_name if ev else "Document"

    if ee.entity_type == "RELATIONSHIP":
        try:
            rel_info = json.loads(ee.normalized_value)
            rel_method = str(rel_info.get("method") or ee.method or "regex")
            if rel_method not in ("regex", "ner", "nlp_relationship", "officer"):
                rel_method = "regex"
            props = {
                "sentence": rel_info.get("sentence", ""),
                "char_span_start": rel_info.get("char_span_start", ee.char_span_start),
                "char_span_end": rel_info.get("char_span_end", ee.char_span_end),
            }
            for opt_key in ("amount_paise", "amount_raw", "from_party", "to_party", "target_type"):
                if opt_key in rel_info:
                    props[opt_key] = rel_info[opt_key]
            link = EntityLink(
                case_id=ee.case_id,
                source_entity_id=rel_info["source"],
                target_entity_id=rel_info["target"],
                relationship_type=rel_info.get("relationship_type", "USES"),
                properties_json=json.dumps(props),
                source_file=src_file,
                source_ref=ee.page_or_paragraph,
                method=rel_method,
                confidence=ee.confidence,
                approved_by=user_id,
            )
            db.add(link)
        except Exception:
            pass

    else:
        label_map = {
            "PERSON": "Person",
            "PHONE": "Phone",
            "BANK_ACCOUNT": "BankAccount",
            "ACCOUNT_SUFFIX": "BankAccount",
            "VEHICLE": "Vehicle",
            "FIR": "FIR",
            "ORGANIZATION": "Organization",
        }
        label = label_map.get(ee.entity_type)
        if label:
            existing_ent = (
                db.query(Entity)
                .filter(
                    Entity.case_id == ee.case_id,
                    Entity.label == label,
                    Entity.canonical_id == ee.normalized_value,
                )
                .first()
            )

            if not existing_ent:
                ent = Entity(
                    case_id=ee.case_id,
                    label=label,
                    canonical_id=ee.normalized_value,
                    display_name=ee.raw_value if label in ["Person", "Organization", "FIR"] else ee.normalized_value,
                    properties_json=json.dumps(
                        {
                            "raw_value": ee.raw_value,
                            "evidence_id": ee.evidence_id,
                            "page_no": ee.page_no,
                            "bbox": json.loads(ee.bbox_json) if ee.bbox_json else None,
                        }
                    ),
                    source_file=src_file,
                    source_ref=ee.page_or_paragraph,
                    method="document_nlp",
                    confidence=ee.confidence,
                )
                db.add(ent)

            if label == "Person":
                fir_entity = (
                    db.query(ExtractedEntity)
                    .filter(
                        ExtractedEntity.evidence_id == ee.evidence_id,
                        ExtractedEntity.entity_type == "FIR",
                        ExtractedEntity.status == "approved",
                    )
                    .first()
                )

                if fir_entity:
                    existing_link = (
                        db.query(EntityLink)
                        .filter(
                            EntityLink.case_id == ee.case_id,
                            EntityLink.source_entity_id == ee.normalized_value,
                            EntityLink.target_entity_id == fir_entity.normalized_value,
                            EntityLink.relationship_type == "MENTIONED_IN",
                        )
                        .first()
                    )
                    if not existing_link:
                        fir_link = EntityLink(
                            case_id=ee.case_id,
                            source_entity_id=ee.normalized_value,
                            target_entity_id=fir_entity.normalized_value,
                            relationship_type="MENTIONED_IN",
                            properties_json=json.dumps({"page": ee.page_or_paragraph}),
                            source_file=src_file,
                            source_ref=ee.page_or_paragraph,
                            method="fir_mention",
                            confidence=ee.confidence,
                            approved_by=user_id,
                        )
                        db.add(fir_link)

            elif label == "FIR":
                approved_persons = (
                    db.query(ExtractedEntity)
                    .filter(
                        ExtractedEntity.evidence_id == ee.evidence_id,
                        ExtractedEntity.entity_type == "PERSON",
                        ExtractedEntity.status == "approved",
                    )
                    .all()
                )
                for p in approved_persons:
                    existing_link = (
                        db.query(EntityLink)
                        .filter(
                            EntityLink.case_id == ee.case_id,
                            EntityLink.source_entity_id == p.normalized_value,
                            EntityLink.target_entity_id == ee.normalized_value,
                            EntityLink.relationship_type == "MENTIONED_IN",
                        )
                        .first()
                    )
                    if not existing_link:
                        fir_link = EntityLink(
                            case_id=ee.case_id,
                            source_entity_id=p.normalized_value,
                            target_entity_id=ee.normalized_value,
                            relationship_type="MENTIONED_IN",
                            properties_json=json.dumps({"page": p.page_or_paragraph}),
                            source_file=src_file,
                            source_ref=p.page_or_paragraph,
                            method="fir_mention",
                            confidence=p.confidence,
                            approved_by=user_id,
                        )
                        db.add(fir_link)


@router.post("/evidence/{evidence_id}/extract")
def extract_evidence_document(
    evidence_id: str,
    is_handwritten: Optional[bool] = Query(None, description="Optional flag marking document/image as handwritten"),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Executes NLP & OCR extraction pipeline on an uploaded document or image evidence file."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    res = run_document_extraction(
        db=db,
        evidence_id=ev.id,
        case_id=ev.case_id,
        file_path=ev.stored_path,
        user_id=current_user.id,
        officer_marked_handwritten=is_handwritten,
    )
    if res.get("status") == "failed":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=res["error"])

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="document_extract",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={
            "status": res["status"],
            "total_extracted": res["total_extracted"],
        },
    )

    return res


@router.patch("/evidence/{evidence_id}/handwritten")
def mark_evidence_handwritten(
    evidence_id: str,
    req: MarkHandwrittenRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Marks or unmarks an evidence file as handwritten and re-runs extraction with handwritten review rules."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    res = run_document_extraction(
        db=db,
        evidence_id=ev.id,
        case_id=ev.case_id,
        file_path=ev.stored_path,
        user_id=current_user.id,
        officer_marked_handwritten=req.is_handwritten,
    )
    return res


@router.get("/evidence/{evidence_id}/pages")
def list_evidence_pages(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns per-page OCR & quality gate metadata for an evidence file:
    page_no, source_kind, status, quality_reason, quality_metrics, mean_confidence,
    is_handwritten, page_image_sha256, perceptual_hash, duplicate_of_evidence_id, exif.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    pages = (
        db.query(EvidencePage)
        .filter(EvidencePage.evidence_id == evidence_id)
        .order_by(EvidencePage.page_no.asc())
        .all()
    )
    if not pages and ev.stored_path:
        # Populate pages lazily if not yet extracted
        run_document_extraction(
            db=db,
            evidence_id=ev.id,
            case_id=ev.case_id,
            file_path=ev.stored_path,
            user_id=current_user.id,
        )
        pages = (
            db.query(EvidencePage)
            .filter(EvidencePage.evidence_id == evidence_id)
            .order_by(EvidencePage.page_no.asc())
            .all()
        )

    ocr_cfg = get_extraction_config().get("ocr", {})
    phash_max_dist = int(ocr_cfg.get("phash_duplicate_max_dist", 4))

    other_pages = (
        db.query(EvidencePage)
        .filter(
            EvidencePage.case_id == ev.case_id,
            EvidencePage.evidence_id != evidence_id,
            EvidencePage.perceptual_hash.isnot(None),
        )
        .all()
    )

    out = []
    for p in pages:
        dup_ev_id = None
        if p.perceptual_hash:
            for op in other_pages:
                if phash_distance(p.perceptual_hash, op.perceptual_hash) <= phash_max_dist:
                    dup_ev_id = op.evidence_id
                    break
        words = json.loads(p.words_json or "[]")
        out.append({
            "page_no": p.page_no,
            "evidence_id": p.evidence_id,
            "case_id": p.case_id,
            "source_kind": p.source_kind,
            "status": p.status,
            "quality_reason": p.quality_reason,
            "quality_metrics": json.loads(p.quality_metrics_json or "{}"),
            "preprocess_params": json.loads(p.preprocess_params_json or "{}"),
            "mean_confidence": p.mean_confidence,
            "is_handwritten": p.is_handwritten,
            "word_count": len(words),
            "engine_name": p.engine_name,
            "engine_version": p.engine_version,
            "page_image_sha256": p.page_image_sha256,
            "perceptual_hash": p.perceptual_hash,
            "duplicate_of_evidence_id": dup_ev_id,
            "exif": json.loads(p.exif_json or '{"disclaimer": "as reported by file"}'),
        })

    return {
        "evidence_id": evidence_id,
        "case_id": ev.case_id,
        "file_name": ev.original_name,
        "status": ev.status,
        "is_handwritten": bool(ev.is_handwritten),
        "pages": out,
    }


@router.get("/evidence/{evidence_id}/pages/{page_no}/ocr")
def get_evidence_page_ocr(
    evidence_id: str,
    page_no: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns per-word OCR bounding boxes, confidences, raw/corrected text, and entities for a page."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    ep = (
        db.query(EvidencePage)
        .filter(EvidencePage.evidence_id == evidence_id, EvidencePage.page_no == page_no)
        .first()
    )
    if not ep and ev.stored_path:
        run_document_extraction(
            db=db,
            evidence_id=ev.id,
            case_id=ev.case_id,
            file_path=ev.stored_path,
            user_id=current_user.id,
        )
        ep = (
            db.query(EvidencePage)
            .filter(EvidencePage.evidence_id == evidence_id, EvidencePage.page_no == page_no)
            .first()
        )
    if not ep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Page {page_no} not found")

    entities = (
        db.query(ExtractedEntity)
        .filter(ExtractedEntity.evidence_id == evidence_id, ExtractedEntity.page_no == page_no)
        .all()
    )

    return {
        "evidence_id": evidence_id,
        "case_id": ev.case_id,
        "page_no": ep.page_no,
        "source_kind": ep.source_kind,
        "status": ep.status,
        "quality_reason": ep.quality_reason,
        "quality_metrics": json.loads(ep.quality_metrics_json or "{}"),
        "preprocess_params": json.loads(ep.preprocess_params_json or "{}"),
        "raw_text": ep.raw_text,
        "corrected_text": ep.corrected_text,
        "active_text": ep.corrected_text if ep.corrected_text is not None else ep.raw_text,
        "words": json.loads(ep.words_json or "[]"),
        "mean_confidence": ep.mean_confidence,
        "is_handwritten": ep.is_handwritten,
        "engine_name": ep.engine_name,
        "engine_version": ep.engine_version,
        "page_image_sha256": ep.page_image_sha256,
        "perceptual_hash": ep.perceptual_hash,
        "exif": json.loads(ep.exif_json or '{"disclaimer": "as reported by file"}'),
        "entities": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "raw_value": e.raw_value,
                "normalized_value": e.normalized_value,
                "page_no": e.page_no,
                "bbox": json.loads(e.bbox_json) if e.bbox_json else None,
                "source_kind": e.source_kind,
                "char_span_start": e.char_span_start,
                "char_span_end": e.char_span_end,
                "confidence": e.confidence,
                "method": e.method,
                "status": e.status,
            }
            for e in entities
        ],
    }


@router.post("/evidence/{evidence_id}/pages/{page_no}/corrections")
def submit_evidence_page_correction(
    evidence_id: str,
    page_no: int,
    req: PageCorrectionRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """
    Stores an officer OCR word/span correction as a locked officer claim (highest trust),
    re-extracts affected entities, and preserves the original OCR raw_text.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    span_tuple = (int(req.span[0]), int(req.span[1])) if req.span and len(req.span) == 2 else None
    try:
        return apply_page_ocr_correction(
            db=db,
            evidence_id=evidence_id,
            page_no=page_no,
            user_id=current_user.id,
            corrected_text=req.corrected_text,
            word_id=req.word_id,
            span=span_tuple,
            note=req.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/cases/{case_id}/extracted")
def list_extracted_entities(
    case_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    entity_type: Optional[str] = Query(None, alias="type"),
    min_conf: Optional[float] = Query(None),
    evidence_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists extracted entities from case documents with status, type, confidence, and bbox provenance."""
    q = db.query(ExtractedEntity).filter(ExtractedEntity.case_id == case.id)
    if status_filter:
        q = q.filter(ExtractedEntity.status == status_filter)
    if entity_type:
        q = q.filter(ExtractedEntity.entity_type == entity_type.upper())
    if min_conf is not None:
        q = q.filter(ExtractedEntity.confidence >= min_conf)
    if evidence_id:
        q = q.filter(ExtractedEntity.evidence_id == evidence_id)

    total = q.count()
    items = (
        q.order_by(ExtractedEntity.confidence.desc(), ExtractedEntity.char_span_start.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "evidence_id": e.evidence_id,
                "case_id": e.case_id,
                "entity_type": e.entity_type,
                "raw_value": e.raw_value,
                "normalized_value": e.normalized_value,
                "page_or_paragraph": e.page_or_paragraph,
                "page_no": e.page_no,
                "bbox": json.loads(e.bbox_json) if e.bbox_json else None,
                "source_kind": e.source_kind,
                "char_span_start": e.char_span_start,
                "char_span_end": e.char_span_end,
                "confidence": e.confidence,
                "method": e.method,
                "status": e.status,
                "reviewed_by": e.reviewed_by,
            }
            for e in items
        ],
    }


@router.get("/evidence/{evidence_id}/text")
def get_evidence_document_text(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns document pages/paragraphs with annotated entity character spans and bounding boxes
    for interactive document highlighting in the review interface.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    doc_data = read_document_text(ev.stored_path, officer_marked_handwritten=bool(ev.is_handwritten))
    if doc_data.get("error"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=doc_data["error"])

    entities = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == evidence_id).all()
    ent_list = [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "raw_value": e.raw_value,
            "normalized_value": e.normalized_value,
            "page_or_paragraph": e.page_or_paragraph,
            "page_no": e.page_no,
            "bbox": json.loads(e.bbox_json) if e.bbox_json else None,
            "source_kind": e.source_kind,
            "char_span_start": e.char_span_start,
            "char_span_end": e.char_span_end,
            "confidence": e.confidence,
            "status": e.status,
        }
        for e in entities
    ]

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "pages": doc_data["pages"],
        "full_text": doc_data["full_text"],
        "entities": ent_list,
        "warning": doc_data.get("warning"),
    }


@router.get("/evidence/{evidence_id}/fir-analysis")
def get_evidence_fir_analysis(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns Phase 6 FIR analysis for a document evidence file:
    - incident `facts` (`fir_no`, `police_station`, `incident_date`, `incident_time`, `incident_place`, `complainant`, `sections`) with character spans,
    - `sections` with IPC <-> BNS / CrPC <-> BNSS / IT Act reference mappings and official gazette disclaimer,
    - chronological incident `timeline`,
    - proposed `relationship_proposals` (`status='pending_review'`),
    - per-FIR `completeness` report (present vs missing required fields).
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    get_case_for_user(case_id=ev.case_id, current_user=current_user, db=db)

    entities_db = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == evidence_id).all()
    if not entities_db and ev.stored_path:
        run_document_extraction(
            db=db,
            evidence_id=ev.id,
            case_id=ev.case_id,
            file_path=ev.stored_path,
            user_id=current_user.id,
        )
        entities_db = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == evidence_id).all()

    doc_data = read_document_text(ev.stored_path, officer_marked_handwritten=bool(ev.is_handwritten))
    full_text = doc_data.get("full_text") or ""

    ent_dicts: List[Dict[str, Any]] = []
    rel_proposals: List[Dict[str, Any]] = []
    for e in entities_db:
        d = {
            "id": e.id,
            "entity_type": e.entity_type,
            "raw_value": e.raw_value,
            "normalized_value": e.normalized_value,
            "page_or_paragraph": e.page_or_paragraph,
            "page_no": e.page_no,
            "bbox": json.loads(e.bbox_json) if e.bbox_json else None,
            "source_kind": e.source_kind,
            "char_span_start": e.char_span_start,
            "char_span_end": e.char_span_end,
            "confidence": e.confidence,
            "method": e.method,
            "status": e.status,
        }
        ent_dicts.append(d)
        if e.entity_type == "RELATIONSHIP":
            try:
                rel_meta = json.loads(e.normalized_value)
            except Exception:
                rel_meta = {}
            rel_proposals.append({
                "id": e.id,
                "status": e.status,
                "method": rel_meta.get("method") or e.method,
                "confidence": e.confidence,
                "char_span_start": e.char_span_start,
                "char_span_end": e.char_span_end,
                **rel_meta,
            })

    facts_res = extract_incident_facts(
        text=full_text,
        page_or_para="Document",
        base_char_offset=0,
        extracted_entities=ent_dicts,
    )
    completeness = compute_fir_completeness(facts_res, ent_dicts)

    return {
        "evidence_id": ev.id,
        "case_id": ev.case_id,
        "file_name": ev.original_name,
        "facts": facts_res.get("facts", []),
        "sections": facts_res.get("sections", []),
        "timeline": facts_res.get("timeline", []),
        "relationship_proposals": rel_proposals,
        "completeness": completeness,
    }


@router.patch("/extracted/{extracted_id}")
def update_extracted_entity(
    extracted_id: str,
    req: PatchExtractedRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Reviews (approves/rejects/edits) an extracted entity. Upon approval, stages it to graph."""
    ee = db.query(ExtractedEntity).filter(ExtractedEntity.id == extracted_id).first()
    if not ee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extracted entity not found")

    if req.normalized_value:
        ee.normalized_value = req.normalized_value.strip()

    if req.status:
        prev_status = ee.status
        ee.status = req.status
        ee.reviewed_by = current_user.id

        if req.status == "approved" and prev_status != "approved":
            _commit_approved_entity(db, ee, current_user.id)
            invalidate_case_graph(ee.case_id)

    db.commit()
    db.refresh(ee)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action=f"extract_{ee.status}",
        case_id=ee.case_id,
        object_type="extracted_entity",
        object_id=ee.id,
        details={"type": ee.entity_type, "value": ee.normalized_value, "status": ee.status},
    )

    return {"status": ee.status, "id": ee.id, "normalized_value": ee.normalized_value}


@router.post("/cases/{case_id}/extracted")
def create_manual_extracted_entity(
    case_id: str,
    req: CreateManualExtractedRequest,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """Allows an investigator to manually tag a missing entity from document text."""
    ee = ExtractedEntity(
        evidence_id=req.evidence_id,
        case_id=case.id,
        entity_type=req.entity_type.upper(),
        raw_value=req.raw_value.strip(),
        normalized_value=req.normalized_value.strip(),
        page_or_paragraph=req.page_or_paragraph,
        source_kind="officer",
        char_span_start=0,
        char_span_end=len(req.raw_value),
        confidence=1.0,
        method="officer",
        status="approved",
        reviewed_by=current_user.id,
    )
    db.add(ee)
    db.commit()
    db.refresh(ee)

    _commit_approved_entity(db, ee, current_user.id)
    invalidate_case_graph(case.id)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="manual_entity_add",
        case_id=case.id,
        object_type="extracted_entity",
        object_id=ee.id,
        details={"type": req.entity_type, "value": req.normalized_value},
    )

    return {"status": "created_and_approved", "id": ee.id}


@router.post("/cases/{case_id}/extracted/approve-all")
def bulk_approve_extracted_entities(
    case_id: str,
    threshold: float = Query(0.8, ge=0.1, le=1.0),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db),
):
    """
    Bulk-approves pending entities meeting the confidence threshold and stages them to the graph.
    Handwritten OCR items (`source_kind == 'ocr_handwritten'`) are never bulk-approved automatically.
    """
    pending_items = (
        db.query(ExtractedEntity)
        .filter(
            ExtractedEntity.case_id == case.id,
            ExtractedEntity.status == "pending_review",
            ExtractedEntity.confidence >= threshold,
            or_(
                ExtractedEntity.source_kind.is_(None),
                ExtractedEntity.source_kind != "ocr_handwritten",
            ),
        )
        .all()
    )

    approved_count = 0
    for ee in pending_items:
        ee.status = "approved"
        ee.reviewed_by = current_user.id
        _commit_approved_entity(db, ee, current_user.id)
        approved_count += 1

    if approved_count > 0:
        db.commit()
        invalidate_case_graph(case.id)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="bulk_approve_entities",
        case_id=case.id,
        object_type="case",
        object_id=case.id,
        details={"threshold": threshold, "approved_count": approved_count},
    )

    return {"status": "success", "approved_count": approved_count, "threshold": threshold}
