import networkx as nx
from typing import Dict, Any, List, Set, Tuple, Optional

def _resolve_master_profile(detail_graph: nx.MultiDiGraph, owner_key: str) -> str:
    """If owner_key is a Person resolved to a MasterProfile, returns the MasterProfile key."""
    if not detail_graph.has_node(owner_key):
        return owner_key
    if detail_graph.nodes[owner_key].get("label") == "Person":
        for succ in detail_graph.successors(owner_key):
            if detail_graph.nodes[succ].get("label") == "MasterProfile":
                for edge in detail_graph.get_edge_data(owner_key, succ).values():
                    if edge.get("type") == "RESOLVED_TO":
                        return succ
    return owner_key

def resolve_entity_of(detail_graph: nx.MultiDiGraph, node_key: str) -> str:
    """
    Resolves the canonical entity owner for a detail node.
    - If node has a single unambiguous Person/Organization owner (via USES/OWNS), returns that owner (or MasterProfile if resolved).
    - If multiple distinct owners link to it, checks if they all resolve to the same MasterProfile; if not, marks shared=True and returns node itself.
    - If unowned (e.g. CDR-only or unlinked account), returns node itself.
    """
    if not detail_graph.has_node(node_key):
        return node_key

    node_data = detail_graph.nodes[node_key]
    label = node_data.get("label")

    if label == "MasterProfile":
        return node_key

    if label == "Person":
        return _resolve_master_profile(detail_graph, node_key)
    if label == "Organization":
        return node_key

    # Check incoming USES, OWNS, DRIVES edges
    owners = set()
    for pred in detail_graph.predecessors(node_key):
        pred_label = detail_graph.nodes[pred].get("label")
        if pred_label in ["Person", "Organization"]:
            edge_data = detail_graph.get_edge_data(pred, node_key)
            if edge_data:
                for edge in edge_data.values():
                    if edge.get("type") in ["USES", "OWNS", "DRIVES"]:
                        owners.add(pred)

    if len(owners) == 1:
        return _resolve_master_profile(detail_graph, list(owners)[0])
    elif len(owners) > 1:
        resolved_owners = set(_resolve_master_profile(detail_graph, ow) for ow in owners)
        if len(resolved_owners) == 1:
            return list(resolved_owners)[0]
        else:
            detail_graph.nodes[node_key]["shared"] = True
            return node_key

    return node_key

def build_entity_projection(detail_graph: nx.MultiDiGraph) -> nx.MultiGraph:
    """
    Builds the Entity-level graph where calls and transfers are collapsed
    onto their unambiguous entity owners (or self if unowned).
    Edges: COMMUNICATES_WITH (undirected), PAID (directed logic stored).
    """
    eg = nx.MultiGraph()

    # Pre-resolve entity map for all detail nodes
    entity_map: Dict[str, str] = {}
    for n in detail_graph.nodes():
        entity_map[n] = resolve_entity_of(detail_graph, n)

    # Add entity nodes
    for orig_key, ent_key in entity_map.items():
        if not eg.has_node(ent_key):
            orig_data = detail_graph.nodes[ent_key]
            eg.add_node(
                ent_key,
                case_id=orig_data.get("case_id"),
                label=orig_data.get("label"),
                id=orig_data.get("id"),
                name=orig_data.get("name"),
                shared=orig_data.get("shared", False),
                degree=0
            )

    # 1. Project CALLED edges -> COMMUNICATES_WITH
    comm_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for u, v, k, d in detail_graph.edges(keys=True, data=True):
        if d.get("type") == "CALLED":
            u_ent = entity_map[u]
            v_ent = entity_map[v]
            if u_ent != v_ent:
                pair = tuple(sorted([u_ent, v_ent]))
                if pair not in comm_edges:
                    comm_edges[pair] = {
                        "calls": 0,
                        "phones": set(),
                        "first_call": d.get("first_call"),
                        "last_call": d.get("last_call")
                    }
                comm_edges[pair]["calls"] += d.get("count", 1)
                comm_edges[pair]["phones"].add(detail_graph.nodes[u].get("id"))
                comm_edges[pair]["phones"].add(detail_graph.nodes[v].get("id"))

    for (src, dst), info in comm_edges.items():
        eg.add_edge(
            src, dst,
            key=f"comm_{src}_{dst}",
            type="COMMUNICATES_WITH",
            calls=info["calls"],
            phones=list(info["phones"]),
            method="derived",
            confidence=1.0
        )

    # 2. Project TRANSFERRED_TO edges -> PAID
    paid_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for u, v, k, d in detail_graph.edges(keys=True, data=True):
        if d.get("type") == "TRANSFERRED_TO":
            u_ent = entity_map[u]
            v_ent = entity_map[v]
            if u_ent != v_ent:
                pair = (u_ent, v_ent)
                if pair not in paid_edges:
                    paid_edges[pair] = {
                        "total_paise": 0,
                        "txn_count": 0,
                        "txn_keys": []
                    }
                paid_edges[pair]["total_paise"] += d.get("amount_paise", 0)
                paid_edges[pair]["txn_count"] += 1
                paid_edges[pair]["txn_keys"].append(d.get("key"))

    for (src, dst), info in paid_edges.items():
        eg.add_edge(
            src, dst,
            key=f"paid_{src}_{dst}",
            type="PAID",
            total_paise=info["total_paise"],
            amount_inr=info["total_paise"] / 100.0,
            txn_count=info["txn_count"],
            txn_keys=info["txn_keys"][:50],
            method="derived",
            confidence=1.0
        )

    # 3. Project USES, OWNS, DRIVES links for uncollapsed/shared nodes
    for u, v, k, d in detail_graph.edges(keys=True, data=True):
        if d.get("type") in ["USES", "OWNS", "DRIVES"]:
            u_ent = entity_map[u]
            v_ent = entity_map[v]
            if u_ent != v_ent:
                link_key = f"rel_{u_ent}_{v_ent}_{d.get('type')}"
                if not eg.has_edge(u_ent, v_ent, key=link_key):
                    eg.add_edge(
                        u_ent, v_ent,
                        key=link_key,
                        type=d.get("type"),
                        method=d.get("method", "derived"),
                        confidence=d.get("confidence", 1.0)
                    )

    # Update degrees
    for n in eg.nodes():
        eg.nodes[n]["degree"] = eg.degree(n)

    return eg

def expand_hops_subgraph(
    graph: nx.Graph,
    seed_keys: List[str],
    hops: int = 1,
    limit: int = 200
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """
    Breadth-first search expansion up to `hops` layers (1 to 4).
    Returns (nodes_list, edges_list, truncated_flag).
    """
    visited_nodes: Set[str] = set()
    current_layer: Set[str] = set([k for k in seed_keys if graph.has_node(k)])
    visited_nodes.update(current_layer)

    hops = max(1, min(4, hops))

    for _ in range(hops):
        next_layer = set()
        for node in current_layer:
            for neighbor in graph.neighbors(node):
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    next_layer.add(neighbor)
                    if len(visited_nodes) >= limit:
                        break
            if len(visited_nodes) >= limit:
                break
        current_layer = next_layer
        if len(visited_nodes) >= limit:
            break

    truncated = (len(visited_nodes) >= limit)
    subgraph = graph.subgraph(visited_nodes)

    # Format nodes
    nodes_res = []
    for n in subgraph.nodes():
        d = dict(subgraph.nodes[n])
        d["key"] = n
        nodes_res.append(d)

    # Format edges
    edges_res = []
    seen_edges = set()
    for u, v, k, d in subgraph.edges(keys=True, data=True):
        edge_id = d.get("key") or f"{u}_{v}_{k}"
        if edge_id not in seen_edges:
            seen_edges.add(edge_id)
            e_dict = dict(d)
            e_dict["source"] = u
            e_dict["target"] = v
            e_dict["id"] = edge_id
            edges_res.append(e_dict)

    return nodes_res, edges_res, truncated

def find_shortest_path_nodes(
    graph: nx.Graph,
    from_key: str,
    to_key: str
) -> Optional[List[str]]:
    """Calculates shortest path sequence between two nodes up to length 6."""
    if not graph.has_node(from_key) or not graph.has_node(to_key):
        return None
    try:
        path = nx.shortest_path(graph, source=from_key, target=to_key)
        return path if len(path) <= 7 else None
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
