import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    get_db, Case, EvidenceFile, ExtractedEntity, Entity, EntityLink, User
)
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.audit.service import record_audit_log
from backend.app.services.graph.builder import invalidate_case_graph
from backend.app.services.extraction.text import read_document_text
from backend.app.services.extraction.pipeline import run_document_extraction

router = APIRouter()

class PatchExtractedRequest(BaseModel):
    status: Optional[str] = None # "approved", "rejected", "pending_review"
    normalized_value: Optional[str] = None

class CreateManualExtractedRequest(BaseModel):
    evidence_id: str
    entity_type: str
    raw_value: str
    normalized_value: str
    page_or_paragraph: str = "Manual Entry"
    confidence: float = 1.0

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
            link = EntityLink(
                case_id=ee.case_id,
                source_entity_id=rel_info["source"],
                target_entity_id=rel_info["target"],
                relationship_type=rel_info.get("relationship_type", "USES"),
                properties_json=json.dumps({"sentence": rel_info.get("sentence", "")}),
                source_file=src_file,
                source_ref=ee.page_or_paragraph,
                method="nlp_relationship",
                confidence=ee.confidence,
                approved_by=user_id
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
            "ORGANIZATION": "Organization"
        }
        label = label_map.get(ee.entity_type)
        if label:
            # Check if entity node already staged
            existing_ent = db.query(Entity).filter(
                Entity.case_id == ee.case_id,
                Entity.label == label,
                Entity.canonical_id == ee.normalized_value
            ).first()

            if not existing_ent:
                ent = Entity(
                    case_id=ee.case_id,
                    label=label,
                    canonical_id=ee.normalized_value,
                    display_name=ee.raw_value if label in ["Person", "Organization", "FIR"] else ee.normalized_value,
                    properties_json=json.dumps({"raw_value": ee.raw_value, "evidence_id": ee.evidence_id}),
                    source_file=src_file,
                    source_ref=ee.page_or_paragraph,
                    method="document_nlp",
                    confidence=ee.confidence
                )
                db.add(ent)

            # If person approved in an FIR document: link person to FIR
            if label == "Person":
                fir_entity = db.query(ExtractedEntity).filter(
                    ExtractedEntity.evidence_id == ee.evidence_id,
                    ExtractedEntity.entity_type == "FIR",
                    ExtractedEntity.status == "approved"
                ).first()

                if fir_entity:
                    existing_link = db.query(EntityLink).filter(
                        EntityLink.case_id == ee.case_id,
                        EntityLink.source_entity_id == ee.normalized_value,
                        EntityLink.target_entity_id == fir_entity.normalized_value,
                        EntityLink.relationship_type == "MENTIONED_IN"
                    ).first()
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
                            approved_by=user_id
                        )
                        db.add(fir_link)

            elif label == "FIR":
                # If FIR approved, link all already approved Persons in same document
                approved_persons = db.query(ExtractedEntity).filter(
                    ExtractedEntity.evidence_id == ee.evidence_id,
                    ExtractedEntity.entity_type == "PERSON",
                    ExtractedEntity.status == "approved"
                ).all()
                for p in approved_persons:
                    existing_link = db.query(EntityLink).filter(
                        EntityLink.case_id == ee.case_id,
                        EntityLink.source_entity_id == p.normalized_value,
                        EntityLink.target_entity_id == ee.normalized_value,
                        EntityLink.relationship_type == "MENTIONED_IN"
                    ).first()
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
                            approved_by=user_id
                        )
                        db.add(fir_link)

@router.post("/evidence/{evidence_id}/extract")
def extract_evidence_document(
    evidence_id: str,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Executes NLP extraction pipeline on an uploaded text/document evidence file."""
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found")

    res = run_document_extraction(db, ev.id, ev.case_id, ev.stored_path)
    if res.get("status") == "failed":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=res["error"])

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="document_extract",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={"total_extracted": res["total_extracted"]}
    )

    return res

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
    db: Session = Depends(get_db)
):
    """Lists extracted entities from case documents with status, type, and confidence filtering."""
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
    items = q.order_by(ExtractedEntity.confidence.desc(), ExtractedEntity.char_span_start.asc()).offset(offset).limit(limit).all()

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
                "char_span_start": e.char_span_start,
                "char_span_end": e.char_span_end,
                "confidence": e.confidence,
                "method": e.method,
                "status": e.status,
                "reviewed_by": e.reviewed_by
            }
            for e in items
        ]
    }

@router.get("/evidence/{evidence_id}/text")
def get_evidence_document_text(
    evidence_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns document pages/paragraphs with annotated entity character spans
    for interactive document highlighting in the review interface.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    doc_data = read_document_text(ev.stored_path)
    if doc_data.get("error"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=doc_data["error"])

    # Attach extracted entities for this evidence
    entities = db.query(ExtractedEntity).filter(ExtractedEntity.evidence_id == evidence_id).all()
    ent_list = [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "raw_value": e.raw_value,
            "normalized_value": e.normalized_value,
            "page_or_paragraph": e.page_or_paragraph,
            "char_span_start": e.char_span_start,
            "char_span_end": e.char_span_end,
            "confidence": e.confidence,
            "status": e.status
        }
        for e in entities
    ]

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "pages": doc_data["pages"],
        "full_text": doc_data["full_text"],
        "entities": ent_list,
        "warning": doc_data.get("warning")
    }

@router.patch("/extracted/{extracted_id}")
def update_extracted_entity(
    extracted_id: str,
    req: PatchExtractedRequest,
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
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
        details={"type": ee.entity_type, "value": ee.normalized_value, "status": ee.status}
    )

    return {"status": ee.status, "id": ee.id, "normalized_value": ee.normalized_value}

@router.post("/cases/{case_id}/extracted")
def create_manual_extracted_entity(
    case_id: str,
    req: CreateManualExtractedRequest,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Allows an investigator to manually tag a missing entity from document text."""
    ee = ExtractedEntity(
        evidence_id=req.evidence_id,
        case_id=case.id,
        entity_type=req.entity_type.upper(),
        raw_value=req.raw_value.strip(),
        normalized_value=req.normalized_value.strip(),
        page_or_paragraph=req.page_or_paragraph,
        char_span_start=0,
        char_span_end=len(req.raw_value),
        confidence=1.0,
        method="officer",
        status="approved",
        reviewed_by=current_user.id
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
        details={"type": req.entity_type, "value": req.normalized_value}
    )

    return {"status": "created_and_approved", "id": ee.id}

@router.post("/cases/{case_id}/extracted/approve-all")
def bulk_approve_extracted_entities(
    case_id: str,
    threshold: float = Query(0.8, ge=0.1, le=1.0),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Bulk-approves all pending entities meeting the confidence threshold and stages them to the graph."""
    pending_items = db.query(ExtractedEntity).filter(
        ExtractedEntity.case_id == case.id,
        ExtractedEntity.status == "pending_review",
        ExtractedEntity.confidence >= threshold
    ).all()

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
        details={"threshold": threshold, "approved_count": approved_count}
    )

    return {"status": "success", "approved_count": approved_count, "threshold": threshold}
