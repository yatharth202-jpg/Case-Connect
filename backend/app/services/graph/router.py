import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.db.sql import get_db, Case, EntityLink, User
from backend.app.auth.deps import get_current_user, require_role
from backend.app.cases.deps import get_case_for_user
from backend.app.services.graph.builder import (
    build_detail_graph, CASE_GRAPH_CACHE, invalidate_case_graph
)
from backend.app.services.graph.projection import (
    build_entity_projection, expand_hops_subgraph, find_shortest_path_nodes
)
from backend.app.audit.service import record_audit_log

router = APIRouter()

class CreateLinkRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str
    link_type: str = "USES" # USES, OWNS, DRIVES

def get_or_build_case_graphs(db: Session, case_id: str):
    """Retrieves or builds cached (detail_graph, entity_graph) for a case."""
    if case_id in CASE_GRAPH_CACHE:
        return CASE_GRAPH_CACHE[case_id]

    detail_g = build_detail_graph(db, case_id)
    entity_g = build_entity_projection(detail_g)
    CASE_GRAPH_CACHE[case_id] = (detail_g, entity_g)
    return detail_g, entity_g

@router.get("/cases/{case_id}/graph/search")
def search_case_graph(
    case_id: str,
    q: Optional[str] = Query(None),
    hops: int = Query(1, ge=1, le=4),
    view: str = Query("entity", pattern="^(entity|detail)$"),
    limit: int = Query(200, ge=10, le=500),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search and hop-expand nodes in the investigation graph.
    - q: search query matching name, phone, account, or vehicle.
    - hops: 1 to 4 entity hops.
    - view: 'entity' (collapsed owners & flows) or 'detail' (granular records).
    """
    detail_g, entity_g = get_or_build_case_graphs(db, case.id)
    active_graph = entity_g if view == "entity" else detail_g

    if active_graph.number_of_nodes() == 0:
        return {
            "nodes": [],
            "edges": [],
            "focus_node": None,
            "candidates": [],
            "truncated": False,
            "view": view,
            "hops": hops
        }

    # 1. Search candidate nodes matching q
    candidates = []
    if q and q.strip():
        q_norm = q.strip().lower()
        for node_key in active_graph.nodes():
            nd = active_graph.nodes[node_key]
            node_id = str(nd.get("id") or "").lower()
            node_name = str(nd.get("name") or "").lower()

            if q_norm == node_id or q_norm == node_name:
                candidates.insert(0, {"key": node_key, "name": nd.get("name"), "id": nd.get("id"), "label": nd.get("label"), "degree": nd.get("degree", 0)})
            elif q_norm in node_id or q_norm in node_name:
                candidates.append({"key": node_key, "name": nd.get("name"), "id": nd.get("id"), "label": nd.get("label"), "degree": nd.get("degree", 0)})

    # If multiple candidates and exact seed not unambiguous
    if len(candidates) > 1 and q and not any(c["id"].lower() == q.strip().lower() for c in candidates):
        return {
            "nodes": [],
            "edges": [],
            "focus_node": None,
            "candidates": candidates[:15],
            "truncated": False,
            "view": view,
            "hops": hops
        }

    # Determine seed keys
    if candidates:
        seed_keys = [candidates[0]["key"]]
        focus_node = candidates[0]
    elif q:
        # No matches found
        return {
            "nodes": [],
            "edges": [],
            "focus_node": None,
            "candidates": [],
            "truncated": False,
            "view": view,
            "hops": hops
        }
    else:
        # Default: pick top 3 highest degree nodes
        sorted_nodes = sorted(active_graph.nodes(data=True), key=lambda x: x[1].get("degree", 0), reverse=True)
        seed_keys = [n[0] for n in sorted_nodes[:3]]
        focus_node = {"key": seed_keys[0], "name": sorted_nodes[0][1].get("name"), "label": sorted_nodes[0][1].get("label")} if seed_keys else None

    nodes, edges, truncated = expand_hops_subgraph(active_graph, seed_keys, hops=hops, limit=limit)

    return {
        "nodes": nodes,
        "edges": edges,
        "focus_node": focus_node,
        "candidates": [],
        "truncated": truncated,
        "view": view,
        "hops": hops
    }

@router.get("/cases/{case_id}/graph/path")
def find_graph_path(
    case_id: str,
    from_key: str = Query(...),
    to_key: str = Query(...),
    view: str = Query("entity", pattern="^(entity|detail)$"),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculates shortest entity/detail connection path between two nodes (capped at 6 hops)."""
    detail_g, entity_g = get_or_build_case_graphs(db, case.id)
    active_graph = entity_g if view == "entity" else detail_g

    path_keys = find_shortest_path_nodes(active_graph, from_key, to_key)
    if not path_keys:
        return {"path_nodes": [], "path_edges": [], "found": False}

    subg = active_graph.subgraph(path_keys)
    nodes_res = [dict(subg.nodes[n], key=n) for n in path_keys]
    edges_res = []
    for u, v, k, d in subg.edges(keys=True, data=True):
        e_dict = dict(d)
        e_dict["source"] = u
        e_dict["target"] = v
        edges_res.append(e_dict)

    return {
        "path_nodes": nodes_res,
        "path_edges": edges_res,
        "found": True,
        "length": len(path_keys) - 1
    }

@router.post("/cases/{case_id}/links")
def create_officer_link(
    case_id: str,
    req: CreateLinkRequest,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Creates manual officer link between person and phone/account, re-projecting the graph."""
    link = EntityLink(
        case_id=case.id,
        source_entity_id=req.source_entity_id.strip(),
        target_entity_id=req.target_entity_id.strip(),
        relationship_type=req.link_type,
        properties_json=json.dumps({"officer_notes": "Officer investigation link"}),
        source_file="Officer Annotation",
        source_ref=current_user.id,
        method="officer",
        confidence=1.0,
        approved_by=current_user.id
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    invalidate_case_graph(case.id)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="create_link",
        case_id=case.id,
        object_type="entity_link",
        object_id=link.id,
        details={"source": req.source_entity_id, "target": req.target_entity_id, "type": req.link_type}
    )

    return {"status": "created", "link_id": link.id}

@router.delete("/cases/{case_id}/links/{link_id}")
def delete_officer_link(
    case_id: str,
    link_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Deletes officer link and restores original graph projection."""
    link = db.query(EntityLink).filter(EntityLink.id == link_id, EntityLink.case_id == case.id).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    db.delete(link)
    db.commit()

    invalidate_case_graph(case.id)

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="delete_link",
        case_id=case.id,
        object_type="entity_link",
        object_id=link_id,
        details={"deleted_link_id": link_id}
    )

    return {"status": "deleted", "link_id": link_id}

@router.post("/cases/{case_id}/graph/rebuild")
def rebuild_graph(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(require_role(["admin", "investigator"])),
    db: Session = Depends(get_db)
):
    """Forces fresh re-projection of the graph from SQLite staging tables."""
    invalidate_case_graph(case.id)
    detail_g, entity_g = get_or_build_case_graphs(db, case.id)
    return {
        "status": "rebuilt",
        "case_id": case.id,
        "detail_nodes": detail_g.number_of_nodes(),
        "detail_edges": detail_g.number_of_edges(),
        "entity_nodes": entity_g.number_of_nodes(),
        "entity_edges": entity_g.number_of_edges()
    }
