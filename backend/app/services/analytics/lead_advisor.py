import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional, Tuple
import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms.community import louvain_communities

from backend.app.db.sql import (
    CallRecord, Transaction, Entity, EntityLink, ExtractedEntity, EvidenceFile, Alert
)

PATTERNS_YAML_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "patterns.yaml"

def parse_date_str(val: Any) -> Optional[datetime]:
    if not val:
        return None
    val_str = str(val).strip()
    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
        try:
            return datetime.strptime(val_str[:10] if len(fmt) == 8 or len(fmt) == 10 else val_str[:19], fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(val_str.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def load_pattern_library() -> List[Dict[str, Any]]:
    if PATTERNS_YAML_PATH.exists():
        try:
            with open(PATTERNS_YAML_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("patterns", [])
        except Exception:
            pass
    return []

def compute_lead_advisor(
    case_id: str,
    entities: List[Entity],
    entity_links: List[EntityLink],
    call_records: List[CallRecord],
    transactions: List[Transaction],
    evidence_files: List[EvidenceFile],
    extracted_entities: List[ExtractedEntity],
    alerts: List[Dict[str, Any]],
    settings: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Computes explainable, data-driven investigative leads for the Lead Advisor engine (Hero #3).
    All thresholds and weights are dynamically loaded from settings / defaults.yaml.
    Calculates 5 normalized signals:
      1. money_flow (weight: 30)
      2. bridge (weight: 25)
      3. unusual_communication (weight: 20)
      4. timing (weight: 15)
      5. multi_document (weight: 10)
    Follows strict Availability Principle: unuploaded data types are marked 'not available'
    and priority is normalized across available weights. Never fakes zeros.
    Prejudicial Terminology Defense: NO prior-conviction-history signal is included to eliminate bias.
    """
    advisor_cfg = settings.get("lead_advisor", {})
    weights_cfg = advisor_cfg.get("weights", {
        "money_flow": 30,
        "bridge": 25,
        "unusual_communication": 20,
        "timing": 15,
        "multi_document": 10
    })
    levels_cfg = advisor_cfg.get("levels", {
        "high_priority_min": 70,
        "medium_priority_min": 40
    })

    w_money = float(weights_cfg.get("money_flow", 30))
    w_bridge = float(weights_cfg.get("bridge", 25))
    w_comm = float(weights_cfg.get("unusual_communication", 20))
    w_timing = float(weights_cfg.get("timing", 15))
    w_doc = float(weights_cfg.get("multi_document", 10))

    high_thresh = float(levels_cfg.get("high_priority_min", 70))
    med_thresh = float(levels_cfg.get("medium_priority_min", 40))

    patterns_lib = load_pattern_library()

    # Determine uploaded data types in the case
    uploaded_types = set(e.detected_type.lower() for e in evidence_files if e.detected_type)
    has_bank_data = len(transactions) > 0 or any("bank" in t for t in uploaded_types)
    has_cdr_data = len(call_records) > 0 or any("cdr" in t for t in uploaded_types)
    has_doc_data = len(extracted_entities) > 0 or any(t in ["fir", "document"] for t in uploaded_types)

    # -------------------------------------------------------------
    # 1. Map Entity Connections & Graph Structure
    # -------------------------------------------------------------
    # Build entity-level network
    G = nx.Graph()
    for ent in entities:
        G.add_node(ent.canonical_id, label=ent.label, display_name=ent.display_name or ent.canonical_id)

    for link in entity_links:
        G.add_edge(link.source_entity_id, link.target_entity_id, rel=link.relationship_type)

    # Also add call graph edges and endpoints
    for c in call_records:
        if c.caller and c.receiver:
            if c.caller not in G:
                G.add_node(c.caller, label="Phone", display_name=c.caller)
            if c.receiver not in G:
                G.add_node(c.receiver, label="Phone", display_name=c.receiver)
            G.add_edge(c.caller, c.receiver, rel="CALLS")

    # Also add bank transaction edges and endpoints
    for t in transactions:
        if t.from_account and t.to_account:
            if t.from_account not in G:
                G.add_node(t.from_account, label="BankAccount", display_name=t.from_name or t.from_account)
            if t.to_account not in G:
                G.add_node(t.to_account, label="BankAccount", display_name=t.to_name or t.to_account)
            G.add_edge(t.from_account, t.to_account, rel="TRANSFERRED_TO")

    # Graph Centrality & Louvain Communities
    betweenness_map: Dict[str, float] = {}
    node_comm_map: Dict[str, int] = {}
    max_bw = 0.0

    if G.number_of_nodes() >= 3:
        try:
            betweenness_map = nx.betweenness_centrality(G, seed=42)
            max_bw = max(betweenness_map.values()) if betweenness_map else 1.0
            comms = louvain_communities(G, seed=42)
            for c_id, comm_nodes in enumerate(comms):
                for node in comm_nodes:
                    node_comm_map[node] = c_id
        except Exception:
            pass

    # -------------------------------------------------------------
    # 2. Transaction Throughput & Percentiles
    # -------------------------------------------------------------
    inflows: Dict[str, int] = {}
    outflows: Dict[str, int] = {}
    all_txn_amounts = [t.amount_paise for t in transactions]
    p90_amount = float(np.percentile(all_txn_amounts, 90)) if all_txn_amounts else 0.0

    for t in transactions:
        outflows[t.from_account] = outflows.get(t.from_account, 0) + t.amount_paise
        inflows[t.to_account] = inflows.get(t.to_account, 0) + t.amount_paise

    # Throughput = min(inflow, outflow) for accounts with both flow
    all_accounts = set(inflows.keys()).union(set(outflows.keys()))
    throughput_map: Dict[str, int] = {}
    for acc in all_accounts:
        tp = min(inflows.get(acc, 0), outflows.get(acc, 0))
        if tp > 0:
            throughput_map[acc] = tp

    tp_values = sorted(list(throughput_map.values()))
    def get_throughput_percentile(val: int) -> float:
        if not tp_values or val <= 0:
            return 0.0
        # Percentile rank in 0..1 (fraction of values <= val)
        idx = int(np.searchsorted(tp_values, val, side="right"))
        return float(idx / len(tp_values))

    # Entity to accounts mapping
    entity_accounts: Dict[str, Set[str]] = {}
    entity_phones: Dict[str, Set[str]] = {}

    for link in entity_links:
        # Check if link connects Person/Organization to BankAccount or Phone
        src, tgt = link.source_entity_id, link.target_entity_id
        rel = link.relationship_type
        if rel in ["OWNS", "BENEFICIARY_OF", "OPERATES"]:
            entity_accounts.setdefault(src, set()).add(tgt)
            entity_accounts.setdefault(tgt, set()).add(src)
        if rel in ["USES", "CALLS", "CONTACT"]:
            entity_phones.setdefault(src, set()).add(tgt)
            entity_phones.setdefault(tgt, set()).add(src)

    # If entity itself is an account or phone:
    for ent in entities:
        if ent.label in ["BankAccount", "Account"]:
            entity_accounts.setdefault(ent.canonical_id, set()).add(ent.canonical_id)
        if ent.label in ["Phone", "Mobile"]:
            entity_phones.setdefault(ent.canonical_id, set()).add(ent.canonical_id)

    # -------------------------------------------------------------
    # 3. Communication Alert Indexing
    # -------------------------------------------------------------
    comm_alerts_by_phone: Dict[str, List[Dict[str, Any]]] = {}
    for a in alerts:
        ent_id = a.get("entity_id", "")
        # Could be phone or pair "p1 <-> p2"
        if "<->" in ent_id:
            p1, p2 = [p.strip() for p in ent_id.split("<->")]
            comm_alerts_by_phone.setdefault(p1, []).append(a)
            comm_alerts_by_phone.setdefault(p2, []).append(a)
        else:
            comm_alerts_by_phone.setdefault(ent_id, []).append(a)

    # -------------------------------------------------------------
    # 4. Total Case Documents for Multi-Document Signal
    # -------------------------------------------------------------
    doc_evidence_ids = set(
        e.id for e in evidence_files
        if e.detected_type in ["fir", "document"] or e.original_name.endswith((".pdf", ".docx", ".txt"))
    )
    total_case_docs = max(len(doc_evidence_ids), 1)

    # -------------------------------------------------------------
    # 5. Evaluate Leads for each Entity
    # -------------------------------------------------------------
    leads: List[Dict[str, Any]] = []

    # Filter to substantive entities (Persons, Organizations, Accounts, Phones)
    target_entities = [e for e in entities if e.label in ["Person", "Organization", "BankAccount", "Phone", "Vehicle"]]
    if not target_entities:
        derived_candidates = []
        seen_cand_ids = set()
        for c in call_records:
            if c.caller and c.caller not in seen_cand_ids:
                seen_cand_ids.add(c.caller)
                derived_candidates.append(Entity(case_id=case_id, label="Phone", canonical_id=c.caller, display_name=c.caller))
            if c.receiver and c.receiver not in seen_cand_ids:
                seen_cand_ids.add(c.receiver)
                derived_candidates.append(Entity(case_id=case_id, label="Phone", canonical_id=c.receiver, display_name=c.receiver))
        for t in transactions:
            if t.from_account and t.from_account not in seen_cand_ids:
                seen_cand_ids.add(t.from_account)
                derived_candidates.append(Entity(case_id=case_id, label="BankAccount", canonical_id=t.from_account, display_name=t.from_name or t.from_account))
            if t.to_account and t.to_account not in seen_cand_ids:
                seen_cand_ids.add(t.to_account)
                derived_candidates.append(Entity(case_id=case_id, label="BankAccount", canonical_id=t.to_account, display_name=t.to_name or t.to_account))
        target_entities = derived_candidates

    for ent in target_entities:
        ent_id = ent.canonical_id
        ent_display = ent.display_name or ent_id
        ent_label = ent.label

        signals: List[Dict[str, Any]] = []

        # --- SIGNAL 1: MONEY FLOW (Weight: 30) ---
        if not has_bank_data:
            signals.append({
                "name": "money_flow",
                "label": "Financial Money Flow",
                "weight": w_money,
                "score": 0.0,
                "max_score": 1.0,
                "is_available": False,
                "explanation": "Not available: No banking statements or transaction logs were uploaded for this case."
            })
        else:
            accs = entity_accounts.get(ent_id, set())
            if not accs and ent_label in ["BankAccount", "Account"]:
                accs = {ent_id}

            ent_throughput = max([throughput_map.get(a, 0) for a in accs], default=0)
            tp_rank = get_throughput_percentile(ent_throughput)

            # Check if any account has money anomaly alerts
            has_anomaly = any(
                a.get("entity_id") in accs and a.get("pattern_type") in ["fan_in", "fan_out", "rapid_pass_through"]
                for a in alerts
            )
            score_mf = round((0.6 * tp_rank) + (0.4 * (1.0 if has_anomaly else 0.0)), 2)

            expl_mf = (
                f"Peak throughput: Rs. {(ent_throughput / 100):,.2f} "
                f"(case percentile rank: {int(tp_rank * 100)}th percentile). "
                f"Carries flow anomaly alerts: {'Yes' if has_anomaly else 'No'}."
            )
            signals.append({
                "name": "money_flow",
                "label": "Financial Money Flow",
                "weight": w_money,
                "score": score_mf,
                "max_score": 1.0,
                "is_available": True,
                "explanation": expl_mf
            })

        # --- SIGNAL 2: BRIDGE (Weight: 25) ---
        if G.number_of_edges() == 0:
            signals.append({
                "name": "bridge",
                "label": "Network Bridge Topology",
                "weight": w_bridge,
                "score": 0.0,
                "max_score": 1.0,
                "is_available": False,
                "explanation": "Not available: No relational connections or communication links exist in the case graph."
            })
        else:
            bw = betweenness_map.get(ent_id, 0.0)
            norm_bw = (bw / max_bw) if max_bw > 0 else 0.0

            # Community connectivity
            neighbors = list(G.neighbors(ent_id)) if ent_id in G else []
            nbr_comms = set(node_comm_map[n] for n in neighbors if n in node_comm_map)
            is_multi_comm = len(nbr_comms) >= 2

            score_br = round((0.5 * norm_bw) + (0.5 * (1.0 if is_multi_comm else 0.0)), 2)
            expl_br = (
                f"Betweenness centrality: {bw:.4f} (relative: {norm_bw:.2f}). "
                f"Adjacent to {len(nbr_comms)} distinct operational clusters "
                f"({'bridges multiple clusters' if is_multi_comm else 'within single cluster'})."
            )
            signals.append({
                "name": "bridge",
                "label": "Network Bridge Topology",
                "weight": w_bridge,
                "score": score_br,
                "max_score": 1.0,
                "is_available": True,
                "explanation": expl_br
            })

        # --- SIGNAL 3: UNUSUAL COMMUNICATION (Weight: 20) ---
        if not has_cdr_data:
            signals.append({
                "name": "unusual_communication",
                "label": "Unusual Communication Patterns",
                "weight": w_comm,
                "score": 0.0,
                "max_score": 1.0,
                "is_available": False,
                "explanation": "Not available: No Call Detail Records (CDRs) were uploaded for this case."
            })
        else:
            ph_list = entity_phones.get(ent_id, set())
            if not ph_list and ent_label in ["Phone", "Mobile"]:
                ph_list = {ent_id}

            ent_comm_alerts: List[Dict[str, Any]] = []
            for ph in ph_list:
                ent_comm_alerts.extend(comm_alerts_by_phone.get(ph, []))

            if not ent_comm_alerts:
                score_comm = 0.0
                expl_comm = "No anomalous spikes, frequent pair outliers, or new connection surges detected on associated phone lines."
            else:
                max_ratio = max([a.get("metrics", {}).get("ratio", 1.0) for a in ent_comm_alerts], default=1.0)
                score_comm = round(min(max_ratio, 1.0), 2)
                best_alert = ent_comm_alerts[0]
                expl_comm = f"Triggered {len(ent_comm_alerts)} communication alert(s). Strongest: {best_alert.get('pattern_type')} ({best_alert.get('explanation')[:120]})."

            signals.append({
                "name": "unusual_communication",
                "label": "Unusual Communication Patterns",
                "weight": w_comm,
                "score": score_comm,
                "max_score": 1.0,
                "is_available": True,
                "explanation": expl_comm
            })

        # --- SIGNAL 4: TIMING COINCIDENCE (Weight: 15) ---
        if not (has_bank_data and has_cdr_data):
            signals.append({
                "name": "timing",
                "label": "Call & Fund Transfer Timing Coincidence",
                "weight": w_timing,
                "score": 0.0,
                "max_score": 1.0,
                "is_available": False,
                "explanation": "Not available: Requires both Call Detail Records and Bank Statement logs to evaluate cross-modal timing coincidence."
            })
        else:
            # Check timing delta between entity's communication alerts and large transactions touching entity's accounts
            ph_list = entity_phones.get(ent_id, set())
            accs = entity_accounts.get(ent_id, set())
            ent_comm_alerts = [a for ph in ph_list for a in comm_alerts_by_phone.get(ph, [])]

            ent_large_txns = [
                t for t in transactions
                if (t.from_account in accs or t.to_account in accs) and t.amount_paise >= p90_amount
            ]

            min_days_delta = 999.0
            for a in ent_comm_alerts:
                a_dt = parse_date_str(a.get("date"))
                if not a_dt:
                    continue
                for t in ent_large_txns:
                    t_dt = parse_date_str(t.date_iso)
                    if t_dt:
                        delta = abs((a_dt - t_dt).total_seconds() / 86400.0)
                        if delta < min_days_delta:
                            min_days_delta = delta

            if min_days_delta <= 2.0:
                score_timing = 1.0
                expl_timing = f"High temporal correlation: Call anomaly occurred within {min_days_delta:.1f} days of a major fund transfer (>= p90 threshold of Rs. {(p90_amount / 100):,.2f})."
            elif min_days_delta <= 7.0:
                # Linear decay from 1.0 at 2 days to 0.0 at 7 days
                score_timing = round(1.0 - ((min_days_delta - 2.0) / 5.0), 2)
                expl_timing = f"Moderate temporal correlation: Call anomaly occurred {min_days_delta:.1f} days from a high-value transaction."
            else:
                score_timing = 0.0
                expl_timing = "No synchronous coincidence detected between call activity and high-value transactions within 7 days."

            signals.append({
                "name": "timing",
                "label": "Call & Fund Transfer Timing Coincidence",
                "weight": w_timing,
                "score": score_timing,
                "max_score": 1.0,
                "is_available": True,
                "explanation": expl_timing
            })

        # --- SIGNAL 5: MULTI-DOCUMENT PRESENCE (Weight: 10) ---
        if not has_doc_data:
            signals.append({
                "name": "multi_document",
                "label": "Cross-Document Legal Mentions",
                "weight": w_doc,
                "score": 0.0,
                "max_score": 1.0,
                "is_available": False,
                "explanation": "Not available: No FIR narrative or case complaint documents were ingested for this case."
            })
        else:
            # Count distinct documents linked to this entity directly or within 2 hops
            linked_docs = set()
            for ee in extracted_entities:
                if ee.status == "approved" and ee.normalized_value == ent_id:
                    linked_docs.add(ee.evidence_id)

            # Check graph neighbors
            if ent_id in G:
                for nbr in G.neighbors(ent_id):
                    for ee in extracted_entities:
                        if ee.status == "approved" and ee.normalized_value == nbr:
                            linked_docs.add(ee.evidence_id)

            doc_ratio = min(len(linked_docs) / total_case_docs, 1.0)
            score_doc = round(doc_ratio, 2)
            expl_doc = f"Linked across {len(linked_docs)} distinct case document(s) out of {total_case_docs} total document(s)."

            signals.append({
                "name": "multi_document",
                "label": "Cross-Document Legal Mentions",
                "weight": w_doc,
                "score": score_doc,
                "max_score": 1.0,
                "is_available": True,
                "explanation": expl_doc
            })

        # -------------------------------------------------------------
        # 6. Priority Calculation & Availability Normalization
        # -------------------------------------------------------------
        avail_signals = [s for s in signals if s["is_available"]]
        total_avail_weight = sum(s["weight"] for s in avail_signals)

        if total_avail_weight > 0:
            weighted_score_sum = sum(s["score"] * s["weight"] for s in avail_signals)
            priority = round((weighted_score_sum / total_avail_weight) * 100.0, 1)
        else:
            priority = 0.0

        if priority >= high_thresh:
            level = "HIGH"
        elif priority >= med_thresh:
            level = "MEDIUM"
        else:
            level = "LOW"

        # -------------------------------------------------------------
        # 7. Pattern Matching & Missing Data Identification
        # -------------------------------------------------------------
        matched_pattern = None
        missing_data: List[str] = []
        suggested_next_steps: List[str] = []

        # Find best matching pattern archetype
        signal_scores_map = {s["name"]: s["score"] for s in avail_signals}

        for pat in patterns_lib:
            req_sigs = pat.get("signals_required", [])
            # If all required signals are available and have positive scores
            if all(signal_scores_map.get(rs, 0.0) >= 0.4 for rs in req_sigs):
                matched_pattern = {
                    "id": pat["id"],
                    "name": pat["name"],
                    "description": pat["description"]
                }
                # Check missing data from required_data
                req_data_list = pat.get("required_data", [])
                for rd in req_data_list:
                    rd_low = rd.lower()
                    if "kyc" in rd_low and "kyc" not in uploaded_types:
                        missing_data.append(rd)
                    elif "statement" in rd_low and not has_bank_data:
                        missing_data.append(rd)
                    elif ("tower" in rd_low or "location" in rd_low) and "tower" not in uploaded_types:
                        missing_data.append(rd)
                    elif ("sdr" in rd_low or "sim" in rd_low) and "sdr" not in uploaded_types:
                        missing_data.append(rd)
                    elif ("imei" in rd_low or "device" in rd_low) and not any(c.imei for c in call_records):
                        missing_data.append(rd)

                suggested_next_steps = pat.get("suggested_next_steps", [])
                break

        # Fallback default next steps if no specific pattern matched
        if not suggested_next_steps:
            if level == "HIGH":
                suggested_next_steps = [
                    "Verify KYC and account operational mandate with relevant banking nodal officer.",
                    "Requisition call data records and subscriber details for primary linked phone numbers.",
                    "Review cross-document citations with case investigation team."
                ]
            else:
                suggested_next_steps = [
                    "Monitor ongoing transactions and communication patterns for threshold escalation."
                ]

        # Confidence rating
        if len(avail_signals) >= 4 and len(missing_data) <= 1:
            confidence = "High"
        elif len(avail_signals) >= 2:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Collect evidence IDs
        ev_ids = set()
        for s in avail_signals:
            if s["name"] == "unusual_communication":
                for ph in entity_phones.get(ent_id, set()):
                    for a in comm_alerts_by_phone.get(ph, []):
                        ev_ids.update(a.get("evidence_ids", []))
            elif s["name"] == "money_flow":
                for a in entity_accounts.get(ent_id, set()):
                    for t in transactions:
                        if t.from_account == a or t.to_account == a:
                            ev_ids.add(t.id)

        leads.append({
            "id": f"lead_{ent_id}",
            "entity_id": ent_id,
            "display_name": ent_display,
            "entity_type": ent_label,
            "priority": priority,
            "level": level,
            "confidence": confidence,
            "signals": signals,
            "matched_pattern": matched_pattern,
            "missing_data": missing_data,
            "suggested_next_steps": suggested_next_steps,
            "evidence_ids": list(ev_ids)[:15],
            "disclaimer": "Lead for review — not a finding of wrongdoing."
        })

    # Sort leads by priority descending
    leads.sort(key=lambda x: x["priority"], reverse=True)
    return leads
