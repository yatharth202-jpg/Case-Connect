"""
Forensic Lead Prioritisation Engine for CaseConnect AI (Phase 3 Upgrade).
Compliant with Section 63 BSA 2023.

Guiding Forensic Standards:
1. AI Suggests, Human Decides: All outputs are objective statistical indicators
   for investigative prioritisation, never judicial determinations of guilt or culpability.
2. Neutral Terminology: Zero prejudicial vocabulary.
   All candidates are labelled 'Primary Attributed Lead #n'.
3. Deterministic & Explainable: 100% stable ranking via multi-key deterministic tie-break:
   (-round(score, 6), -degree, -total_paise, entity_id).
4. Configurable Weights: Weights dynamically loaded from SystemConfig table ('top_leads_weights')
   with fallback to seed defaults.
5. Ingestion-Sourced Evidence Links: Direct linkage of every candidate to underlying evidence IDs.
6. DB Persistence: Stored in analysis_results table for zero-recompute instant case reopening.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import networkx as nx
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.db.sql import (
    Case, EvidenceFile, RawRow, CallRecord, Transaction, IPEvent,
    Entity, EntityLink, AnalysisResult, SystemConfig, generate_uuid
)
from backend.app.audit.service import record_audit_log

DEFAULT_WEIGHTS = {
    "weight_degree": 0.20,
    "weight_betweenness": 0.25,
    "weight_pagerank": 0.20,
    "weight_pass_through": 0.20,
    "weight_total_paise": 0.10,
    "weight_cross_case": 0.05,
}

LEGAL_DISCLAIMER = (
    "Rank is a statistical indicator for investigative prioritisation, not a finding of culpability."
)


def get_top_leads_weights(db: Session) -> Dict[str, float]:
    """Retrieves lead scoring weights from SystemConfig or returns seeded defaults."""
    cfg = db.query(SystemConfig).filter(SystemConfig.key == "top_leads_weights").first()
    if cfg:
        try:
            stored = json.loads(cfg.value)
            if isinstance(stored, dict):
                return {k: float(stored.get(k, DEFAULT_WEIGHTS.get(k, 0.0))) for k in DEFAULT_WEIGHTS}
        except Exception:
            pass
    return dict(DEFAULT_WEIGHTS)


def compute_case_top_leads(
    db: Session,
    case_id: str,
    n: int = 5,
    persist: bool = True
) -> List[Dict[str, Any]]:
    """
    Computes explainable, data-driven Top-N Primary Attributed Leads for a case.
    Never pads or fabricates: if fewer than n candidates exist, returns only what exists.
    """
    weights = get_top_leads_weights(db)
    w_deg = weights.get("weight_degree", 0.20)
    w_bw = weights.get("weight_betweenness", 0.25)
    w_pr = weights.get("weight_pagerank", 0.20)
    w_pt = weights.get("weight_pass_through", 0.20)
    w_flow = weights.get("weight_total_paise", 0.10)
    w_cross = weights.get("weight_cross_case", 0.05)
    total_w = w_deg + w_bw + w_pr + w_pt + w_flow + w_cross
    if total_w > 0:
        w_deg /= total_w
        w_bw /= total_w
        w_pr /= total_w
        w_pt /= total_w
        w_flow /= total_w
        w_cross /= total_w

    # Step 1: Collect Case Data
    call_records = db.query(CallRecord).filter(CallRecord.case_id == case_id).all()
    transactions = db.query(Transaction).filter(Transaction.case_id == case_id).all()
    ip_events = db.query(IPEvent).filter(IPEvent.case_id == case_id).all()
    entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    entity_links = db.query(EntityLink).filter(EntityLink.case_id == case_id).all()
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case_id).all()
    ev_id_map = {e.id: e.original_name for e in evidence_files}

    # Track evidence sources per entity
    entity_evidence: Dict[str, set] = {}
    entity_labels: Dict[str, str] = {}
    entity_display: Dict[str, str] = {}

    for ent in entities:
        c_id = ent.canonical_id
        entity_labels[c_id] = ent.label
        entity_display[c_id] = ent.display_name or c_id
        if ent.source_file:
            entity_evidence.setdefault(c_id, set()).add(ent.source_file)

    # Step 2: Build NetworkX Graph
    G = nx.Graph()

    # Communication Edges
    for c in call_records:
        if c.caller and c.receiver:
            G.add_edge(c.caller, c.receiver, rel="COMMUNICATION")
            entity_labels.setdefault(c.caller, "Phone")
            entity_labels.setdefault(c.receiver, "Phone")
            if c.source_file:
                entity_evidence.setdefault(c.caller, set()).add(c.source_file)
                entity_evidence.setdefault(c.receiver, set()).add(c.source_file)

    # Transaction Edges and Money Flow Tracking
    inflows: Dict[str, int] = {}
    outflows: Dict[str, int] = {}
    total_flow: Dict[str, int] = {}

    for t in transactions:
        if t.from_account and t.to_account:
            G.add_edge(t.from_account, t.to_account, rel="TRANSACTION")
            entity_labels.setdefault(t.from_account, "Account")
            entity_labels.setdefault(t.to_account, "Account")
            if t.from_name:
                entity_display.setdefault(t.from_account, f"{t.from_name} ({t.from_account})")
            if t.to_name:
                entity_display.setdefault(t.to_account, f"{t.to_name} ({t.to_account})")

            amt = t.amount_paise or 0
            outflows[t.from_account] = outflows.get(t.from_account, 0) + amt
            inflows[t.to_account] = inflows.get(t.to_account, 0) + amt
            total_flow[t.from_account] = total_flow.get(t.from_account, 0) + amt
            total_flow[t.to_account] = total_flow.get(t.to_account, 0) + amt

            if t.source_file:
                entity_evidence.setdefault(t.from_account, set()).add(t.source_file)
                entity_evidence.setdefault(t.to_account, set()).add(t.source_file)

    # IP Event Edges
    for ip in ip_events:
        if ip.identifier and ip.ip_address:
            G.add_edge(ip.identifier, ip.ip_address, rel="IP_SESSION")
            entity_labels.setdefault(ip.identifier, "Account")
            entity_labels.setdefault(ip.ip_address, "IP")
            if ip.source_file:
                entity_evidence.setdefault(ip.identifier, set()).add(ip.source_file)
                entity_evidence.setdefault(ip.ip_address, set()).add(ip.source_file)

    # Explicit Entity Links
    for link in entity_links:
        if link.source_entity_id and link.target_entity_id:
            G.add_edge(link.source_entity_id, link.target_entity_id, rel=link.relationship_type)
            if link.source_file:
                entity_evidence.setdefault(link.source_entity_id, set()).add(link.source_file)
                entity_evidence.setdefault(link.target_entity_id, set()).add(link.source_file)

    candidates = list(G.nodes())
    if not candidates:
        # If no edges, fallback to isolated entities
        candidates = [e.canonical_id for e in entities]
        for c in candidates:
            G.add_node(c)

    if not candidates:
        return []

    # Step 3: Compute Topological Metrics
    # Degree
    deg_map = dict(G.degree())
    max_deg = max(deg_map.values()) if deg_map else 1

    # Betweenness Centrality
    if G.number_of_nodes() >= 3:
        try:
            bw_map = nx.betweenness_centrality(G, seed=42)
        except Exception:
            bw_map = {n: 0.0 for n in candidates}
    else:
        bw_map = {n: 0.0 for n in candidates}
    max_bw = max(bw_map.values()) if bw_map and max(bw_map.values()) > 0 else 1.0

    # PageRank
    if G.number_of_nodes() >= 2:
        try:
            pr_map = nx.pagerank(G, alpha=0.85, max_iter=200, tol=1e-6)
        except Exception:
            pr_map = {n: 1.0 / len(candidates) for n in candidates}
    else:
        pr_map = {n: 1.0 for n in candidates}
    max_pr = max(pr_map.values()) if pr_map and max(pr_map.values()) > 0 else 1.0

    # Pass-Through Flag
    # Rapid pass-through: has both inflow and outflow, throughput > 0, and balanced ratio >= 0.70
    pass_through_map: Dict[str, float] = {}
    for node in candidates:
        inf = inflows.get(node, 0)
        outf = outflows.get(node, 0)
        if inf > 0 and outf > 0:
            ratio = min(inf, outf) / max(inf, outf)
            if ratio >= 0.70:
                pass_through_map[node] = 1.0
            else:
                pass_through_map[node] = 0.5
        else:
            pass_through_map[node] = 0.0

    # Total Paise Flow
    max_flow = max(total_flow.values()) if total_flow else 1

    # Cross-Case Hits
    cross_case_map: Dict[str, float] = {}
    for node in candidates:
        # Count other cases where this identifier appears
        other_call_cases = db.query(func.count(func.distinct(CallRecord.case_id))).filter(
            CallRecord.case_id != case_id,
            (CallRecord.caller == node) | (CallRecord.receiver == node)
        ).scalar() or 0

        other_txn_cases = db.query(func.count(func.distinct(Transaction.case_id))).filter(
            Transaction.case_id != case_id,
            (Transaction.from_account == node) | (Transaction.to_account == node)
        ).scalar() or 0

        hits = other_call_cases + other_txn_cases
        cross_case_map[node] = min(hits, 5) / 5.0

    # Step 4: Scoring & Normalization
    scored_items = []
    for node in candidates:
        norm_deg = deg_map.get(node, 0) / max_deg if max_deg > 0 else 0.0
        norm_bw = bw_map.get(node, 0.0) / max_bw if max_bw > 0 else 0.0
        norm_pr = pr_map.get(node, 0.0) / max_pr if max_pr > 0 else 0.0
        pt_val = pass_through_map.get(node, 0.0)
        norm_flow = total_flow.get(node, 0) / max_flow if max_flow > 0 else 0.0
        norm_cross = cross_case_map.get(node, 0.0)

        composite_score = (
            (w_deg * norm_deg) +
            (w_bw * norm_bw) +
            (w_pr * norm_pr) +
            (w_pt * pt_val) +
            (w_flow * norm_flow) +
            (w_cross * norm_cross)
        )

        breakdown = {
            "degree": deg_map.get(node, 0),
            "normalized_degree": round(norm_deg, 4),
            "betweenness": round(bw_map.get(node, 0.0), 4),
            "normalized_betweenness": round(norm_bw, 4),
            "pagerank": round(pr_map.get(node, 0.0), 4),
            "normalized_pagerank": round(norm_pr, 4),
            "pass_through_flag": bool(pt_val >= 0.5),
            "pass_through_score": round(pt_val, 2),
            "total_paise": total_flow.get(node, 0),
            "normalized_flow": round(norm_flow, 4),
            "cross_case_hits": round(norm_cross * 5),
            "weights_applied": {
                "degree": round(w_deg, 3),
                "betweenness": round(w_bw, 3),
                "pagerank": round(w_pr, 3),
                "pass_through": round(w_pt, 3),
                "total_paise": round(w_flow, 3),
                "cross_case": round(w_cross, 3),
            }
        }

        # Resolve evidence filenames / IDs
        ev_sources = sorted(list(entity_evidence.get(node, [])))

        scored_items.append({
            "entity_id": node,
            "label": entity_labels.get(node, "Entity"),
            "display_name": entity_display.get(node, node),
            "score": round(composite_score, 4),
            "degree": deg_map.get(node, 0),
            "total_paise": total_flow.get(node, 0),
            "breakdown": breakdown,
            "evidence_sources": ev_sources,
        })

    # Step 5: Deterministic Stable Sort
    # Tie-break order: (-round(score, 6), -degree, -total_paise, entity_id)
    scored_items.sort(
        key=lambda x: (
            -round(x["score"], 6),
            -x["degree"],
            -x["total_paise"],
            str(x["entity_id"])
        )
    )

    top_items = scored_items[:n]

    # Assign Rank and Designation
    results = []
    for rank_idx, item in enumerate(top_items, start=1):
        lead_record = {
            "rank": rank_idx,
            "designation": f"Primary Attributed Lead #{rank_idx}",
            "entity_id": item["entity_id"],
            "label": item["label"],
            "display_name": item["display_name"],
            "score": item["score"],
            "breakdown": item["breakdown"],
            "evidence_sources": item["evidence_sources"],
            "disclaimer": LEGAL_DISCLAIMER,
        }
        results.append(lead_record)

    # Step 6: Persist in DB (analysis_results table)
    if persist and results:
        run_id = f"run_{case_id}_{int(datetime.now(timezone.utc).timestamp())}"
        # Remove previous runs for this case if refreshing
        db.query(AnalysisResult).filter(AnalysisResult.case_id == case_id).delete()
        for res in results:
            ar = AnalysisResult(
                id=generate_uuid(),
                run_id=run_id,
                case_id=case_id,
                entity_id=res["entity_id"],
                rank=res["rank"],
                score=res["score"],
                breakdown_json=json.dumps(res["breakdown"]),
                evidence_ids=json.dumps(res["evidence_sources"]),
                created_at=datetime.now(timezone.utc),
            )
            db.add(ar)
        db.commit()

        # Append to SHA-256 genesis audit chain
        record_audit_log(
            db=db,
            user_id="lead_advisor_engine",
            action="COMPUTE_TOP_LEADS",
            case_id=case_id,
            object_type="analysis_run",
            object_id=run_id,
            details={
                "run_id": run_id,
                "n_leads": len(results),
                "top_entity": results[0]["entity_id"] if results else None,
                "top_score": results[0]["score"] if results else 0.0,
            }
        )

    return results


def get_stored_or_computed_top_leads(
    db: Session,
    case_id: str,
    n: int = 5,
    recompute: bool = False
) -> List[Dict[str, Any]]:
    """
    Retrieves stored top leads from DB without recomputing (fast reload),
    or triggers computation if none are persisted or recompute=True.
    """
    if not recompute:
        stored = db.query(AnalysisResult).filter(
            AnalysisResult.case_id == case_id
        ).order_by(AnalysisResult.rank.asc()).limit(n).all()

        if stored:
            results = []
            for ar in stored:
                try:
                    bk = json.loads(ar.breakdown_json or "{}")
                except Exception:
                    bk = {}
                try:
                    evs = json.loads(ar.evidence_ids or "[]")
                except Exception:
                    evs = []

                results.append({
                    "rank": ar.rank,
                    "designation": f"Primary Attributed Lead #{ar.rank}",
                    "entity_id": ar.entity_id,
                    "label": "Entity",
                    "display_name": ar.entity_id,
                    "score": ar.score,
                    "breakdown": bk,
                    "evidence_sources": evs,
                    "disclaimer": LEGAL_DISCLAIMER,
                })
            return results

    return compute_case_top_leads(db=db, case_id=case_id, n=n, persist=True)


# Backwards compatibility and test convenience aliases
compute_top_leads = compute_case_top_leads
get_persisted_top_leads = get_stored_or_computed_top_leads

