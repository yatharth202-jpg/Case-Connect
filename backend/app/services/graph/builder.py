import json
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    CallRecord, Transaction, IPEvent, Entity, EntityLink, ProfileMember
)
from backend.app.db.neo4j import check_neo4j_health, get_neo4j_session

# In-memory graph cache per case: { case_id: (detail_graph, entity_graph) }
CASE_GRAPH_CACHE: Dict[str, Tuple[nx.MultiDiGraph, nx.MultiGraph]] = {}

def invalidate_case_graph(case_id: str):
    """Evicts cached graph for a case to force fresh rebuild."""
    if case_id in CASE_GRAPH_CACHE:
        del CASE_GRAPH_CACHE[case_id]

def build_detail_graph(db: Session, case_id: str) -> nx.MultiDiGraph:
    """
    Builds the detailed directed multi-graph from SQLite staging tables for a case.
    Node key format: '<case_id>|<Label>|<normalized_id>'
    Labels: Phone, BankAccount, Person, Organization, Vehicle, Device, IP, FIR
    """
    g = nx.MultiDiGraph()

    # 1. Staged Entities (Persons, Vehicles, unassigned BankAccounts/Phones from identity tables)
    entities = db.query(Entity).filter(Entity.case_id == case_id).all()

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
    links = db.query(EntityLink).filter(EntityLink.case_id == case_id).all()
    for link in links:
        owner_key = f"{case_id}|Person|{link.source_entity_id}"
        target_key = None
        for candidate_label in ["Phone", "BankAccount", "Vehicle", "Person"]:
            ck = f"{case_id}|{candidate_label}|{link.target_entity_id}"
            if g.has_node(ck):
                target_key = ck
                break
        if not target_key:
            target_label = "Phone" if link.relationship_type == "USES" else ("Vehicle" if link.relationship_type == "DRIVES" else "BankAccount")
            target_key = f"{case_id}|{target_label}|{link.target_entity_id}"
            g.add_node(target_key, case_id=case_id, label=target_label, id=link.target_entity_id, name=link.target_entity_id, shared=False)
        
        if not g.has_node(owner_key):
            g.add_node(owner_key, case_id=case_id, label="Person", id=link.source_entity_id, name=link.source_entity_id, shared=False)
        
        g.add_edge(
            owner_key, target_key,
            key=f"link_{link.id}",
            type=link.relationship_type,
            method=link.method or "officer",
            confidence=link.confidence or 1.0,
            source_file=link.source_file or "Officer Annotation",
            source_ref=link.source_ref or str(link.id)
        )

    # 3. Call Records -> Phone nodes and CALLED edges
    calls = db.query(CallRecord).filter(CallRecord.case_id == case_id).all()
    
    # Group calls by ordered pair
    call_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for call in calls:
        caller_key = f"{case_id}|Phone|{call.caller}"
        receiver_key = f"{case_id}|Phone|{call.receiver}"

        if not g.has_node(caller_key):
            g.add_node(caller_key, case_id=case_id, label="Phone", id=call.caller, name=call.caller, shared=False, first_seen=call.call_date, last_seen=call.call_date)
        if not g.has_node(receiver_key):
            g.add_node(receiver_key, case_id=case_id, label="Phone", id=call.receiver, name=call.receiver, shared=False, first_seen=call.call_date, last_seen=call.call_date)

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

    # 4. Transactions -> BankAccount nodes and TRANSFERRED_TO edges
    txns = db.query(Transaction).filter(Transaction.case_id == case_id).all()
    for t in txns:
        from_key = f"{case_id}|BankAccount|{t.from_account}"
        to_key = f"{case_id}|BankAccount|{t.to_account}"

        if not g.has_node(from_key):
            g.add_node(from_key, case_id=case_id, label="BankAccount", id=t.from_account, name=t.from_name or t.from_account, shared=False)
        if not g.has_node(to_key):
            g.add_node(to_key, case_id=case_id, label="BankAccount", id=t.to_account, name=t.to_name or t.to_account, shared=False)

        # Connect from_name / to_name if present
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
    ip_events = db.query(IPEvent).filter(IPEvent.case_id == case_id).all()
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

