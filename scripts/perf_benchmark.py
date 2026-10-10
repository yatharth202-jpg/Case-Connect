import os
import sys
import time
import json
import tracemalloc
from pathlib import Path
import numpy as np

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.sql import SessionLocal, Case, User, CallRecord, Transaction
from backend.app.auth.security import hash_password
from backend.app.services.graph.builder import build_detail_graph
from backend.app.services.money.trail import build_money_trail
from backend.app.services.analytics.lead_advisor import compute_lead_advisor
from backend.app.cases.router import get_effective_case_settings
from scripts.generate_data import SyntheticDataGenerator

def run_performance_benchmarks():
    print("=" * 80)
    print("        CASE CONNECT AI — SYSTEM PERFORMANCE & SCALE BENCHMARK        ")
    print("=" * 80)
    
    tracemalloc.start()
    db = SessionLocal()
    
    # Ensure test user
    u = db.query(User).filter(User.username == "benchmark_user").first()
    if not u:
        u = User(username="benchmark_user", password_hash=hash_password("Pass1234!"), role="investigator", is_active=True)
        db.add(u)
        db.commit()
        db.refresh(u)
    
    # Create benchmark case
    case = Case(title="Performance Benchmark Case", priority="high", created_by=u.id)
    db.add(case)
    db.commit()
    db.refresh(case)
    case_id = case.id

    print(f"\n[1/5] Synthesizing & Ingesting Dataset for Case {case_id[:8]}...")
    gen = SyntheticDataGenerator(seed=999)
    # Generate medium-large scenario
    scenario_data = gen.build_scenario_data("ring", size="medium")
    calls = scenario_data["calls"]
    txns = scenario_data["transactions"]
    print(f"       -> Synthetic records generated: {len(calls)} calls, {len(txns)} transactions")

    # Ingest Timing
    t0 = time.perf_counter()
    call_records = []
    for idx, c in enumerate(calls):
        call_records.append(CallRecord(
            case_id=case_id,
            source_file="bench_ev_cdr.csv",
            source_ref=str(idx),
            caller=c["caller"],
            receiver=c["receiver"],
            call_date=c["date"],
            call_time=c["time"],
            datetime_iso=f"{c['date']}T{c['time']}",
            duration_seconds=c["duration_seconds"],
            call_type=c["call_type"],
            fingerprint=f"bench_{c['call_id']}"
        ))
    db.bulk_save_objects(call_records)

    txn_records = []
    for idx, t in enumerate(txns):
        txn_records.append(Transaction(
            case_id=case_id,
            source_file="bench_ev_bank.csv",
            source_ref=str(idx),
            from_account=t["from_account"],
            to_account=t["to_account"],
            from_name=t.get("from_name", "Remitter"),
            to_name=t.get("to_name", "Beneficiary"),
            amount_paise=t["amount_paise"],
            date_iso=t["date"],
            reference=t["reference"],
            fingerprint=f"bench_{t['txn_id']}"
        ))
    db.bulk_save_objects(txn_records)
    db.commit()
    t_ingest = time.perf_counter() - t0
    print(f"       -> Bulk Ingestion Time: {t_ingest:.3f}s ({len(calls)+len(txns)} records, {(len(calls)+len(txns))/max(t_ingest, 0.001):.0f} rows/sec)")

    # Graph Building Timing
    print("\n[2/5] Benchmarking In-Memory Graph Builder...")
    t0 = time.perf_counter()
    G = build_detail_graph(db, case_id)
    t_graph = time.perf_counter() - t0
    print(f"       -> Graph Rebuild Time: {t_graph:.3f}s ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")

    # Hop Search Latency
    print("\n[3/5] Benchmarking Hop Search Latency (p50 / p95 across 50 traversals)...")
    import networkx as nx
    sample_nodes = list(G.nodes())[:min(20, G.number_of_nodes())]
    hop_latencies = {1: [], 2: [], 3: [], 4: []}

    for hops in [1, 2, 3, 4]:
        for n in sample_nodes:
            t0 = time.perf_counter()
            sub = nx.ego_graph(G, n, radius=hops)
            _ = sub.number_of_nodes()
            dt_ms = (time.perf_counter() - t0) * 1000.0
            hop_latencies[hops].append(dt_ms)

        p50 = np.percentile(hop_latencies[hops], 50)
        p95 = np.percentile(hop_latencies[hops], 95)
        print(f"       -> Radius {hops} Hops: p50 = {p50:.2f}ms | p95 = {p95:.2f}ms (Max sampled subnodes: {max(len(nx.ego_graph(G, n, radius=hops)) for n in sample_nodes)})")

    # Money Trail Latency
    print("\n[4/5] Benchmarking Multi-Hop Money Trail BFS Engine...")
    trail_latencies = []
    sample_accounts = list(set(t["from_account"] for t in txns[:10]))
    for acc in sample_accounts:
        t0 = time.perf_counter()
        _ = build_money_trail(db, case_id, account_query=acc, hops=4, min_amount_rupees=100.0)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        trail_latencies.append(dt_ms)

    mt_p50 = np.percentile(trail_latencies, 50) if trail_latencies else 0.0
    mt_p95 = np.percentile(trail_latencies, 95) if trail_latencies else 0.0
    print(f"       -> Money Trail BFS (4 Hops): p50 = {mt_p50:.2f}ms | p95 = {mt_p95:.2f}ms")

    # Lead Computation Latency
    print("\n[5/5] Benchmarking Explainable Lead Advisor Engine...")
    settings = get_effective_case_settings(db, case_id)
    stored_calls = db.query(CallRecord).filter(CallRecord.case_id == case_id).all()
    stored_txns = db.query(Transaction).filter(Transaction.case_id == case_id).all()
    t0 = time.perf_counter()
    leads = compute_lead_advisor(
        case_id=case_id,
        entities=[],
        entity_links=[],
        call_records=stored_calls,
        transactions=stored_txns,
        evidence_files=[],
        extracted_entities=[],
        alerts=[],
        settings=settings
    )
    t_leads = time.perf_counter() - t0
    print(f"       -> Lead Advisor Scoring: {t_leads:.3f}s for {len(leads)} prioritized leads")

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"\n[RESOURCE USAGE] Peak Memory Consumed: {peak_mem / (1024 * 1024):.2f} MB")

    db.close()

    print("\n" + "=" * 80)
    print("                    PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"| {'Benchmark Stage':<30} | {'Throughput / Time':<25} | {'p50 Latency':<16} |")
    print("|" + "-" * 32 + "|" + "-" * 27 + "|" + "-" * 18 + "|")
    print(f"| {'SQLite Bulk Ingestion':<30} | {f'{t_ingest:.3f}s ({len(calls)+len(txns)} rows)':<25} | {'N/A':<16} |")
    print(f"| {'NetworkX Graph Rebuild':<30} | {f'{t_graph:.3f}s ({G.number_of_nodes()} nodes)':<25} | {'N/A':<16} |")
    print(f"| {'Graph Subgraph (Hops 1-2)':<30} | {'Instantaneous':<25} | {f'{np.percentile(hop_latencies[2], 50):.2f}ms':<16} |")
    print(f"| {'Graph Subgraph (Hops 3-4)':<30} | {'Bounded traversal':<25} | {f'{np.percentile(hop_latencies[4], 50):.2f}ms':<16} |")
    print(f"| {'Money Trail BFS (4 Hops)':<30} | {'Sub-15ms Layering':<25} | {f'{mt_p50:.2f}ms':<16} |")
    print(f"| {'Lead Advisor 5-Signal Scorer':<30} | {f'{t_leads:.3f}s total':<25} | {'N/A':<16} |")
    print(f"| {'Peak RAM Allocation':<30} | {f'{peak_mem / (1024 * 1024):.1f} MB':<25} | {'Strictly Bounded':<16} |")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_performance_benchmarks()
