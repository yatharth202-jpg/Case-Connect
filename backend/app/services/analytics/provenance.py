import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.app.db.sql import (
    Entity, EntityLink, EvidenceFile, CallRecord, Transaction, ExtractedEntity, User
)

def get_provenance_details(
    db: Session,
    case_id: str,
    node_id: Optional[str] = None,
    edge_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes forensic evidentiary provenance ('Why this link?' / 'Why this node?').
    Returns source file name, row/page indices, stream SHA-256 hash, extraction method,
    confidence rating, and underlying transaction or call records.
    """
    # 1. NODE PROVENANCE
    if node_id:
        ent = db.query(Entity).filter(
            Entity.case_id == case_id,
            or_(Entity.id == node_id, Entity.canonical_id == node_id)
        ).first()

        if not ent:
            # Fallback: check if it's a known phone or account
            return {
                "target_type": "node",
                "id": node_id,
                "label": "Unknown",
                "display_name": node_id,
                "found": False,
                "explanation": f"Node {node_id} does not have an explicit staging record in this case."
            }

        # Look up source evidence file
        ev = db.query(EvidenceFile).filter(
            EvidenceFile.case_id == case_id,
            EvidenceFile.original_name == ent.source_file
        ).first()

        # Check if node was extracted from document narrative
        doc_ext = db.query(ExtractedEntity).filter(
            ExtractedEntity.case_id == case_id,
            ExtractedEntity.normalized_value == ent.canonical_id
        ).first()

        # Count incident links
        degree = db.query(EntityLink).filter(
            EntityLink.case_id == case_id,
            or_(EntityLink.source_entity_id == ent.canonical_id, EntityLink.target_entity_id == ent.canonical_id)
        ).count()

        return {
            "target_type": "node",
            "found": True,
            "id": ent.id,
            "canonical_id": ent.canonical_id,
            "label": ent.label,
            "display_name": ent.display_name or ent.canonical_id,
            "source_file": ent.source_file or "Document",
            "source_ref": ent.source_ref or "Staged Record",
            "evidence_sha256": ev.sha256 if ev else "N/A",
            "evidence_type": ev.detected_type if ev else "structured",
            "method": ent.method or "structured",
            "confidence": ent.confidence if ent.confidence is not None else 1.0,
            "degree": degree,
            "document_provenance": {
                "page_or_paragraph": doc_ext.page_or_paragraph if doc_ext else None,
                "raw_text_mention": doc_ext.raw_value if doc_ext else None,
                "status": doc_ext.status if doc_ext else None
            } if doc_ext else None,
            "explanation": f"Entity '{ent.display_name or ent.canonical_id}' identified via {ent.method} in source file {ent.source_file} (ref: {ent.source_ref})."
        }

    # 2. EDGE PROVENANCE
    if edge_id:
        link = db.query(EntityLink).filter(
            EntityLink.case_id == case_id,
            or_(
                EntityLink.id == edge_id,
                and_(EntityLink.source_entity_id == edge_id.split("|")[0], EntityLink.target_entity_id == edge_id.split("|")[-1]) if "|" in edge_id else False
            )
        ).first()

        if not link and "|" in edge_id:
            parts = edge_id.split("|")
            if len(parts) >= 2:
                src, tgt = parts[0], parts[-1]
                link = db.query(EntityLink).filter(
                    EntityLink.case_id == case_id,
                    or_(
                        and_(EntityLink.source_entity_id == src, EntityLink.target_entity_id == tgt),
                        and_(EntityLink.source_entity_id == tgt, EntityLink.target_entity_id == src)
                    )
                ).first()

        src_id = link.source_entity_id if link else (edge_id.split("|")[0] if "|" in edge_id else "Source")
        tgt_id = link.target_entity_id if link else (edge_id.split("|")[-1] if "|" in edge_id else "Target")
        rel_type = link.relationship_type if link else "CONNECTED_TO"

        # Look up source evidence file
        ev = None
        if link and link.source_file:
            ev = db.query(EvidenceFile).filter(
                EvidenceFile.case_id == case_id,
                EvidenceFile.original_name == link.source_file
            ).first()

        approver_name = None
        if link and link.approved_by:
            u = db.query(User).filter(User.id == link.approved_by).first()
            approver_name = u.username if u else "Officer"

        # Check for underlying financial transactions
        underlying_txns = db.query(Transaction).filter(
            Transaction.case_id == case_id,
            or_(
                and_(Transaction.from_account == src_id, Transaction.to_account == tgt_id),
                and_(Transaction.from_account == tgt_id, Transaction.to_account == src_id)
            )
        ).order_by(Transaction.amount_paise.desc()).limit(15).all()

        txn_records = [
            {
                "id": t.id,
                "from_account": t.from_account,
                "to_account": t.to_account,
                "amount_paise": t.amount_paise,
                "amount_rs": f"Rs. {(t.amount_paise / 100):,.2f}",
                "date_iso": t.date_iso,
                "source_file": t.source_file,
                "source_ref": t.source_ref,
                "fingerprint": t.fingerprint
            }
            for t in underlying_txns
        ]

        # Check for underlying telecommunication calls
        underlying_calls = db.query(CallRecord).filter(
            CallRecord.case_id == case_id,
            or_(
                and_(CallRecord.caller == src_id, CallRecord.receiver == tgt_id),
                and_(CallRecord.caller == tgt_id, CallRecord.receiver == src_id)
            )
        ).order_by(CallRecord.duration_seconds.desc()).limit(15).all()

        call_records_list = [
            {
                "id": c.id,
                "caller": c.caller,
                "receiver": c.receiver,
                "duration_seconds": c.duration_seconds,
                "datetime_iso": c.datetime_iso or c.call_date,
                "source_file": c.source_file,
                "source_ref": c.source_ref
            }
            for c in underlying_calls
        ]

        return {
            "target_type": "edge",
            "found": True,
            "id": link.id if link else edge_id,
            "source": src_id,
            "target": tgt_id,
            "relationship_type": rel_type,
            "source_file": link.source_file if link else (ev.original_name if ev else "Data Repository"),
            "source_ref": link.source_ref if link else "Aggregated",
            "evidence_sha256": ev.sha256 if ev else "N/A",
            "method": link.method if link else "analytical_derived",
            "confidence": link.confidence if link and link.confidence is not None else 0.95,
            "approved_by": approver_name,
            "underlying_transactions_count": len(underlying_txns),
            "underlying_transactions": txn_records,
            "underlying_calls_count": len(underlying_calls),
            "underlying_calls": call_records_list,
            "explanation": (
                f"Relationship '{rel_type}' between {src_id} and {tgt_id} substantiated by "
                f"{len(underlying_txns)} financial transfer(s) and {len(underlying_calls)} call record(s)."
            )
        }

    return {
        "target_type": "none",
        "found": False,
        "explanation": "Provide either node_id or edge_id parameter for forensic provenance inspection."
    }
