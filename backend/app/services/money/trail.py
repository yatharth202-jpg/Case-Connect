import json
from decimal import Decimal
from typing import Dict, Any, List, Set, Optional, Tuple
import networkx as nx
from sqlalchemy.orm import Session
from backend.app.db.sql import Transaction, Entity, EntityLink
from backend.app.services.money.patterns import detect_money_patterns

def build_money_trail(
    db: Session,
    case_id: str,
    account_query: Optional[str] = None,
    min_amount_rupees: float = 0.0,
    hops: int = 2,
    direction: str = "both", # "in", "out", "both"
    limit: int = 200,
    case_settings: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Constructs the BankAccount-level Money Trail subgraph.
    - Focuses on a seed account (or highest volume account if unspecified).
    - Traverses directed transfers up to `hops` layers.
    - Filters edges by `min_amount_rupees` (converted to exact integer paise).
    - Preserves below-threshold connections as `hidden_edges` for dashed rendering.
    - Computes summary totals and detects pattern anomalies with provenance.
    """
    hops = max(1, min(4, hops))
    min_amount_paise = int(Decimal(str(min_amount_rupees or 0.0)) * 100)
    case_settings = case_settings or {}

    # 1. Fetch transactions for the case
    txns = db.query(Transaction).filter(Transaction.case_id == case_id).all()
    if not txns:
        return {
            "nodes": [],
            "edges": [],
            "hidden_edges": [],
            "focus_account": None,
            "totals": {
                "inflow_paise": 0, "outflow_paise": 0, "net_paise": 0,
                "inflow_inr": 0.0, "outflow_inr": 0.0, "net_inr": 0.0,
                "txn_count": 0, "counterparties": 0
            },
            "ordered_paths": [],
            "patterns": [],
            "candidates": [],
            "truncated": False,
            "meta": {"hops": hops, "direction": direction, "min_amount_inr": min_amount_rupees}
        }

    # 2. Extract account holders
    account_names: Dict[str, str] = {}
    for t in txns:
        if t.from_account and t.from_name and t.from_account not in account_names:
            account_names[t.from_account] = t.from_name.strip()
        if t.to_account and t.to_name and t.to_account not in account_names:
            account_names[t.to_account] = t.to_name.strip()

    # Also query Entity staging
    entities = db.query(Entity).filter(Entity.case_id == case_id, Entity.label.in_(["BankAccount", "Person"])).all()
    for ent in entities:
        if ent.label == "BankAccount" and ent.display_name and ent.canonical_id not in account_names:
            account_names[ent.canonical_id] = ent.display_name

    # 3. Disambiguate or pick focus account
    all_accounts = set()
    account_volume: Dict[str, int] = {}
    for t in txns:
        all_accounts.add(t.from_account)
        all_accounts.add(t.to_account)
        account_volume[t.from_account] = account_volume.get(t.from_account, 0) + t.amount_paise
        account_volume[t.to_account] = account_volume.get(t.to_account, 0) + t.amount_paise

    focus_account = None
    candidates = []

    if account_query and account_query.strip():
        q_norm = account_query.strip().lower()
        exact_matches = []
        partial_matches = []

        for acc in all_accounts:
            name = account_names.get(acc, "")
            if q_norm == acc.lower() or q_norm == name.lower():
                exact_matches.append(acc)
            elif q_norm in acc.lower() or (name and q_norm in name.lower()):
                partial_matches.append(acc)

        matches = exact_matches or partial_matches
        if len(matches) > 1 and not exact_matches:
            candidates = [
                {
                    "account": a,
                    "holder_name": account_names.get(a, a),
                    "volume_inr": account_volume.get(a, 0) / 100.0
                }
                for a in matches[:15]
            ]
            return {
                "nodes": [],
                "edges": [],
                "hidden_edges": [],
                "focus_account": None,
                "totals": {"inflow_paise": 0, "outflow_paise": 0, "net_paise": 0, "inflow_inr": 0.0, "outflow_inr": 0.0, "net_inr": 0.0, "txn_count": 0, "counterparties": 0},
                "ordered_paths": [],
                "patterns": [],
                "candidates": candidates,
                "truncated": False,
                "meta": {"hops": hops, "direction": direction, "min_amount_inr": min_amount_rupees}
            }
        elif matches:
            focus_account = matches[0]
        else:
            return {
                "nodes": [],
                "edges": [],
                "hidden_edges": [],
                "focus_account": None,
                "totals": {"inflow_paise": 0, "outflow_paise": 0, "net_paise": 0, "inflow_inr": 0.0, "outflow_inr": 0.0, "net_inr": 0.0, "txn_count": 0, "counterparties": 0},
                "ordered_paths": [],
                "patterns": [],
                "candidates": [],
                "truncated": False,
                "meta": {"hops": hops, "direction": direction, "min_amount_inr": min_amount_rupees}
            }
    else:
        # Default: Pick highest volume account
        if account_volume:
            focus_account = max(account_volume.items(), key=lambda x: x[1])[0]

    if not focus_account:
        return {
            "nodes": [],
            "edges": [],
            "hidden_edges": [],
            "focus_account": None,
            "totals": {"inflow_paise": 0, "outflow_paise": 0, "net_paise": 0, "inflow_inr": 0.0, "outflow_inr": 0.0, "net_inr": 0.0, "txn_count": 0, "counterparties": 0},
            "ordered_paths": [],
            "patterns": [],
            "candidates": [],
            "truncated": False,
            "meta": {"hops": hops, "direction": direction, "min_amount_inr": min_amount_rupees}
        }

    # 4. Collapse parallel transactions per account pair
    pair_txns: Dict[Tuple[str, str], List[Transaction]] = {}
    for t in txns:
        pair = (t.from_account, t.to_account)
        pair_txns.setdefault(pair, []).append(t)

    # Build directed graph of qualifying edges
    qualifying_graph = nx.DiGraph()
    all_pairs_graph = nx.DiGraph()

    for (u, v), t_list in pair_txns.items():
        total_p = sum(t.amount_paise for t in t_list)
        all_pairs_graph.add_edge(u, v, total_paise=total_p, txns=t_list)

        # Qualifying condition: at least one transaction meets filter OR sum meets filter
        # Per PLAYBOOK line 394: qualifying transactions amount >= filter
        qualifying_t_list = [t for t in t_list if t.amount_paise >= min_amount_paise]
        if qualifying_t_list:
            q_sum = sum(t.amount_paise for t in qualifying_t_list)
            qualifying_graph.add_edge(u, v, total_paise=q_sum, txns=qualifying_t_list)

    # 5. BFS Hop expansion from focus_account
    visited_nodes: Set[str] = {focus_account}
    current_layer: Set[str] = {focus_account}
    truncated = False

    for _ in range(hops):
        next_layer = set()
        for node in current_layer:
            # Outflow neighbors (forward successors)
            if direction in ["out", "both"] and qualifying_graph.has_node(node):
                for succ in qualifying_graph.successors(node):
                    if succ not in visited_nodes:
                        visited_nodes.add(succ)
                        next_layer.add(succ)
                        if len(visited_nodes) >= limit:
                            truncated = True
                            break
            # Inflow neighbors (backward predecessors)
            if direction in ["in", "both"] and qualifying_graph.has_node(node):
                for pred in qualifying_graph.predecessors(node):
                    if pred not in visited_nodes:
                        visited_nodes.add(pred)
                        next_layer.add(pred)
                        if len(visited_nodes) >= limit:
                            truncated = True
                            break
            if truncated:
                break
        current_layer = next_layer
        if truncated or not current_layer:
            break

    # 6. Build visible edges and hidden edges
    visible_edges = []
    hidden_edges = []

    for u in visited_nodes:
        for v in visited_nodes:
            if u == v:
                continue
            pair = (u, v)
            if pair not in pair_txns:
                continue

            t_list = pair_txns[pair]
            qualifying_txns = [t for t in t_list if t.amount_paise >= min_amount_paise]
            below_txns = [t for t in t_list if t.amount_paise < min_amount_paise]

            # Qualifying Edge
            if qualifying_txns:
                tot_q = sum(t.amount_paise for t in qualifying_txns)
                dates = [t.date_iso for t in qualifying_txns if t.date_iso]
                visible_edges.append({
                    "id": f"txn_{u}_{v}",
                    "source": u,
                    "target": v,
                    "type": "TRANSFERRED_TO",
                    "total_paise": tot_q,
                    "amount_inr": tot_q / 100.0,
                    "txn_count": len(qualifying_txns),
                    "first_date": min(dates) if dates else None,
                    "last_date": max(dates) if dates else None,
                    "references": [t.reference for t in qualifying_txns if t.reference][:10],
                    "txn_keys": [t.fingerprint for t in qualifying_txns],
                    "below_filter": False
                })

            # Hidden Edge (touching visible nodes but below min_amount)
            if below_txns and min_amount_paise > 0:
                tot_b = sum(t.amount_paise for t in below_txns)
                hidden_edges.append({
                    "id": f"hidden_{u}_{v}",
                    "source": u,
                    "target": v,
                    "type": "TRANSFERRED_TO",
                    "total_paise": tot_b,
                    "amount_inr": tot_b / 100.0,
                    "txn_count": len(below_txns),
                    "txn_keys": [t.fingerprint for t in below_txns],
                    "below_filter": True
                })

    # 7. Build nodes
    nodes = []
    for acc in visited_nodes:
        # Inflow / Outflow within case
        inflow = sum(t.amount_paise for t in txns if t.to_account == acc)
        outflow = sum(t.amount_paise for t in txns if t.from_account == acc)
        holder = account_names.get(acc, acc)

        nodes.append({
            "id": acc,
            "key": f"{case_id}|BankAccount|{acc}",
            "label": "BankAccount",
            "name": holder,
            "holder_name": holder,
            "account_number": acc,
            "inflow_paise": inflow,
            "outflow_paise": outflow,
            "inflow_inr": inflow / 100.0,
            "outflow_inr": outflow / 100.0,
            "is_focus": (acc == focus_account)
        })

    # 8. Focus Account Totals
    focus_in_txns = [t for t in txns if t.to_account == focus_account]
    focus_out_txns = [t for t in txns if t.from_account == focus_account]
    inflow_p = sum(t.amount_paise for t in focus_in_txns)
    outflow_p = sum(t.amount_paise for t in focus_out_txns)
    net_p = inflow_p - outflow_p
    counterparties = set(t.from_account for t in focus_in_txns) | set(t.to_account for t in focus_out_txns)

    totals = {
        "inflow_paise": inflow_p,
        "outflow_paise": outflow_p,
        "net_paise": net_p,
        "inflow_inr": inflow_p / 100.0,
        "outflow_inr": outflow_p / 100.0,
        "net_inr": net_p / 100.0,
        "txn_count": len(focus_in_txns) + len(focus_out_txns),
        "counterparties": len(counterparties)
    }

    # 9. Ordered Paths from focus_account
    sub_digraph = nx.DiGraph()
    for e in visible_edges:
        sub_digraph.add_edge(e["source"], e["target"], amount_inr=e["amount_inr"], total_paise=e["total_paise"], count=e["txn_count"])

    ordered_paths = []
    if sub_digraph.has_node(focus_account):
        # Find leaves or target nodes
        target_nodes = [n for n in sub_digraph.nodes() if n != focus_account]
        for tgt in target_nodes:
            if direction in ["out", "both"]:
                try:
                    for p in nx.all_simple_paths(sub_digraph, source=focus_account, target=tgt, cutoff=hops):
                        steps = []
                        for i in range(len(p) - 1):
                            edata = sub_digraph.get_edge_data(p[i], p[i+1])
                            steps.append({
                                "from": p[i],
                                "to": p[i+1],
                                "amount_inr": edata.get("amount_inr", 0),
                                "total_paise": edata.get("total_paise", 0)
                            })
                        ordered_paths.append({
                            "direction": "outflow",
                            "sequence": p,
                            "length": len(p) - 1,
                            "steps": steps
                        })
                        if len(ordered_paths) >= 25:
                            break
                except Exception:
                    pass

            if direction in ["in", "both"]:
                try:
                    for p in nx.all_simple_paths(sub_digraph, source=tgt, target=focus_account, cutoff=hops):
                        steps = []
                        for i in range(len(p) - 1):
                            edata = sub_digraph.get_edge_data(p[i], p[i+1])
                            steps.append({
                                "from": p[i],
                                "to": p[i+1],
                                "amount_inr": edata.get("amount_inr", 0),
                                "total_paise": edata.get("total_paise", 0)
                            })
                        ordered_paths.append({
                            "direction": "inflow",
                            "sequence": p,
                            "length": len(p) - 1,
                            "steps": steps
                        })
                        if len(ordered_paths) >= 50:
                            break
                except Exception:
                    pass

    # Sort paths by length and total volume
    ordered_paths.sort(key=lambda x: x["length"])

    # 10. Run Pattern Anomaly Detection on all case transactions for visible accounts
    patterns = detect_money_patterns(txns, case_settings, focus_accounts=visited_nodes)

    return {
        "nodes": nodes,
        "edges": visible_edges,
        "hidden_edges": hidden_edges,
        "focus_account": focus_account,
        "totals": totals,
        "ordered_paths": ordered_paths[:50],
        "patterns": patterns,
        "candidates": [],
        "truncated": truncated,
        "meta": {
            "hops": hops,
            "direction": direction,
            "min_amount_inr": min_amount_rupees,
            "count_nodes": len(nodes),
            "count_edges": len(visible_edges),
            "count_hidden_edges": len(hidden_edges)
        }
    }
