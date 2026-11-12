"""
Forensic Graph Topological Rebuild and Projection Engine for CaseConnect AI (Phase 4 Upgrade).
Compliant with Section 63 BSA 2023.

Prime Architectural Directives:
1. SQLite WAL is the sole authoritative source of truth:
   graph_nodes and graph_edges are stored deterministically in SQLite first.
2. Neo4j and NetworkX are disposable projections rebuilt from SQLite via rebuild_graph(case_id).
3. If Neo4j is offline, gracefully fall back to NetworkX/SQLite with clear diagnostic reporting.
4. Stable node IDs: hash of case_id + node_type + normalized label.
5. Edge Aggregation: Multiple interactions between the same node pair aggregate into a single edge
   (total count, total paise as 64-bit integer, first/last seen, evidence links).
6. Config-Driven: Node and edge types dynamically loaded from NodeTypeConfig/EdgeTypeConfig tables
   with fallback to seed defaults.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

import yaml
import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.sql import (
    CallRecord, Transaction, IPEvent, Entity, EntityLink, AnalysisResult,
    GraphNode, GraphEdge, NodeTypeConfig, EdgeTypeConfig, SystemConfig, Case
)
from backend.app.db.neo4j import check_neo4j_health, get_neo4j_driver
from backend.app.audit.service import record_audit_log

logger = logging.getLogger("case_connect.graph_builder")

# In-memory graph cache per case: { case_id: (detail_graph, entity_graph) }
CASE_GRAPH_CACHE: Dict[str, Tuple[nx.MultiDiGraph, nx.MultiGraph]] = {}

SEED_GRAPH_CONFIG_PATH = Path("backend") / "config" / "seed_graph_config.yaml"


def generate_node_id(case_id: str, node_type: str, label: str) -> str:
    """Computes a deterministic, collision-resistant node ID."""
    clean_type = node_type.strip()
    clean_label = label.strip().lower()
    raw = f"{case_id}:{clean_type}:{clean_label}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def generate_edge_id(case_id: str, src_id: str, dst_id: str, edge_type: str) -> str:
    """Computes a deterministic, collision-resistant edge ID."""
    clean_type = edge_type.strip().upper()
    raw = f"{case_id}:{src_id}:{dst_id}:{clean_type}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def to_datetime(val: Any) -> Optional[datetime]:
    """Safely converts ISO strings or date strings to python datetime objects for SQLite."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    val_str = str(val).strip()
    try:
        clean = val_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(val_str, fmt)
        except Exception:
            pass
    return None


def ensure_graph_configs_seeded(db: Session):
    """Seeds NodeTypeConfig and EdgeTypeConfig from seed_graph_config.yaml if empty."""
    node_count = db.query(NodeTypeConfig).count()
    if node_count == 0 and SEED_GRAPH_CONFIG_PATH.exists():
        try:
            with open(SEED_GRAPH_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            for nt in data.get("node_types", []):
                cfg = NodeTypeConfig(
                    type_name=nt["type_name"],
                    label=nt.get("label", nt["type_name"]),
                    color=nt.get("color", "#2563EB"),
                    icon=nt.get("icon", "circle"),
                    shape=nt.get("shape", "ellipse"),
                    score_weight=float(nt.get("score_weight", 1.0)),
                    is_active=True
                )
                db.add(cfg)

            for et in data.get("edge_types", []):
                cfg = EdgeTypeConfig(
                    type_name=et["type_name"],
                    label=et.get("label", et["type_name"]),
                    color=et.get("color", "#64748B"),
                    line_style=et.get("line_style", "solid"),
                    directional=bool(et.get("directional", True)),
                    is_active=True
                )
                db.add(cfg)

            db.commit()
        except Exception as e:
            logger.warning(f"Error seeding graph configs: {e}")
            db.rollback()


def invalidate_case_graph(case_id: str):
    """Evicts cached graph for a case to force fresh rebuild."""
    if case_id in CASE_GRAPH_CACHE:
        del CASE_GRAPH_CACHE[case_id]


def rebuild_graph(db: Session, case_id: str) -> Dict[str, Any]:
    """
    Authoritative Graph Rebuild Engine (Phase 4):
    1. Harvests CDR, Banking, IP, Entity, and Finding records for case_id.
    2. Builds stable, deterministic nodes and aggregates multi-events into single edges.
    3. Persists graph_nodes and graph_edges in SQLite WAL first (idempotent overwrite).
    4. Projects graph into NetworkX in-memory representation.
    5. Projects graph into Neo4j (if healthy; otherwise activates offline fallback).
    6. Appends cryptographic audit entry to SHA-256 genesis chain.
    """
    ensure_graph_configs_seeded(db)
    invalidate_case_graph(case_id)

    # Temporary collector dictionaries
    # node_id -> { id, node_type, label, props, evidence_ids }
    nodes_map: Dict[str, Dict[str, Any]] = {}
    # edge_id -> { id, src, dst, edge_type, count, total_paise, first_seen, last_seen, props, evidence_ids }
    edges_map: Dict[str, Dict[str, Any]] = {}

    def add_node(node_type: str, raw_label: str, props: Optional[Dict[str, Any]] = None, evidence_id: Optional[str] = None) -> str:
        if not raw_label or not str(raw_label).strip():
            return ""
        clean_label = str(raw_label).strip()
        n_id = generate_node_id(case_id, node_type, clean_label)
        if n_id not in nodes_map:
            nodes_map[n_id] = {
                "id": n_id,
                "case_id": case_id,
                "node_type": node_type,
                "label": clean_label,
                "props": props or {},
                "evidence_ids": set([evidence_id]) if evidence_id else set()
            }
        else:
            if props:
                nodes_map[n_id]["props"].update(props)
            if evidence_id:
                nodes_map[n_id]["evidence_ids"].add(evidence_id)
        return n_id

    def add_edge(
        src_id: str,
        dst_id: str,
        edge_type: str,
        paise: int = 0,
        seen_time: Optional[str] = None,
        props: Optional[Dict[str, Any]] = None,
        evidence_id: Optional[str] = None
    ) -> str:
        if not src_id or not dst_id or src_id == dst_id:
            return ""
        e_id = generate_edge_id(case_id, src_id, dst_id, edge_type)
        if e_id not in edges_map:
            edges_map[e_id] = {
                "id": e_id,
                "case_id": case_id,
                "src": src_id,
                "dst": dst_id,
                "edge_type": edge_type,
                "count": 1,
                "total_paise": int(paise or 0),
                "first_seen": seen_time,
                "last_seen": seen_time,
                "props": props or {},
                "evidence_ids": set([evidence_id]) if evidence_id else set()
            }
        else:
            rec = edges_map[e_id]
            rec["count"] += 1
            rec["total_paise"] += int(paise or 0)
            if seen_time:
                if not rec["first_seen"] or seen_time < rec["first_seen"]:
                    rec["first_seen"] = seen_time
                if not rec["last_seen"] or seen_time > rec["last_seen"]:
                    rec["last_seen"] = seen_time
            if props:
                rec["props"].update(props)
            if evidence_id:
                rec["evidence_ids"].add(evidence_id)
        return e_id

    # -------------------------------------------------------------
    # 1. Harvest Call Records (CDR)
    # -------------------------------------------------------------
    calls = db.query(CallRecord).filter(CallRecord.case_id == case_id, CallRecord.is_active.is_(True)).all()
    for call in calls:
        c_src = add_node("Phone", call.caller, {"phone": call.caller}, call.source_file)
        c_dst = add_node("Phone", call.receiver, {"phone": call.receiver}, call.source_file)
        seen_ts = call.datetime_iso or (f"{call.call_date}T{call.call_time}" if call.call_date and call.call_time else None)

        add_edge(
            src_id=c_src,
            dst_id=c_dst,
            edge_type="CALLED",
            paise=0,
            seen_time=seen_ts,
            props={"duration_seconds": call.duration_seconds, "call_type": call.call_type},
            evidence_id=call.source_file
        )

        if call.imei:
            dev_id = add_node("Device", call.imei, {"imei": call.imei}, call.source_file)
            add_edge(c_src, dev_id, "USES_DEVICE", seen_time=seen_ts, evidence_id=call.source_file)

    # -------------------------------------------------------------
    # 2. Harvest Transactions (Bank & UPI)
    # -------------------------------------------------------------
    txns = db.query(Transaction).filter(Transaction.case_id == case_id, Transaction.is_active.is_(True)).all()
    for t in txns:
        # Check if account looks like UPI VPA
        from_type = "VPA" if "@" in (t.from_account or "") else "Account"
        to_type = "VPA" if "@" in (t.to_account or "") else "Account"

        from_acc_id = add_node(from_type, t.from_account, {"name": t.from_name}, t.source_file)
        to_acc_id = add_node(to_type, t.to_account, {"name": t.to_name}, t.source_file)

        add_edge(
            src_id=from_acc_id,
            dst_id=to_acc_id,
            edge_type="TRANSFERRED",
            paise=t.amount_paise or 0,
            seen_time=t.date_iso,
            props={"direction": t.direction, "reference": t.reference},
            evidence_id=t.source_file
        )

        if t.from_name:
            p_from = add_node("Person", t.from_name, {"display_name": t.from_name}, t.source_file)
            add_edge(p_from, from_acc_id, "OWNS", seen_time=t.date_iso, evidence_id=t.source_file)

        if t.to_name:
            p_to = add_node("Person", t.to_name, {"display_name": t.to_name}, t.source_file)
            add_edge(p_to, to_acc_id, "OWNS", seen_time=t.date_iso, evidence_id=t.source_file)

    # -------------------------------------------------------------
    # 3. Harvest IP Events
    # -------------------------------------------------------------
    ip_events = db.query(IPEvent).filter(IPEvent.case_id == case_id, IPEvent.is_active.is_(True)).all()
    for ip in ip_events:
        ident_type = "Account" if "@" in ip.identifier or ip.identifier.isalpha() else "Phone"
        ident_id = add_node(ident_type, ip.identifier, {}, ip.source_file)
        ip_id = add_node("IP", ip.ip_address, {"ip": ip.ip_address}, ip.source_file)

        add_edge(ident_id, ip_id, "USED_IP", seen_time=ip.datetime_iso, evidence_id=ip.source_file)

    # -------------------------------------------------------------
    # 4. Harvest Staged Entities & Explicit Links
    # -------------------------------------------------------------
    entities = db.query(Entity).filter(Entity.case_id == case_id, Entity.is_active.is_(True)).all()
    ent_node_map: Dict[str, str] = {}
    for ent in entities:
        node_type = ent.label or "Person"
        n_id = add_node(
            node_type=node_type,
            raw_label=ent.canonical_id,
            props={"display_name": ent.display_name, "confidence": ent.confidence, "method": ent.method},
            evidence_id=ent.source_file
        )
        ent_node_map[ent.id] = n_id
        ent_node_map[ent.canonical_id] = n_id

    links = db.query(EntityLink).filter(EntityLink.case_id == case_id, EntityLink.is_active.is_(True)).all()
    for link in links:
        s_id = ent_node_map.get(link.source_entity_id) or add_node("Person", link.source_entity_id, evidence_id=link.source_file)
        t_id = ent_node_map.get(link.target_entity_id) or add_node("Phone", link.target_entity_id, evidence_id=link.source_file)
        rel_type = (link.relationship_type or "ASSOCIATED_WITH").upper()

        add_edge(
            src_id=s_id,
            dst_id=t_id,
            edge_type=rel_type,
            props={"confidence": link.confidence, "method": link.method},
            evidence_id=link.source_file
        )

    # -------------------------------------------------------------
    # 5. Harvest Finding Nodes (Top Leads / Findings)
    # -------------------------------------------------------------
    findings = db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).all()
    for f_res in findings:
        f_label = f"Primary Attributed Lead #{f_res.rank}"
        f_node_id = add_node("Finding", f_label, {"score": f_res.score, "rank": f_res.rank})
        # Link to underlying entity node
        e_target_id = None
        for cand_type in ["Phone", "Account", "Person", "VPA"]:
            test_id = generate_node_id(case_id, cand_type, f_res.entity_id)
            if test_id in nodes_map:
                e_target_id = test_id
                break
        if not e_target_id:
            e_target_id = add_node("Person", f_res.entity_id)

        add_edge(f_node_id, e_target_id, "MENTIONED_IN")

    # -------------------------------------------------------------
    # 6. SQLite Transactional Persistence (Authoritative Source of Truth)
    # -------------------------------------------------------------
    db.query(GraphEdge).filter(GraphEdge.case_id == case_id).delete()
    db.query(GraphNode).filter(GraphNode.case_id == case_id).delete()
    db.commit()

    db_nodes = []
    for n_data in nodes_map.values():
        gn = GraphNode(
            id=n_data["id"],
            case_id=case_id,
            node_type=n_data["node_type"],
            label=n_data["label"],
            props_json=json.dumps(n_data["props"]),
            source_evidence_ids=json.dumps(sorted(list(n_data["evidence_ids"])))
        )
        db_nodes.append(gn)
    db.bulk_save_objects(db_nodes)

    db_edges = []
    for e_data in edges_map.values():
        ge = GraphEdge(
            id=e_data["id"],
            case_id=case_id,
            src=e_data["src"],
            dst=e_data["dst"],
            edge_type=e_data["edge_type"],
            count=e_data["count"],
            total_paise=e_data["total_paise"],
            first_seen=to_datetime(e_data["first_seen"]),
            last_seen=to_datetime(e_data["last_seen"]),
            props_json=json.dumps(e_data["props"]),
            source_evidence_ids=json.dumps(sorted(list(e_data["evidence_ids"])))
        )
        db_edges.append(ge)
    db.bulk_save_objects(db_edges)
    db.commit()

    # -------------------------------------------------------------
    # 7. NetworkX Projection
    # -------------------------------------------------------------
    nx_graph = nx.MultiDiGraph()
    for n in nodes_map.values():
        nx_graph.add_node(
            n["id"],
            node_type=n["node_type"],
            label=n["label"],
            props=n["props"],
            evidence_ids=sorted(list(n["evidence_ids"]))
        )

    for e in edges_map.values():
        nx_graph.add_edge(
            e["src"],
            e["dst"],
            key=e["id"],
            edge_type=e["edge_type"],
            count=e["count"],
            total_paise=e["total_paise"],
            first_seen=e["first_seen"],
            last_seen=e["last_seen"],
            evidence_ids=sorted(list(e["evidence_ids"]))
        )

    # Invalidate and cache in memory
    CASE_GRAPH_CACHE[case_id] = (nx_graph, nx_graph)

    # -------------------------------------------------------------
    # 8. Neo4j Projection with Resilient Offline Fallback
    # -------------------------------------------------------------
    neo4j_status = "offline_fallback_active"
    if check_neo4j_health():
        driver = get_neo4j_driver()
        if driver:
            try:
                with driver.session() as session:
                    # Clear previous case nodes
                    session.run("MATCH (n:CaseNode {case_id: $case_id}) DETACH DELETE n", case_id=case_id)

                    # Batch write nodes
                    nodes_payload = [
                        {
                            "id": n["id"],
                            "case_id": case_id,
                            "node_type": n["node_type"],
                            "label": n["label"],
                            "props_json": json.dumps(n["props"])
                        }
                        for n in nodes_map.values()
                    ]
                    if nodes_payload:
                        session.run(
                            """
                            UNWIND $batch AS row
                            MERGE (n:CaseNode {id: row.id})
                            SET n.case_id = row.case_id,
                                n.node_type = row.node_type,
                                n.label = row.label,
                                n.props = row.props_json
                            """,
                            batch=nodes_payload
                        )

                    # Batch write edges
                    edges_payload = [
                        {
                            "id": e["id"],
                            "case_id": case_id,
                            "src": e["src"],
                            "dst": e["dst"],
                            "edge_type": e["edge_type"],
                            "count": e["count"],
                            "total_paise": e["total_paise"],
                            "first_seen": e["first_seen"] or "",
                            "last_seen": e["last_seen"] or ""
                        }
                        for e in edges_map.values()
                    ]
                    if edges_payload:
                        session.run(
                            """
                            UNWIND $batch AS row
                            MATCH (a:CaseNode {id: row.src}), (b:CaseNode {id: row.dst})
                            MERGE (a)-[r:RELATED {id: row.id}]->(b)
                            SET r.case_id = row.case_id,
                                r.edge_type = row.edge_type,
                                r.count = row.count,
                                r.total_paise = row.total_paise,
                                r.first_seen = row.first_seen,
                                r.last_seen = row.last_seen
                            """,
                            batch=edges_payload
                        )

                neo4j_status = "synced"
            except Exception as neo_err:
                logger.warning(f"Neo4j sync failed; continuing with SQLite/NetworkX: {neo_err}")
                neo4j_status = f"sync_failed_fallback_active: {str(neo_err)}"

    # -------------------------------------------------------------
    # 9. Cryptographic Audit Chain Log
    # -------------------------------------------------------------
    record_audit_log(
        db=db,
        user_id="graph_engine",
        action="REBUILD_GRAPH",
        case_id=case_id,
        object_type="case_graph",
        object_id=case_id,
        details={
            "nodes_count": len(nodes_map),
            "edges_count": len(edges_map),
            "neo4j_status": neo4j_status,
            "sqlite_authoritative": True
        }
    )

    return {
        "case_id": case_id,
        "status": "rebuilt",
        "nodes_count": len(nodes_map),
        "edges_count": len(edges_map),
        "neo4j_status": neo4j_status,
        "authoritative_source": "SQLite WAL"
    }


def build_detail_graph(db: Session, case_id: str) -> nx.MultiDiGraph:
    """Legacy backward-compatibility wrapper; invokes rebuild_graph."""
    if case_id not in CASE_GRAPH_CACHE:
        rebuild_graph(db, case_id)
    return CASE_GRAPH_CACHE[case_id][0]
