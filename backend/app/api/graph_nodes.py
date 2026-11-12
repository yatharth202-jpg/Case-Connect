"""
Forensic Graph Topological Nodes & Inspection Router for CaseConnect AI (Phase 4 Upgrade).
Compliant with Section 63 BSA 2023.

Provides:
- GET /cases/{id}/graph/node/{node_id}: Full neighbour inspection grouped by type with pagination
  and notices like 'showing 200 of 5,431'.
- GET /cases/{id}/graph/config: Dynamic node & edge style configurations (colors, shapes, icons).
- GET /cases/{id}/graph/nodes: Capped initial Cytoscape topology with search and type filters.
- POST /cases/{id}/graph/rebuild: Triggers authoritative SQLite graph rebuild & disposable projections.
"""

import json
from math import ceil
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.db.sql import (
    get_db, Case, User, GraphNode, GraphEdge, NodeTypeConfig, EdgeTypeConfig
)
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.services.graph.builder import rebuild_graph, ensure_graph_configs_seeded
from backend.app.services.excel_export import format_paise_to_inr_text

router = APIRouter()


@router.get("/cases/{case_id}/graph/config", summary="Retrieve Graph Styles and Legend Configuration")
def get_graph_config(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Returns data-agnostic style definitions for node types and edge types.
    Adding a config row to NodeTypeConfig immediately styles new entity types
    with zero frontend or backend code changes.
    """
    ensure_graph_configs_seeded(db)

    node_types = db.query(NodeTypeConfig).filter(NodeTypeConfig.is_active.is_(True)).all()
    edge_types = db.query(EdgeTypeConfig).filter(EdgeTypeConfig.is_active.is_(True)).all()

    return {
        "case_id": case.id,
        "node_types": [
            {
                "type_name": nt.type_name,
                "label": nt.label,
                "color": nt.color,
                "icon": nt.icon,
                "shape": nt.shape,
                "score_weight": nt.score_weight,
            }
            for nt in node_types
        ],
        "edge_types": [
            {
                "type_name": et.type_name,
                "label": et.label,
                "color": et.color,
                "line_style": et.line_style,
                "directional": et.directional,
            }
            for et in edge_types
        ],
    }


@router.post("/cases/{case_id}/graph/rebuild", summary="Trigger Authoritative Graph Rebuild")
def rebuild_case_graph_endpoint(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Idempotently rebuilds the graph topology from SQLite source records,
    persisting into graph_nodes and graph_edges, with projections to NetworkX and Neo4j.
    """
    try:
        result = rebuild_graph(db, case.id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Graph rebuild failed: {str(e)}"
        )


@router.get("/cases/{case_id}/graph/nodes", summary="Fetch Cytoscape Graph Topology")
def get_graph_topology(
    case_id: str,
    limit: int = Query(300, ge=10, le=2000, description="Capped initial render node count"),
    q: Optional[str] = Query(None, description="Search query to filter nodes by label"),
    node_type: Optional[str] = Query(None, description="Filter nodes by type"),
    min_weight: Optional[int] = Query(None, description="Filter edges by minimum transaction paise or count"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Returns capped initial nodes and active edges formatted for Cytoscape elements,
    with node styles derived from dynamic configuration.
    """
    ensure_graph_configs_seeded(db)

    # If graph is empty in SQLite, run initial rebuild
    existing_count = db.query(GraphNode).filter(GraphNode.case_id == case.id).count()
    if existing_count == 0:
        rebuild_graph(db, case.id)

    # Style mapping
    node_configs = {
        nt.type_name: nt for nt in db.query(NodeTypeConfig).filter(NodeTypeConfig.is_active.is_(True)).all()
    }
    edge_configs = {
        et.type_name: et for et in db.query(EdgeTypeConfig).filter(EdgeTypeConfig.is_active.is_(True)).all()
    }

    # Query Nodes
    node_q = db.query(GraphNode).filter(GraphNode.case_id == case.id)
    if node_type:
        node_q = node_q.filter(GraphNode.node_type == node_type)
    if q and q.strip():
        node_q = node_q.filter(GraphNode.label.ilike(f"%{q.strip()}%"))

    nodes = node_q.limit(limit).all()
    rendered_node_ids = set(n.id for n in nodes)

    # Query Edges connecting these rendered nodes
    if rendered_node_ids:
        edge_q = db.query(GraphEdge).filter(
            GraphEdge.case_id == case.id,
            GraphEdge.src.in_(rendered_node_ids),
            GraphEdge.dst.in_(rendered_node_ids)
        )
        if min_weight is not None and min_weight > 0:
            edge_q = edge_q.filter(or_(GraphEdge.count >= min_weight, GraphEdge.total_paise >= min_weight))
        edges = edge_q.all()
    else:
        edges = []

    # Format Cytoscape elements
    elements = []
    for n in nodes:
        style = node_configs.get(n.node_type)
        color = style.color if style else "#64748B"
        shape = style.shape if style else "ellipse"
        try:
            props = json.loads(n.props_json or "{}")
        except Exception:
            props = {}

        elements.append({
            "group": "nodes",
            "data": {
                "id": n.id,
                "label": n.label,
                "node_type": n.node_type,
                "color": color,
                "shape": shape,
                "props": props,
            }
        })

    for e in edges:
        style = edge_configs.get(e.edge_type)
        color = style.color if style else "#64748B"
        line_style = style.line_style if style else "solid"

        elements.append({
            "group": "edges",
            "data": {
                "id": e.id,
                "source": e.src,
                "target": e.dst,
                "edge_type": e.edge_type,
                "count": e.count,
                "total_paise": e.total_paise,
                "total_inr": format_paise_to_inr_text(e.total_paise),
                "color": color,
                "line_style": line_style,
                "first_seen": e.first_seen.isoformat() if e.first_seen else None,
                "last_seen": e.last_seen.isoformat() if e.last_seen else None,
            }
        })

    return {
        "case_id": case.id,
        "nodes_count": len(nodes),
        "edges_count": len(edges),
        "total_case_nodes": existing_count,
        "elements": elements,
    }


@router.get("/cases/{case_id}/graph/node/{node_id}", summary="Inspect Node Direct Neighbours")
def get_node_neighbours(
    case_id: str,
    node_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    type_filter: Optional[str] = Query(None, description="Optional filter by neighbour node type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    case: Case = Depends(get_case_for_user),
):
    """
    Inspects a single graph node and returns ALL direct neighbours grouped by type,
    with edge weights, total transaction volume, first/last seen, source evidence files,
    and structured pagination with human-readable notice.
    """
    node = db.query(GraphNode).filter(
        GraphNode.id == node_id,
        GraphNode.case_id == case.id
    ).first()

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {node_id} not found in case {case.id}."
        )

    try:
        node_props = json.loads(node.props_json or "{}")
    except Exception:
        node_props = {}
    try:
        node_sources = json.loads(node.source_evidence_ids or "[]")
    except Exception:
        node_sources = []

    # Find all edges touching this node
    edges = db.query(GraphEdge).filter(
        GraphEdge.case_id == case.id,
        or_(GraphEdge.src == node_id, GraphEdge.dst == node_id)
    ).all()

    # Determine unique neighbor IDs
    neighbor_edge_map: Dict[str, List[GraphEdge]] = {}
    for e in edges:
        nbr_id = e.dst if e.src == node_id else e.src
        neighbor_edge_map.setdefault(nbr_id, []).append(e)

    # Fetch neighbour node details
    neighbour_nodes = db.query(GraphNode).filter(
        GraphNode.case_id == case.id,
        GraphNode.id.in_(list(neighbor_edge_map.keys()))
    ).all()

    if type_filter:
        neighbour_nodes = [n for n in neighbour_nodes if n.node_type.lower() == type_filter.strip().lower()]

    # Sort neighbours deterministically: by node_type, then label
    neighbour_nodes.sort(key=lambda x: (x.node_type, x.label))

    total_neighbours = len(neighbour_nodes)
    total_pages = ceil(total_neighbours / page_size) if total_neighbours > 0 else 1
    offset = (page - 1) * page_size
    paged_neighbours = neighbour_nodes[offset : offset + page_size]

    # Group paged neighbours by type
    grouped_neighbours: Dict[str, List[Dict[str, Any]]] = {}
    for nbr in paged_neighbours:
        nbr_edges = neighbor_edge_map.get(nbr.id, [])
        edges_summary = []
        for eg in nbr_edges:
            direction = "OUTGOING" if eg.src == node_id else "INCOMING"
            try:
                e_sources = json.loads(eg.source_evidence_ids or "[]")
            except Exception:
                e_sources = []
            try:
                e_props = json.loads(eg.props_json or "{}")
            except Exception:
                e_props = {}

            edges_summary.append({
                "edge_id": eg.id,
                "edge_type": eg.edge_type,
                "direction": direction,
                "count": eg.count,
                "total_paise": eg.total_paise,
                "total_inr": format_paise_to_inr_text(eg.total_paise),
                "first_seen": eg.first_seen.isoformat() if eg.first_seen else None,
                "last_seen": eg.last_seen.isoformat() if eg.last_seen else None,
                "source_evidence_ids": e_sources,
                "properties": e_props,
            })

        try:
            nbr_props = json.loads(nbr.props_json or "{}")
        except Exception:
            nbr_props = {}
        try:
            nbr_sources = json.loads(nbr.source_evidence_ids or "[]")
        except Exception:
            nbr_sources = []

        item = {
            "node_id": nbr.id,
            "label": nbr.label,
            "node_type": nbr.node_type,
            "props": nbr_props,
            "source_evidence_ids": nbr_sources,
            "connections": edges_summary,
        }
        grouped_neighbours.setdefault(nbr.node_type, []).append(item)

    notice = f"showing {len(paged_neighbours)} of {total_neighbours}"

    return {
        "case_id": case.id,
        "node": {
            "id": node.id,
            "node_type": node.node_type,
            "label": node.label,
            "props": node_props,
            "source_evidence_ids": node_sources,
        },
        "total_neighbours": total_neighbours,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "notice": notice,
        "grouped_neighbours": grouped_neighbours,
    }
