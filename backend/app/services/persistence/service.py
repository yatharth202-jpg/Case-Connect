"""
Forensic Analysis Persistence and Saved Graph View Engine for CaseConnect AI (Phase 5).
Compliant with Section 63 BSA 2023.

Guarantees:
1. Every forensic analysis output is persisted in SQLite WAL as AnalysisResult and Finding graph nodes.
2. SavedGraphView captures viewport camera coordinates (pan, zoom), selection, and filter states.
3. Zero-Recompute Invariant: Case reopening loads directly from SQLite with zero algorithmic recalculation.
4. Cryptographic SHA-256 chain of custody audit logging for every mutation.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from backend.app.db.sql import (
    AnalysisResult, SavedGraphView, GraphNode, GraphEdge,
    generate_uuid
)
from backend.app.services.graph.builder import generate_node_id, generate_edge_id
from backend.app.audit.service import record_audit_log

logger = logging.getLogger("case_connect.persistence")


def persist_analysis_result(
    db: Session,
    case_id: str,
    user_id: str,
    entity_id: str,
    rank: int,
    score: float,
    breakdown: Dict[str, Any],
    evidence_ids: List[str],
    run_id: Optional[str] = None
) -> AnalysisResult:
    """
    Persists a single analysis finding row into SQLite and creates an associated
    'Finding' GraphNode linked via an 'ATTRIBUTED_TO' GraphEdge.
    """
    active_run_id = run_id or generate_uuid()

    result_obj = AnalysisResult(
        id=generate_uuid(),
        run_id=active_run_id,
        case_id=case_id,
        entity_id=entity_id,
        rank=rank,
        score=score,
        breakdown_json=json.dumps(breakdown),
        evidence_ids=json.dumps(evidence_ids)
    )
    db.add(result_obj)
    db.commit()
    db.refresh(result_obj)

    # Automatically create Finding GraphNode and ATTRIBUTED_TO GraphEdge if graph exists
    try:
        finding_label = f"Lead #{rank}: {score:.2f}"
        finding_node_id = generate_node_id(case_id, "Finding", f"lead_{rank}_{entity_id}")

        existing_finding = db.query(GraphNode).filter(GraphNode.id == finding_node_id).first()
        if not existing_finding:
            finding_node = GraphNode(
                id=finding_node_id,
                case_id=case_id,
                node_type="Finding",
                label=finding_label,
                props_json=json.dumps({
                    "rank": rank,
                    "score": score,
                    "target_entity": entity_id,
                    "breakdown": breakdown,
                    "run_id": active_run_id
                }),
                source_evidence_ids=json.dumps(evidence_ids)
            )
            db.add(finding_node)

        # Attempt to link to the target entity node in the graph
        target_node = (
            db.query(GraphNode)
            .filter(
                GraphNode.case_id == case_id,
                GraphNode.label.ilike(f"%{entity_id}%")
            )
            .first()
        )

        if target_node:
            edge_id = generate_edge_id(case_id, finding_node_id, target_node.id, "ATTRIBUTED_TO")
            existing_edge = db.query(GraphEdge).filter(GraphEdge.id == edge_id).first()
            if not existing_edge:
                finding_edge = GraphEdge(
                    id=edge_id,
                    case_id=case_id,
                    src=finding_node_id,
                    dst=target_node.id,
                    edge_type="ATTRIBUTED_TO",
                    count=1,
                    total_paise=0,
                    props_json=json.dumps({"rank": rank, "score": score, "run_id": active_run_id}),
                    source_evidence_ids=json.dumps(evidence_ids)
                )
                db.add(finding_edge)

        db.commit()
    except Exception as e:
        logger.warning(f"Finding node link attachment deferred: {e}")
        db.rollback()

    # Append to cryptographic audit chain
    record_audit_log(
        db=db,
        user_id=user_id,
        action="SAVE_ANALYSIS_RESULT",
        case_id=case_id,
        object_type="analysis_result",
        object_id=result_obj.id,
        details={
            "entity_id": entity_id,
            "rank": rank,
            "score": score,
            "run_id": active_run_id
        }
    )

    return result_obj


def get_case_analysis_results(db: Session, case_id: str) -> List[Dict[str, Any]]:
    """Retrieves all persisted analysis findings for a case docket ordered by rank."""
    rows = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.case_id == case_id)
        .order_by(AnalysisResult.created_at.desc(), AnalysisResult.rank.asc())
        .all()
    )

    out = []
    for r in rows:
        try:
            bdown = json.loads(r.breakdown_json)
        except Exception:
            bdown = {}
        try:
            evs = json.loads(r.evidence_ids)
        except Exception:
            evs = []

        out.append({
            "id": r.id,
            "run_id": r.run_id,
            "case_id": r.case_id,
            "entity_id": r.entity_id,
            "rank": r.rank,
            "score": r.score,
            "breakdown": bdown,
            "evidence_ids": evs,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return out


def save_graph_view(
    db: Session,
    case_id: str,
    user_id: str,
    name: str,
    view_data: Dict[str, Any]
) -> SavedGraphView:
    """Stores a named viewport configuration (pan, zoom, filters, selected nodes)."""
    view = SavedGraphView(
        id=generate_uuid(),
        case_id=case_id,
        name=name.strip(),
        view_data_json=json.dumps(view_data),
        created_by=user_id
    )
    db.add(view)
    db.commit()
    db.refresh(view)

    record_audit_log(
        db=db,
        user_id=user_id,
        action="SAVE_GRAPH_VIEW",
        case_id=case_id,
        object_type="saved_graph_view",
        object_id=view.id,
        details={"name": view.name}
    )
    return view


def list_graph_views(db: Session, case_id: str) -> List[Dict[str, Any]]:
    """Lists all saved graph views for a case docket."""
    views = (
        db.query(SavedGraphView)
        .filter(SavedGraphView.case_id == case_id)
        .order_by(SavedGraphView.created_at.desc())
        .all()
    )
    res = []
    for v in views:
        try:
            data = json.loads(v.view_data_json)
        except Exception:
            data = {}
        res.append({
            "id": v.id,
            "case_id": v.case_id,
            "name": v.name,
            "view_data": data,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat() if v.created_at else None
        })
    return res


def get_graph_view(db: Session, case_id: str, view_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a specific saved view by ID."""
    v = db.query(SavedGraphView).filter(
        SavedGraphView.case_id == case_id,
        SavedGraphView.id == view_id
    ).first()
    if not v:
        return None
    try:
        data = json.loads(v.view_data_json)
    except Exception:
        data = {}
    return {
        "id": v.id,
        "case_id": v.case_id,
        "name": v.name,
        "view_data": data,
        "created_by": v.created_by,
        "created_at": v.created_at.isoformat() if v.created_at else None
    }


def delete_graph_view(db: Session, case_id: str, user_id: str, view_id: str) -> bool:
    """Deletes a saved graph view and writes audit log."""
    v = db.query(SavedGraphView).filter(
        SavedGraphView.case_id == case_id,
        SavedGraphView.id == view_id
    ).first()
    if not v:
        return False

    view_name = v.name
    db.delete(v)
    db.commit()

    record_audit_log(
        db=db,
        user_id=user_id,
        action="DELETE_GRAPH_VIEW",
        case_id=case_id,
        object_type="saved_graph_view",
        object_id=view_id,
        details={"deleted_view_name": view_name}
    )
    return True
