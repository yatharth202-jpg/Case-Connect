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
7. 100% Backward Compatibility: Preserves build_detail_graph and entity projections for legacy views.
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
    CallRecord, Transaction, IPEvent, Entity, EntityLink, ProfileMember,
    GraphNode, GraphEdge, NodeTypeConfig, EdgeTypeConfig, SystemConfig, Case
)
from backend.app.db.neo4j import check_neo4j_health, get_neo4j_driver
from backend.app.audit.service import record_audit_log
from backend.app.services.graph.projection import build_entity_projection

logger = logging.getLogger("case_connect.graph_builder")

# In-memory graph cache per case: { case_id: (detail_graph, entity_graph) }
CASE_GRAPH_CACHE: Dict[str, Tuple[nx.MultiDiGraph, nx.MultiGraph]] = {}

SEED_GRAPH_CONFIG_PATH = Path("backend") / "config" / "seed_graph_config.yaml"


def ensure_graph_configs_seeded(db: Session):
    """Seeds NodeTypeConfig and EdgeTypeConfig from default yaml if table is empty."""
    if db.query(NodeTypeConfig).count() == 0 and SEED_GRAPH_CONFIG_PATH.exists():
        try:
            with open(SEED_GRAPH_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for nt in data.get("node_types", []):
                    db.add(NodeTypeConfig(
                        type_name=nt["type_name"],
                        label=nt.get("label", nt["type_name"]),
                        color=nt.get("color", "#2563EB"),
                        icon=nt.get("icon", "circle"),
                        shape=nt.get("shape", "ellipse"),
                        score_weight=nt.get("score_weight", 1.0)
                    ))
                for et in data.get("edge_types", []):
                    db.add(EdgeTypeConfig(
                        type_name=et["type_name"],
                        label=et.get("label", et["type_name"]),
                        color=et.get("color", "#64748B"),
                        line_style=et.get("line_style", "solid"),
                        directional=et.get("directional", True)
                    ))
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to seed graph config: {e}")



def invalidate_case_graph(case_id: str):
    """Evicts cached graph for a case to force fresh rebuild."""
    if case_id in CASE_GRAPH_CACHE:
        del CASE_GRAPH_CACHE[case_id]


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


def build_detail_graph(db: Session, case_id: str) -> nx.MultiDiGraph:
    """
    Builds the detailed directed multi-graph from SQLite staging tables for a case.
    Node key format: '<case_id>|<Label>|<normalized_id>'
    Labels: Phone, BankAccount, Person, Organization, Vehicle, Device, IP, FIR
    """
    g = nx.MultiDiGraph()

    # 1. Staged Entities (Persons, Vehicles, unassigned BankAccounts/Phones from identity tables)
    entities = db.query(Entity).filter(Entity.case_id == case_id, Entity.is_active.is_(True)).all()

    for ent in entities:
        props = {}
        try:
            props = json.loads(ent.properties_json)
        except Exception:
            pass

        node_key = f"{case_id}|{ent.label}|{ent.canonical_id}"
        if not g.has_node(node_key):
            g.add_node(
                node_key,
                case_id=case_id,
                label=ent.label,
                id=ent.canonical_id,
                name=ent.display_name,
                source_file=ent.source_file,
                source_ref=ent.source_ref,
                method=ent.method,
                confidence=ent.confidence,
                shared=False,
                degree=0
            )

    # 1b. Connect entities staged from the same identity table row
    row_entities: Dict[Tuple[str, str], List[Entity]] = {}
    for ent in entities:
        if ent.source_file and ent.source_ref:
            row_entities.setdefault((ent.source_file, ent.source_ref), []).append(ent)

    for (s_file, s_ref), ents_in_row in row_entities.items():
        persons = [e for e in ents_in_row if e.label in ["Person", "Organization"]]
        identifiers = [e for e in ents_in_row if e.label not in ["Person", "Organization"]]
        for p in persons:
            p_key = f"{case_id}|{p.label}|{p.canonical_id}"
            for ident in identifiers:
                ident_key = f"{case_id}|{ident.label}|{ident.canonical_id}"
                rel = "USES" if ident.label == "Phone" else ("DRIVES" if ident.label == "Vehicle" else "OWNS")
                g.add_edge(
                    p_key, ident_key,
                    key=f"idtab_{p.canonical_id}_{ident.canonical_id}",
                    type=rel,
                    method="identity_table",
                    confidence=1.0,
                    source_file=s_file,
                    source_ref=s_ref
                )

    # 1c. Master Profiles & RESOLVED_TO relationships
    members = db.query(ProfileMember).all()
    case_pids = set(e.canonical_id for e in entities if e.label == "Person")
    case_members = [m for m in members if m.entity_id in case_pids]
    for m in case_members:
        mp_key = f"{case_id}|MasterProfile|{m.profile_id}"
        person_key = f"{case_id}|Person|{m.entity_id}"
        if not g.has_node(mp_key):
            g.add_node(
                mp_key,
                case_id=case_id,
                label="MasterProfile",
                id=m.profile_id,
                name=f"Profile {m.profile_id}",
                shared=False,
                degree=0
            )
        if g.has_node(person_key):
            g.add_edge(
                person_key, mp_key,
                key=f"res_{m.id}",
                type="RESOLVED_TO",
                method="master_profile",
                confidence=1.0,
                approved_by=m.approved_by,
                approved_at=m.created_at.isoformat() if m.created_at else None,
                match_id=m.match_id
            )

    # 2. Officer & staged entity links
    links = db.query(EntityLink).filter(EntityLink.case_id == case_id, EntityLink.is_active.is_(True)).all()
    for link in links:
        source_key = None
        for candidate_label in ["Person", "Organization", "Phone", "BankAccount", "Vehicle", "FIR", "IP"]:
            sk = f"{case_id}|{candidate_label}|{link.source_entity_id}"
            if g.has_node(sk):
                source_key = sk
                break
        if not source_key:
            source_key = f"{case_id}|Person|{link.source_entity_id}"
            g.add_node(source_key, case_id=case_id, label="Person", id=link.source_entity_id, name=link.source_entity_id, shared=False)

        target_key = None
        for candidate_label in ["Phone", "BankAccount", "Vehicle", "Person", "Organization", "FIR", "IP"]:
            tk = f"{case_id}|{candidate_label}|{link.target_entity_id}"
            if g.has_node(tk):
                target_key = tk
                break
        if not target_key:
            default_target_label = "Phone" if link.relationship_type == "USES" else ("Vehicle" if link.relationship_type == "DRIVES" else "BankAccount")
            target_key = f"{case_id}|{default_target_label}|{link.target_entity_id}"
            g.add_node(target_key, case_id=case_id, label=default_target_label, id=link.target_entity_id, name=link.target_entity_id, shared=False)

        g.add_edge(
            source_key, target_key,
            key=f"link_{link.id}",
            type=link.relationship_type,
            method=link.method or "officer",
            confidence=link.confidence or 1.0,
            source_file=link.source_file,
            source_ref=link.source_ref,
            approved_by=link.approved_by,
            link_id=link.id
        )

    # 3. Call Records -> Phone nodes and CALLED edges
    calls = db.query(CallRecord).filter(CallRecord.case_id == case_id, CallRecord.is_active.is_(True)).all()
    call_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for call in calls:
        caller_key = f"{case_id}|Phone|{call.caller}"
        receiver_key = f"{case_id}|Phone|{call.receiver}"

        if not g.has_node(caller_key):
            g.add_node(caller_key, case_id=case_id, label="Phone", id=call.caller, name=call.caller, shared=False)
        if not g.has_node(receiver_key):
            g.add_node(receiver_key, case_id=case_id, label="Phone", id=call.receiver, name=call.receiver, shared=False)

        pair = (caller_key, receiver_key)
        if pair not in call_pairs:
            call_pairs[pair] = {
                "count": 0,
                "total_duration": 0,
                "first_call": call.datetime_iso or call.call_date,
                "last_call": call.datetime_iso or call.call_date,
                "source_file": call.source_file,
                "source_ref": call.source_ref
            }
        call_pairs[pair]["count"] += 1
        call_pairs[pair]["total_duration"] += call.duration_seconds
        if call.datetime_iso:
            call_pairs[pair]["last_call"] = max(call_pairs[pair]["last_call"] or "", call.datetime_iso)

    for (src, dst), c_info in call_pairs.items():
        g.add_edge(
            src, dst,
            key=f"called_{src}_{dst}",
            type="CALLED",
            count=c_info["count"],
            total_duration=c_info["total_duration"],
            first_call=c_info["first_call"],
            last_call=c_info["last_call"],
            source_file=c_info["source_file"],
            source_ref=c_info["source_ref"],
            method="cdr",
            confidence=1.0
        )

    # 3b. IMEI Device associations from CallRecords
    for call in calls:
        if call.imei and call.caller:
            caller_key = f"{case_id}|Phone|{call.caller}"
            imei_key = f"{case_id}|Device|{call.imei}"
            if not g.has_node(imei_key):
                g.add_node(imei_key, case_id=case_id, label="Device", id=call.imei, name=call.imei, shared=False)
            if not g.has_edge(caller_key, imei_key):
                g.add_edge(
                    caller_key, imei_key,
                    key=f"device_{call.caller}_{call.imei}",
                    type="USES_DEVICE",
                    source_file=call.source_file,
                    source_ref=call.source_ref,
                    method="cdr_imei",
                    confidence=1.0
                )

    # 4. Transactions -> BankAccount nodes and TRANSFERRED_TO edges
    txns = db.query(Transaction).filter(Transaction.case_id == case_id, Transaction.is_active.is_(True)).all()
    for t in txns:
        from_key = f"{case_id}|BankAccount|{t.from_account}"
        to_key = f"{case_id}|BankAccount|{t.to_account}"

        if not g.has_node(from_key):
            g.add_node(from_key, case_id=case_id, label="BankAccount", id=t.from_account, name=t.from_name or t.from_account, shared=False)
        if not g.has_node(to_key):
            g.add_node(to_key, case_id=case_id, label="BankAccount", id=t.to_account, name=t.to_name or t.to_account, shared=False)

        if t.from_name:
            norm_name = t.from_name.lower().strip()
            p_key = f"{case_id}|Person|{norm_name}"
            if not g.has_node(p_key):
                g.add_node(p_key, case_id=case_id, label="Person", id=norm_name, name=t.from_name, shared=False)
            g.add_edge(p_key, from_key, key=f"owns_{p_key}_{from_key}", type="OWNS", method="bank_statement", confidence=0.9, source_file=t.source_file, source_ref=t.source_ref)

        if t.to_name:
            norm_name = t.to_name.lower().strip()
            p_key = f"{case_id}|Person|{norm_name}"
            if not g.has_node(p_key):
                g.add_node(p_key, case_id=case_id, label="Person", id=norm_name, name=t.to_name, shared=False)
            g.add_edge(p_key, to_key, key=f"owns_{p_key}_{to_key}", type="OWNS", method="bank_statement", confidence=0.9, source_file=t.source_file, source_ref=t.source_ref)

        g.add_edge(
            from_key, to_key,
            key=t.fingerprint,
            type="TRANSFERRED_TO",
            amount_paise=t.amount_paise,
            date=t.date_iso,
            reference=t.reference,
            source_file=t.source_file,
            source_ref=t.source_ref,
            method="banking",
            confidence=1.0
        )

    # 5. IP Events -> IP nodes and SEEN_ON_IP edges
    ip_events = db.query(IPEvent).filter(IPEvent.case_id == case_id, IPEvent.is_active.is_(True)).all()
    for ip_ev in ip_events:
        phone_key = f"{case_id}|Phone|{ip_ev.identifier}"
        ip_key = f"{case_id}|IP|{ip_ev.ip_address}"

        if not g.has_node(phone_key):
            g.add_node(phone_key, case_id=case_id, label="Phone", id=ip_ev.identifier, name=ip_ev.identifier, shared=False)
        if not g.has_node(ip_key):
            g.add_node(ip_key, case_id=case_id, label="IP", id=ip_ev.ip_address, name=ip_ev.ip_address, shared=False)

        g.add_edge(
            phone_key, ip_key,
            key=f"ip_{ip_ev.id}",
            type="SEEN_ON_IP",
            datetime=ip_ev.datetime_iso,
            source_file=ip_ev.source_file,
            source_ref=ip_ev.source_ref,
            method="ip_log",
            confidence=0.85
        )

    # 6. Mark shared identifiers (e.g. multiple persons sharing a phone/account)
    for n in g.nodes():
        if g.nodes[n].get("label") not in ["Person", "Organization"]:
            owners = set()
            for pred in g.predecessors(n):
                if g.nodes[pred].get("label") in ["Person", "Organization"]:
                    for edge in g.get_edge_data(pred, n).values():
                        if edge.get("type") in ["USES", "OWNS", "DRIVES"]:
                            owners.add(pred)
            if len(owners) > 1:
                g.nodes[n]["shared"] = True

    # 7. Update degrees
    for n in g.nodes():
        g.nodes[n]["degree"] = g.degree(n)

    return g


def rebuild_graph(db: Session, case_id: str) -> Dict[str, Any]:
    """
    Authoritative SQLite-first Graph Rebuild & Disposable Projection Pipeline.
    1. Rebuilds active NetworkX detail and entity graphs.
    2. Persists authoritative GraphNode and GraphEdge records to SQLite with stable IDs and aggregation.
    3. Projects to Neo4j if available, with graceful fallback.
    4. Logs to cryptographic audit chain.
    """
    # Invalidate in-memory cache
    invalidate_case_graph(case_id)

    # 1. Build authoritative NetworkX structures
    detail_g = build_detail_graph(db, case_id)
    entity_g = build_entity_projection(detail_g)
    CASE_GRAPH_CACHE[case_id] = (detail_g, entity_g)

    # 2. Extract and Persist SQLite Graph Nodes & Edges
    db.query(GraphEdge).filter(GraphEdge.case_id == case_id).delete()
    db.query(GraphNode).filter(GraphNode.case_id == case_id).delete()
    db.commit()

    # Map node keys to stable GraphNode models
    node_key_to_id: Dict[str, str] = {}
    sqlite_nodes: Dict[str, GraphNode] = {}

    for n_key, data in detail_g.nodes(data=True):
        raw_type = data.get("label", "Entity")
        label_type = "Account" if raw_type == "BankAccount" else raw_type
        if label_type in ["Account", "Phone", "Device", "IP", "VPA", "Aadhaar", "PAN", "Vehicle"]:
            canonical_label = data.get("id") or data.get("name") or n_key
        else:
            canonical_label = data.get("name") or data.get("id") or n_key
        node_id = generate_node_id(case_id, label_type, canonical_label)
        node_key_to_id[n_key] = node_id

        if node_id not in sqlite_nodes:
            evidence_ids = []
            s_file = data.get("source_file")
            if s_file:
                evidence_ids.append(s_file)

            sqlite_nodes[node_id] = GraphNode(
                id=node_id,
                case_id=case_id,
                node_type=label_type,
                label=canonical_label,
                props_json=json.dumps({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "shared": data.get("shared", False),
                    "confidence": data.get("confidence", 1.0),
                    "method": data.get("method", "auto")
                }),
                source_evidence_ids=json.dumps(evidence_ids)
            )

    # Add any nodes from entity_g not in detail_g (e.g. MasterProfiles)
    for n_key, data in entity_g.nodes(data=True):
        raw_type = data.get("label", "Entity")
        label_type = "Account" if raw_type == "BankAccount" else raw_type
        if label_type in ["Account", "Phone", "Device", "IP", "VPA", "Aadhaar", "PAN", "Vehicle"]:
            canonical_label = data.get("id") or data.get("name") or n_key
        else:
            canonical_label = data.get("name") or data.get("id") or n_key
        node_id = generate_node_id(case_id, label_type, canonical_label)
        node_key_to_id[n_key] = node_id

        if node_id not in sqlite_nodes:
            sqlite_nodes[node_id] = GraphNode(
                id=node_id,
                case_id=case_id,
                node_type=label_type,
                label=canonical_label,
                props_json=json.dumps({
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "shared": data.get("shared", False)
                }),
                source_evidence_ids=json.dumps([])
            )

    if sqlite_nodes:
        db.bulk_save_objects(list(sqlite_nodes.values()))
        db.commit()

    # Aggregate edges between stable node IDs
    sqlite_edges: Dict[str, Dict[str, Any]] = {}
    for u, v, e_key, data in detail_g.edges(keys=True, data=True):
        src_id = node_key_to_id.get(u)
        dst_id = node_key_to_id.get(v)
        if not src_id or not dst_id or src_id == dst_id:
            continue

        raw_edge = data.get("type", "RELATED")
        edge_type = "TRANSFERRED" if raw_edge in ["TRANSFERRED_TO", "TRANSFERRED"] else raw_edge
        edge_id = generate_edge_id(case_id, src_id, dst_id, edge_type)

        paise = data.get("amount_paise") or 0
        if not isinstance(paise, int):
            try:
                paise = int(paise)
            except Exception:
                paise = 0

        ts_candidates = [
            to_datetime(data.get("first_call")),
            to_datetime(data.get("last_call")),
            to_datetime(data.get("date")),
            to_datetime(data.get("datetime"))
        ]
        valid_ts = [t for t in ts_candidates if t is not None]

        evidence_list = []
        if data.get("source_file"):
            evidence_list.append(data.get("source_file"))

        if edge_id not in sqlite_edges:
            sqlite_edges[edge_id] = {
                "id": edge_id,
                "case_id": case_id,
                "src": src_id,
                "dst": dst_id,
                "edge_type": edge_type,
                "count": data.get("count", 1) or 1,
                "total_paise": paise,
                "first_seen": min(valid_ts) if valid_ts else None,
                "last_seen": max(valid_ts) if valid_ts else None,
                "props": {k: v for k, v in data.items() if k not in ["amount_paise", "first_call", "last_call"]},
                "evidence_ids": set(evidence_list)
            }
        else:
            rec = sqlite_edges[edge_id]
            rec["count"] += data.get("count", 1) or 1
            rec["total_paise"] += paise
            if valid_ts:
                current_min = rec["first_seen"]
                current_max = rec["last_seen"]
                rec["first_seen"] = min(current_min, min(valid_ts)) if current_min else min(valid_ts)
                rec["last_seen"] = max(current_max, max(valid_ts)) if current_max else max(valid_ts)
            rec["evidence_ids"].update(evidence_list)

    if sqlite_edges:
        edge_objs = [
            GraphEdge(
                id=e["id"],
                case_id=e["case_id"],
                src=e["src"],
                dst=e["dst"],
                edge_type=e["edge_type"],
                count=e["count"],
                total_paise=e["total_paise"],
                first_seen=e["first_seen"],
                last_seen=e["last_seen"],
                props_json=json.dumps(e["props"]),
                source_evidence_ids=json.dumps(sorted(list(e["evidence_ids"])))
            )
            for e in sqlite_edges.values()
        ]
        db.bulk_save_objects(edge_objs)
        db.commit()

    # 3. Neo4j Projection with Resilient Offline Fallback
    neo4j_status = "offline_fallback_active"
    if check_neo4j_health():
        driver = get_neo4j_driver()
        if driver:
            try:
                with driver.session() as session:
                    session.run("MATCH (n:CaseNode {case_id: $case_id}) DETACH DELETE n", case_id=case_id)
                    nodes_payload = [
                        {
                            "id": n.id,
                            "case_id": case_id,
                            "node_type": n.node_type,
                            "label": n.label,
                            "props_json": n.props_json
                        }
                        for n in sqlite_nodes.values()
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

                    edges_payload = [
                        {
                            "id": e["id"],
                            "case_id": case_id,
                            "src": e["src"],
                            "dst": e["dst"],
                            "edge_type": e["edge_type"],
                            "count": e["count"],
                            "total_paise": e["total_paise"],
                            "first_seen": e["first_seen"].isoformat() if e["first_seen"] else "",
                            "last_seen": e["last_seen"].isoformat() if e["last_seen"] else ""
                        }
                        for e in sqlite_edges.values()
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

    # 4. Cryptographic Audit Chain Log
    record_audit_log(
        db=db,
        user_id="graph_engine",
        action="REBUILD_GRAPH",
        case_id=case_id,
        object_type="case_graph",
        object_id=case_id,
        details={
            "detail_nodes": detail_g.number_of_nodes(),
            "detail_edges": detail_g.number_of_edges(),
            "entity_nodes": entity_g.number_of_nodes(),
            "entity_edges": entity_g.number_of_edges(),
            "sqlite_nodes": len(sqlite_nodes),
            "sqlite_edges": len(sqlite_edges),
            "neo4j_status": neo4j_status
        }
    )

    return {
        "case_id": case_id,
        "status": "rebuilt",
        "detail_nodes": detail_g.number_of_nodes(),
        "detail_edges": detail_g.number_of_edges(),
        "entity_nodes": entity_g.number_of_nodes(),
        "entity_edges": entity_g.number_of_edges(),
        "nodes_count": len(sqlite_nodes),
        "edges_count": len(sqlite_edges),
        "neo4j_status": neo4j_status,
        "authoritative_source": "SQLite WAL"
    }
