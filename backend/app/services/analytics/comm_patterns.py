import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional, Tuple
import pandas as pd
import numpy as np
import networkx as nx
from networkx.algorithms.community import louvain_communities

from backend.app.db.sql import CallRecord

def parse_date_str(d_str: Optional[str]) -> Optional[datetime]:
    if not d_str:
        return None
    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(str(d_str)[:10], fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(str(d_str).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def detect_communication_patterns(
    call_records: List[CallRecord],
    settings: Dict[str, Any],
    case_documents_earliest_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Detects communication anomalies across call detail records (CDRs) using case-configured thresholds.
    Algorithms:
      1. sudden_spike (per-phone median + k * 1.4826 * MAD over preceding historical window)
      2. very_frequent_pair (outliers in calls per pair above Q3 + 1.5 * IQR)
      3. sudden_new_connection (first call within X days of appearance with initial surge)
      4. shared_device (IMEI shared across >= 2 phones)
      5. bridge (high betweenness centrality connecting >= 2 Louvain communities)
    All thresholds are data-driven from settings/defaults.yaml and recorded in explanations.
    """
    if not call_records:
        return []

    comm_cfg = settings.get("communication", {})
    spike_cfg = comm_cfg.get("spike", {
        "mad_multiplier": 3.0,
        "baseline_window_days": 14,
        "min_history_days": 5,
        "min_call_floor": 5
    })
    freq_cfg = comm_cfg.get("frequent_pair", {"iqr_multiplier": 1.5})
    new_conn_cfg = comm_cfg.get("new_connection", {"window_days": 7, "min_early_calls": 5})
    bridge_cfg = comm_cfg.get("bridge", {"min_betweenness_ratio": 0.1})

    earliest_doc_dt = parse_date_str(case_documents_earliest_date)

    fallback_dt = datetime.utcnow()
    fallback_date_str = fallback_dt.strftime("%Y-%m-%d")

    # Convert records to DataFrame
    rows = []
    for c in call_records:
        dt = parse_date_str(c.datetime_iso or c.call_date)
        d_str = dt.strftime("%Y-%m-%d") if dt else fallback_date_str
        rows.append({
            "id": c.id,
            "caller": c.caller,
            "receiver": c.receiver,
            "date_str": d_str,
            "datetime": dt or fallback_dt,
            "duration": c.duration_seconds or 0,
            "imei": (c.imei or "").strip(),
            "source_file": c.source_file or "cdr"
        })

    df = pd.DataFrame(rows)
    alerts: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. SUDDEN SPIKE (Per-phone self-baseline median + k * 1.4826 * MAD)
    # -------------------------------------------------------------
    k_mad = float(spike_cfg.get("mad_multiplier", 3.0))
    window_days = int(spike_cfg.get("baseline_window_days", 14))
    min_history = int(spike_cfg.get("min_history_days", 5))
    min_floor = int(spike_cfg.get("min_call_floor", 5))

    # All distinct phones
    all_phones = set(df["caller"].unique()).union(set(df["receiver"].unique()))

    for phone in all_phones:
        phone_calls = df[(df["caller"] == phone) | (df["receiver"] == phone)]
        daily_counts = phone_calls.groupby("date_str")["id"].count().sort_index()

        # Need sufficient distinct days of activity
        if len(daily_counts) < min_history:
            continue

        dates_list = daily_counts.index.tolist()
        for idx, cur_date_str in enumerate(dates_list):
            cur_dt = datetime.strptime(cur_date_str, "%Y-%m-%d")
            cur_count = int(daily_counts[cur_date_str])

            # Preceding window dates strictly before cur_dt
            window_start = cur_dt - timedelta(days=window_days)
            hist_series = daily_counts[
                (daily_counts.index < cur_date_str) &
                (daily_counts.index >= window_start.strftime("%Y-%m-%d"))
            ]

            if len(hist_series) < min_history:
                continue

            hist_vals = hist_series.values
            med = float(np.median(hist_vals))
            mad = float(np.median(np.abs(hist_vals - med)))

            # Normal consistency factor
            threshold = med + (k_mad * 1.4826 * mad)
            effective_threshold = max(threshold, float(min_floor))

            if cur_count > effective_threshold:
                ratio = round(cur_count / effective_threshold, 2)
                severity = "high" if cur_count >= (2.0 * effective_threshold) else "medium"

                # Check difference relative to earliest FIR/document
                doc_diff_note = ""
                if earliest_doc_dt:
                    diff_days = (earliest_doc_dt - cur_dt).days
                    if diff_days > 0:
                        doc_diff_note = f" ({diff_days} days before first document)"

                expl = (
                    f"Call volume spiked to {cur_count} calls on {cur_date_str}{doc_diff_note}. "
                    f"Baseline median: {med:.1f}, MAD: {mad:.1f}, threshold: {effective_threshold:.1f} "
                    f"(multiplier: {k_mad}x, floor: {min_floor})."
                )

                call_ids = phone_calls[phone_calls["date_str"] == cur_date_str]["id"].tolist()[:10]
                alerts.append({
                    "pattern_type": "sudden_spike",
                    "entity_id": phone,
                    "severity": severity,
                    "date": cur_date_str,
                    "explanation": expl,
                    "evidence_ids": call_ids,
                    "metrics": {
                        "peak_count": cur_count,
                        "threshold": effective_threshold,
                        "ratio": ratio,
                        "median": med,
                        "mad": mad
                    }
                })

    # -------------------------------------------------------------
    # 2. VERY FREQUENT PAIR (Outliers above Q3 + 1.5 * IQR)
    # -------------------------------------------------------------
    iqr_mult = float(freq_cfg.get("iqr_multiplier", 1.5))

    # Normalized undirected pairs
    pair_counts: Dict[Tuple[str, str], int] = {}
    pair_calls_map: Dict[Tuple[str, str], List[str]] = {}
    pair_last_date: Dict[Tuple[str, str], str] = {}

    for _, row in df.iterrows():
        p1, p2 = sorted([row["caller"], row["receiver"]])
        pair_key = (p1, p2)
        pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
        pair_calls_map.setdefault(pair_key, []).append(row["id"])
        pair_last_date[pair_key] = max(pair_last_date.get(pair_key, ""), row["date_str"])

    if len(pair_counts) >= 4:
        counts_arr = np.array(list(pair_counts.values()))
        q1 = float(np.percentile(counts_arr, 25))
        q3 = float(np.percentile(counts_arr, 75))
        iqr = q3 - q1
        pair_threshold = max(q3 + (iqr_mult * iqr), 5.0)

        for pair_key, count in pair_counts.items():
            if count > pair_threshold:
                severity = "high" if count >= (q3 + 3.0 * iqr) else "medium"
                p1, p2 = pair_key
                expl = (
                    f"Anomalous high-frequency call pair between {p1} and {p2} with {count} calls. "
                    f"Case distribution Q1: {q1:.1f}, Q3: {q3:.1f}, IQR: {iqr:.1f}, outlier threshold: {pair_threshold:.1f}."
                )
                alerts.append({
                    "pattern_type": "very_frequent_pair",
                    "entity_id": f"{p1} <-> {p2}",
                    "severity": severity,
                    "date": pair_last_date[pair_key],
                    "explanation": expl,
                    "evidence_ids": pair_calls_map[pair_key][:10],
                    "metrics": {
                        "pair_calls": count,
                        "threshold": pair_threshold,
                        "ratio": round(count / pair_threshold, 2)
                    }
                })

    # -------------------------------------------------------------
    # 3. SUDDEN NEW CONNECTION (First call within X days of appearance + surge)
    # -------------------------------------------------------------
    new_win_days = int(new_conn_cfg.get("window_days", 7))
    min_early = int(new_conn_cfg.get("min_early_calls", 5))

    # Determine first appearance date for each phone
    phone_first_seen: Dict[str, datetime] = {}
    for _, row in df.iterrows():
        for ph in [row["caller"], row["receiver"]]:
            if ph not in phone_first_seen or row["datetime"] < phone_first_seen[ph]:
                phone_first_seen[ph] = row["datetime"]

    for pair_key, c_ids in pair_calls_map.items():
        p1, p2 = pair_key
        pair_df = df[((df["caller"] == p1) & (df["receiver"] == p2)) | ((df["caller"] == p2) & (df["receiver"] == p1))].sort_values("datetime")
        if pair_df.empty:
            continue

        first_call_dt = pair_df.iloc[0]["datetime"]
        first_call_str = pair_df.iloc[0]["date_str"]

        # Check if first call occurred within new_win_days of either party's initial appearance
        diff_p1 = abs((first_call_dt - phone_first_seen[p1]).days)
        diff_p2 = abs((first_call_dt - phone_first_seen[p2]).days)

        if diff_p1 <= new_win_days or diff_p2 <= new_win_days:
            # Calls in first 3 days of connection
            surge_end = first_call_dt + timedelta(days=3)
            surge_df = pair_df[pair_df["datetime"] <= surge_end]
            early_count = len(surge_df)

            if early_count >= min_early:
                expl = (
                    f"Sudden new connection formed between {p1} and {p2} on {first_call_str} "
                    f"with rapid initial surge of {early_count} calls within first 3 days (threshold: {min_early})."
                )
                alerts.append({
                    "pattern_type": "sudden_new_connection",
                    "entity_id": f"{p1} <-> {p2}",
                    "severity": "medium",
                    "date": first_call_str,
                    "explanation": expl,
                    "evidence_ids": surge_df["id"].tolist()[:10],
                    "metrics": {
                        "early_calls": early_count,
                        "threshold": min_early,
                        "ratio": round(early_count / min_early, 2)
                    }
                })

    # -------------------------------------------------------------
    # 4. SHARED DEVICE (IMEI used by >= 2 distinct phones)
    # -------------------------------------------------------------
    imei_df = df[df["imei"].str.len() >= 8]
    if not imei_df.empty:
        for imei_val, grp in imei_df.groupby("imei"):
            distinct_phones = sorted(list(set(grp["caller"].unique()).union(set(grp["receiver"].unique()))))
            if len(distinct_phones) >= 2:
                latest_d = grp["date_str"].max()
                expl = (
                    f"Device IMEI {imei_val} was utilized by {len(distinct_phones)} distinct mobile numbers "
                    f"({', '.join(distinct_phones[:4])}) indicating potential shared hardware or burner SIM rotation."
                )
                alerts.append({
                    "pattern_type": "shared_device",
                    "entity_id": imei_val,
                    "severity": "high",
                    "date": latest_d,
                    "explanation": expl,
                    "evidence_ids": grp["id"].tolist()[:10],
                    "metrics": {
                        "distinct_phones_count": len(distinct_phones),
                        "phones": distinct_phones
                    }
                })

    # -------------------------------------------------------------
    # 5. BRIDGE (Betweenness centrality & Louvain communities)
    # -------------------------------------------------------------
    min_betweenness = float(bridge_cfg.get("min_betweenness_ratio", 0.1))

    # Build NetworkX undirected call graph
    G = nx.Graph()
    for (p1, p2), cnt in pair_counts.items():
        G.add_edge(p1, p2, weight=cnt)

    if G.number_of_nodes() >= 4:
        # Centrality
        if G.number_of_nodes() > 3000:
            betweenness = nx.betweenness_centrality(G, k=300, seed=42)
        else:
            betweenness = nx.betweenness_centrality(G, seed=42)

        # Louvain communities
        try:
            comms = louvain_communities(G, seed=42)
            node_comm_map: Dict[str, int] = {}
            for c_id, comm_nodes in enumerate(comms):
                for node in comm_nodes:
                    node_comm_map[node] = c_id

            max_bw = max(betweenness.values()) if betweenness else 1.0
            if max_bw > 0:
                for node, bw_val in betweenness.items():
                    norm_bw = bw_val / max_bw
                    if norm_bw >= min_betweenness:
                        # Count distinct neighbor communities
                        neighbors = list(G.neighbors(node))
                        neighbor_comms = set(node_comm_map[nbr] for nbr in neighbors if nbr in node_comm_map)
                        # Remove node's own community
                        node_c = node_comm_map.get(node)
                        foreign_comms = neighbor_comms - {node_c}

                        if len(foreign_comms) >= 1 and len(neighbor_comms) >= 2:
                            latest_d = df[(df["caller"] == node) | (df["receiver"] == node)]["date_str"].max()
                            expl = (
                                f"Node {node} functions as a highest-betweenness bridge (normalized betweenness: {norm_bw:.3f}) "
                                f"interconnecting {len(neighbor_comms)} distinct operational clusters in the network."
                            )
                            alerts.append({
                                "pattern_type": "bridge",
                                "entity_id": node,
                                "severity": "high",
                                "date": latest_d or fallback_date_str,
                                "explanation": expl,
                                "evidence_ids": [],
                                "metrics": {
                                    "betweenness": round(bw_val, 4),
                                    "normalized_betweenness": round(norm_bw, 3),
                                    "clusters_connected": len(neighbor_comms)
                                }
                            })
        except Exception:
            pass

    return alerts
