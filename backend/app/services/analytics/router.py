import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import networkx as nx
from networkx.algorithms.community import louvain_communities
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text

from backend.app.db.sql import (
    get_db, Case, Entity, EntityLink, CallRecord, Transaction,
    EvidenceFile, ExtractedEntity, Alert, LeadDecision, User, RejectedRow
)
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.cases.router import get_effective_case_settings
from backend.app.audit.service import record_audit_log
from backend.app.services.analytics.comm_patterns import detect_communication_patterns, parse_date_str
from backend.app.services.analytics.lead_advisor import compute_lead_advisor
from backend.app.services.analytics.provenance import get_provenance_details
from backend.app.services.money.patterns import detect_money_patterns
from backend.app.services.analytics.dynamic_analyzer import process_dynamic_file_analysis

router = APIRouter()

class LeadDecisionPayload(BaseModel):
    decision: str  # accept, reject, need_more_data
    notes: Optional[str] = None

class DynamicTextPayload(BaseModel):
    title: Optional[str] = "Incident Narrative"
    text: str
    case_id: Optional[str] = None

# -------------------------------------------------------------------------
# 0. DIRECT RUNTIME FILE & TEXT ANALYSIS (ZERO HARDCODED MOCKS)
# -------------------------------------------------------------------------
@router.post("/analytics/analyse-file")
def dynamic_file_analysis_endpoint(
    file: UploadFile = File(...),
    case_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Direct endpoint for runtime dynamic evidence file analysis.
    Supports incremental multi-evidence appending by passing an existing case_id.
    Runs synchronously in FastAPI worker threadpool.
    """
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    result = process_dynamic_file_analysis(
        file_bytes=content,
        filename=file.filename or "uploaded_evidence.txt",
        db=db,
        user_id=current_user.id,
        case_id=case_id
    )
    return result

@router.post("/analytics/analyse-text")
def dynamic_text_analysis_endpoint(
    payload: DynamicTextPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Direct endpoint for runtime direct text/FIR statement analysis.
    Supports incremental multi-evidence appending by passing an existing case_id.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text payload is empty.")

    result = process_dynamic_file_analysis(
        file_bytes=payload.text.encode("utf-8"),
        filename=f"{payload.title or 'FIR_Narrative'}.txt",
        db=db,
        user_id=current_user.id,
        case_id=payload.case_id
    )
    return result


# -------------------------------------------------------------------------
# 1. ANALYTICS OVERVIEW
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/overview")
def get_analytics_overview(
    case_id: str,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Overview summary metrics for the case dashboard:
    Files, ingested/rejected rows, entity counts by type, total connections,
    money throughput volume, and operational date span.
    """
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()
    rows_ingested = (
        db.query(CallRecord).filter(CallRecord.case_id == case.id).count()
        + db.query(Transaction).filter(Transaction.case_id == case.id).count()
    )
    rows_rejected = db.query(RejectedRow).filter(RejectedRow.case_id == case.id).count()

    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    entity_counts: Dict[str, int] = {}
    for ent in entities:
        lbl = ent.label or "Other"
        entity_counts[lbl] = entity_counts.get(lbl, 0) + 1

    total_edges = db.query(EntityLink).filter(EntityLink.case_id == case.id).count()

    # Transactions with optional date filter
    q_tx = db.query(Transaction).filter(Transaction.case_id == case.id)
    if from_date:
        q_tx = q_tx.filter(Transaction.date_iso >= from_date)
    if to_date:
        q_tx = q_tx.filter(Transaction.date_iso <= to_date)
    txns = q_tx.all()

    total_volume_paise = sum(t.amount_paise for t in txns)
    total_volume_inr = round(total_volume_paise / 100.0, 2)

    # Calls with optional date filter
    q_calls = db.query(CallRecord).filter(CallRecord.case_id == case.id)
    if from_date:
        q_calls = q_calls.filter(CallRecord.datetime_iso >= from_date)
    if to_date:
        q_calls = q_calls.filter(CallRecord.datetime_iso <= to_date)
    calls = q_calls.all()

    # Calculate date span across calls and transactions
    all_dates: List[str] = []
    for t in txns:
        if t.date_iso:
            all_dates.append(str(t.date_iso)[:10])
    for c in calls:
        d = c.datetime_iso or c.call_date
        if d:
            all_dates.append(str(d)[:10])

    earliest_date = min(all_dates) if all_dates else None
    latest_date = max(all_dates) if all_dates else None
    days_span = 0
    if earliest_date and latest_date:
        try:
            d1 = datetime.strptime(earliest_date[:10], "%Y-%m-%d")
            d2 = datetime.strptime(latest_date[:10], "%Y-%m-%d")
            days_span = max((d2 - d1).days + 1, 1)
        except Exception:
            pass

    return {
        "files_count": len(evidence_files),
        "rows_ingested": rows_ingested,
        "rows_rejected": rows_rejected,
        "entity_counts": entity_counts,
        "total_entities": len(entities),
        "total_edges": total_edges,
        "total_calls": len(calls),
        "total_txns": len(txns),
        "total_money_volume_paise": total_volume_paise,
        "total_money_volume_rs": total_volume_inr,
        "date_span": {
            "earliest": earliest_date,
            "latest": latest_date,
            "days": days_span
        }
    }


# -------------------------------------------------------------------------
# 2. CALLS PER DAY (WITH SPIKE MARKERS)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/calls-per-day")
def get_calls_per_day(
    case_id: str,
    phone: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Daily aggregated call volume series with detected sudden-spike markers.
    """
    q_calls = db.query(CallRecord).filter(CallRecord.case_id == case.id)
    if phone:
        q_calls = q_calls.filter(or_(CallRecord.caller == phone, CallRecord.receiver == phone))
    all_calls = q_calls.all()

    if not all_calls:
        return {
            "daily_calls": [],
            "total_calls": 0,
            "peak_day": None,
            "spike_days_count": 0
        }

    # Detect communication anomalies
    settings = get_effective_case_settings(db, case.id)
    alerts = detect_communication_patterns(all_calls, settings)

    spikes_map: Dict[str, Dict[str, Any]] = {}
    for a in alerts:
        if a.get("pattern_type") == "sudden_spike":
            ent = a.get("entity_id", "")
            if not phone or ent == phone:
                spikes_map[a.get("date", "")] = a

    daily_map: Dict[str, int] = {}
    for c in all_calls:
        d_val = str(c.datetime_iso or c.call_date or "unknown")[:10]
        if from_date and d_val < from_date:
            continue
        if to_date and d_val > to_date:
            continue
        daily_map[d_val] = daily_map.get(d_val, 0) + 1

    daily_calls = []
    spike_days_count = 0
    max_count = -1
    peak_day = None

    for d in sorted(daily_map.keys()):
        cnt = daily_map[d]
        if cnt > max_count:
            max_count = cnt
            peak_day = {"date": d, "count": cnt}

        spike_info = spikes_map.get(d)
        is_spike = spike_info is not None
        if is_spike:
            spike_days_count += 1

        daily_calls.append({
            "date": d,
            "count": cnt,
            "is_spike": is_spike,
            "threshold": spike_info.get("metrics", {}).get("threshold") if spike_info else None,
            "spike_info": {
                "severity": spike_info.get("severity"),
                "ratio": spike_info.get("metrics", {}).get("ratio"),
                "explanation": spike_info.get("explanation")
            } if spike_info else None
        })

    return {
        "daily_calls": daily_calls,
        "total_calls": sum(daily_map.values()),
        "peak_day": peak_day,
        "spike_days_count": spike_days_count
    }


# -------------------------------------------------------------------------
# 2B. TRANSACTIONS PER DAY (DAILY FINANCIAL VOLUME & THROUGHPUT)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/txns-per-day")
def get_txns_per_day(
    case_id: str,
    account: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Daily aggregated transaction volume (paise and INR) and transaction count,
    with peak volume detection and optional account filtering.
    """
    q_tx = db.query(Transaction).filter(Transaction.case_id == case.id)
    if account:
        q_tx = q_tx.filter(or_(Transaction.from_account == account, Transaction.to_account == account))
    if from_date:
        q_tx = q_tx.filter(Transaction.date_iso >= from_date)
    if to_date:
        q_tx = q_tx.filter(Transaction.date_iso <= to_date)
    all_txns = q_tx.all()

    if not all_txns:
        return {
            "daily_txns": [],
            "total_transactions": 0,
            "total_volume_paise": 0,
            "total_volume_inr": 0.0,
            "peak_day": None
        }

    daily_map: Dict[str, Dict[str, Any]] = {}
    for t in all_txns:
        d = str(t.date_iso or "unknown")[:10]
        if d not in daily_map:
            daily_map[d] = {
                "date": d,
                "count": 0,
                "volume_paise": 0,
                "volume_inr": 0.0,
                "max_single_txn_paise": 0
            }
        amt = t.amount_paise or 0
        daily_map[d]["count"] += 1
        daily_map[d]["volume_paise"] += amt
        if amt > daily_map[d]["max_single_txn_paise"]:
            daily_map[d]["max_single_txn_paise"] = amt

    daily_txns = []
    max_vol = -1
    peak_day = None

    for d in sorted(daily_map.keys()):
        item = daily_map[d]
        item["volume_inr"] = round(item["volume_paise"] / 100.0, 2)
        daily_txns.append(item)
        if item["volume_paise"] > max_vol:
            max_vol = item["volume_paise"]
            peak_day = {
                "date": d,
                "volume_inr": item["volume_inr"],
                "count": item["count"]
            }

    tot_paise = sum(item["volume_paise"] for item in daily_txns)

    return {
        "daily_txns": daily_txns,
        "total_transactions": len(all_txns),
        "total_volume_paise": tot_paise,
        "total_volume_inr": round(tot_paise / 100.0, 2),
        "peak_day": peak_day
    }


# -------------------------------------------------------------------------
# 3. TOP ENTITIES (DEGREE / CALLS / THROUGHPUT)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/top-entities")
def get_top_entities(
    case_id: str,
    metric: str = Query("degree", pattern="^(degree|calls|throughput)$"),
    limit: int = Query(10, ge=1, le=50),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ranks entities by dynamic operational metrics:
      - degree: graph link connectivity
      - calls: total CDR call activity
      - throughput: financial inflow/outflow volume
    """
    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    ent_map = {e.canonical_id: e for e in entities}
    display_names = {e.canonical_id: (e.display_name or e.canonical_id) for e in entities}
    labels = {e.canonical_id: e.label for e in entities}

    res_entities: List[Dict[str, Any]] = []

    if metric == "degree":
        links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
        degree_map: Dict[str, int] = {}
        for l in links:
            degree_map[l.source_entity_id] = degree_map.get(l.source_entity_id, 0) + 1
            degree_map[l.target_entity_id] = degree_map.get(l.target_entity_id, 0) + 1

        sorted_items = sorted(degree_map.items(), key=lambda x: x[1], reverse=True)[:limit]
        for node_id, deg in sorted_items:
            res_entities.append({
                "id": node_id,
                "display_name": display_names.get(node_id, node_id),
                "label": labels.get(node_id, "Entity"),
                "value": deg,
                "metric": "degree",
                "details": {"degree": deg}
            })

    elif metric == "calls":
        calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
        call_counts: Dict[str, int] = {}
        for c in calls:
            call_counts[c.caller] = call_counts.get(c.caller, 0) + 1
            call_counts[c.receiver] = call_counts.get(c.receiver, 0) + 1

        sorted_items = sorted(call_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        for node_id, cnt in sorted_items:
            res_entities.append({
                "id": node_id,
                "display_name": display_names.get(node_id, node_id),
                "label": labels.get(node_id, "Phone"),
                "value": cnt,
                "metric": "calls",
                "details": {"total_calls": cnt}
            })

    elif metric == "throughput":
        txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()
        inflows: Dict[str, int] = {}
        outflows: Dict[str, int] = {}
        for t in txns:
            outflows[t.from_account] = outflows.get(t.from_account, 0) + t.amount_paise
            inflows[t.to_account] = inflows.get(t.to_account, 0) + t.amount_paise

        all_accs = set(inflows.keys()).union(set(outflows.keys()))
        tp_map: Dict[str, int] = {}
        for acc in all_accs:
            tp = min(inflows.get(acc, 0), outflows.get(acc, 0))
            if tp == 0:
                tp = inflows.get(acc, 0) + outflows.get(acc, 0)
            tp_map[acc] = tp

        sorted_items = sorted(tp_map.items(), key=lambda x: x[1], reverse=True)[:limit]
        for node_id, val_paise in sorted_items:
            res_entities.append({
                "id": node_id,
                "display_name": display_names.get(node_id, node_id),
                "label": labels.get(node_id, "BankAccount"),
                "value": round(val_paise / 100.0, 2),
                "metric": "throughput",
                "details": {
                    "throughput_rs": round(val_paise / 100.0, 2),
                    "inflow_rs": round(inflows.get(node_id, 0) / 100.0, 2),
                    "outflow_rs": round(outflows.get(node_id, 0) / 100.0, 2)
                }
            })

    return {
        "metric": metric,
        "entities": res_entities
    }


# -------------------------------------------------------------------------
# 4. COMMUNITIES (LOUVAIN PARTITIONING)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/communities")
def get_communities_analytics(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Partitions the network into modular communities using deterministic Louvain clustering (seed=42).
    """
    links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    ent_map = {e.canonical_id: e for e in entities}

    G = nx.Graph()
    for e in entities:
        G.add_node(e.canonical_id, label=e.label, display_name=e.display_name or e.canonical_id)
    for l in links:
        G.add_edge(l.source_entity_id, l.target_entity_id)

    if G.number_of_nodes() < 2:
        return {
            "communities_count": 1 if G.number_of_nodes() == 1 else 0,
            "nodes": [
                {
                    "id": n,
                    "display_name": ent_map.get(n, None).display_name if ent_map.get(n) else n,
                    "label": ent_map.get(n, None).label if ent_map.get(n) else "Entity",
                    "community_id": 0
                }
                for n in G.nodes
            ],
            "community_sizes": {"0": G.number_of_nodes()} if G.number_of_nodes() == 1 else {}
        }

    try:
        comms = louvain_communities(G, seed=42)
    except Exception:
        comms = [set(G.nodes)]

    nodes_list = []
    sizes: Dict[str, int] = {}
    for c_id, comm_set in enumerate(comms):
        sizes[str(c_id)] = len(comm_set)
        for node in comm_set:
            ent = ent_map.get(node)
            nodes_list.append({
                "id": node,
                "display_name": ent.display_name if ent and ent.display_name else node,
                "label": ent.label if ent else "Entity",
                "community_id": c_id
            })

    return {
        "communities_count": len(comms),
        "nodes": nodes_list,
        "community_sizes": sizes
    }


# -------------------------------------------------------------------------
# 5. DEGREE DISTRIBUTION (HISTOGRAM)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/degree-distribution")
def get_degree_distribution(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Histogram of node degree connectivity across the case entity graph.
    """
    links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    entities = db.query(Entity).filter(Entity.case_id == case.id).all()

    deg_map: Dict[str, int] = {e.canonical_id: 0 for e in entities}
    for l in links:
        deg_map[l.source_entity_id] = deg_map.get(l.source_entity_id, 0) + 1
        deg_map[l.target_entity_id] = deg_map.get(l.target_entity_id, 0) + 1

    degrees = list(deg_map.values())
    if not degrees:
        return {
            "buckets": [],
            "max_degree": 0,
            "avg_degree": 0.0,
            "total_nodes": 0
        }

    max_deg = max(degrees)
    avg_deg = round(float(np.mean(degrees)), 2)

    # Standard distribution buckets
    bucket_defs = [
        (1, 1, "1 link"),
        (2, 3, "2 - 3 links"),
        (4, 5, "4 - 5 links"),
        (6, 10, "6 - 10 links"),
        (11, 20, "11 - 20 links"),
        (21, 999999, "21+ links")
    ]

    buckets = []
    for low, high, lbl in bucket_defs:
        count = sum(1 for d in degrees if low <= d <= high)
        if count > 0 or low <= max_deg:
            buckets.append({
                "degree_range": lbl,
                "min_degree": low,
                "max_degree": high if high < 999999 else max_deg,
                "count": count
            })

    return {
        "buckets": buckets,
        "max_degree": max_deg,
        "avg_degree": avg_deg,
        "total_nodes": len(degrees)
    }


# -------------------------------------------------------------------------
# 6. CALL HEATMAP (WEEKDAY X HOUR)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/analytics/call-heatmap")
def get_call_heatmap(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    7x24 Matrix of call activity distribution by day of week and hour of day.
    """
    calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
    matrix = [[0 for _ in range(24)] for _ in range(7)]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    valid_calls_count = 0
    for c in calls:
        dt = parse_date_str(c.datetime_iso or c.call_date)
        if dt:
            w = dt.weekday()  # 0 to 6
            h = dt.hour       # 0 to 23
            if 0 <= w < 7 and 0 <= h < 24:
                matrix[w][h] += 1
                valid_calls_count += 1

    flat_matrix = []
    peak_count = -1
    peak_cell = None

    for d_idx, d_name in enumerate(day_names):
        for h in range(24):
            cnt = matrix[d_idx][h]
            if cnt > peak_count:
                peak_count = cnt
                peak_cell = {"day_name": d_name, "day": d_idx, "hour": h, "count": cnt}
            flat_matrix.append({
                "day": d_idx,
                "day_name": d_name,
                "hour": h,
                "count": cnt
            })

    return {
        "days": day_names,
        "matrix": flat_matrix,
        "peak_cell": peak_cell,
        "total_calls": valid_calls_count
    }


# -------------------------------------------------------------------------
# 7. ANOMALY ALERTS (COMMUNICATION + FINANCIAL FLOW PATTERNS)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/alerts")
def get_case_alerts(
    case_id: str,
    severity: Optional[str] = Query(None),
    pattern_type: Optional[str] = Query(None),
    recompute: bool = Query(False),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns persisted anomaly alerts across communication detail records and money flows.
    Optionally recomputes using active case configuration settings.
    """
    existing_count = db.query(Alert).filter(Alert.case_id == case.id).count()

    if recompute or existing_count == 0:
        settings = get_effective_case_settings(db, case.id)
        calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
        txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()

        comm_alerts = detect_communication_patterns(calls, settings)
        money_alerts = detect_money_patterns(txns, settings)

        # Clear existing alerts if recomputing
        if recompute and existing_count > 0:
            db.query(Alert).filter(Alert.case_id == case.id).delete()
            db.commit()

        # Persist detected alerts
        for a in (comm_alerts + money_alerts):
            al_obj = Alert(
                case_id=case.id,
                entity_id=str(a.get("entity_id", "Unknown")),
                pattern_type=str(a.get("pattern_type", "anomaly")),
                severity=str(a.get("severity", "medium")),
                alert_date=str(a.get("date") or datetime.utcnow().strftime("%Y-%m-%d")),
                explanation=str(a.get("explanation", "")),
                evidence_ids_json=json.dumps(a.get("evidence_ids", []))
            )
            db.add(al_obj)
        db.commit()

    # Query filtered alerts
    q = db.query(Alert).filter(Alert.case_id == case.id)
    if severity:
        q = q.filter(Alert.severity == severity.lower())
    if pattern_type:
        q = q.filter(Alert.pattern_type == pattern_type)

    alert_rows = q.order_by(Alert.alert_date.desc(), Alert.created_at.desc()).all()

    alerts_list = []
    pattern_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {}

    for row in alert_rows:
        pattern_counts[row.pattern_type] = pattern_counts.get(row.pattern_type, 0) + 1
        severity_counts[row.severity] = severity_counts.get(row.severity, 0) + 1

        try:
            ev_ids = json.loads(row.evidence_ids_json)
        except Exception:
            ev_ids = []

        alerts_list.append({
            "id": row.id,
            "entity_id": row.entity_id,
            "pattern_type": row.pattern_type,
            "severity": row.severity,
            "alert_date": row.alert_date,
            "explanation": row.explanation,
            "evidence_ids": ev_ids,
            "created_at": row.created_at.isoformat() if row.created_at else None
        })

    return {
        "alerts": alerts_list,
        "total_count": len(alerts_list),
        "counts_by_pattern": pattern_counts,
        "counts_by_severity": severity_counts
    }


# -------------------------------------------------------------------------
# 8. LEAD ADVISOR (HERO FEATURE #3)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/leads")
def get_leads_advisor(
    case_id: str,
    level: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes explainable, data-driven investigative leads via Lead Advisor engine.
    Normalized over available signals with zero faked zeros and zero ML bias.
    """
    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    entity_links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    call_records = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
    transactions = db.query(Transaction).filter(Transaction.case_id == case.id).all()
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()
    extracted_entities = db.query(ExtractedEntity).filter(ExtractedEntity.case_id == case.id).all()
    settings = get_effective_case_settings(db, case.id)

    # Compute alerts to feed into signals
    comm_alerts = detect_communication_patterns(call_records, settings)
    money_alerts = detect_money_patterns(transactions, settings)
    all_alerts = comm_alerts + money_alerts

    leads = compute_lead_advisor(
        case_id=case.id,
        entities=entities,
        entity_links=entity_links,
        call_records=call_records,
        transactions=transactions,
        evidence_files=evidence_files,
        extracted_entities=extracted_entities,
        alerts=all_alerts,
        settings=settings
    )

    # Enrich with recorded officer decisions
    decisions = db.query(LeadDecision).filter(LeadDecision.case_id == case.id).all()
    dec_map = {d.lead_id: d for d in decisions}

    for lead in leads:
        d = dec_map.get(lead["id"])
        if d:
            lead["decision"] = d.decision
            lead["decision_notes"] = d.notes
            lead["decided_by"] = d.officer_id
            lead["decided_at"] = d.decided_at.isoformat() if d.decided_at else None
        else:
            lead["decision"] = None
            lead["decision_notes"] = None
            lead["decided_by"] = None
            lead["decided_at"] = None

    high_cnt = sum(1 for l in leads if l["level"] == "HIGH")
    med_cnt = sum(1 for l in leads if l["level"] == "MEDIUM")
    low_cnt = sum(1 for l in leads if l["level"] == "LOW")

    if level:
        leads = [l for l in leads if l["level"].upper() == level.upper()]

    capped_leads = leads[:limit]

    return {
        "leads": capped_leads,
        "total_count": len(leads),
        "high_count": high_cnt,
        "medium_count": med_cnt,
        "low_count": low_cnt,
        "disclaimer": "Lead for review — not a finding of wrongdoing."
    }


# -------------------------------------------------------------------------
# 9. LEAD DECISION RECORDING
# -------------------------------------------------------------------------
@router.post("/cases/{case_id}/leads/{lead_id}/decision")
def record_lead_decision(
    case_id: str,
    lead_id: str,
    payload: LeadDecisionPayload,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Records investigator decision (accept, reject, need_more_data) with cryptographic audit trail.
    Viewers are strictly prohibited.
    """
    if current_user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers do not possess authorization to record investigative lead decisions."
        )

    valid_decisions = {"accept", "reject", "need_more_data"}
    if payload.decision.lower() not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{payload.decision}'. Permitted decisions: {sorted(list(valid_decisions))}"
        )

    existing = db.query(LeadDecision).filter(
        LeadDecision.case_id == case.id,
        LeadDecision.lead_id == lead_id
    ).first()

    now = datetime.utcnow()
    decision_val = payload.decision.lower()
    notes_val = payload.notes or ""

    if existing:
        existing.decision = decision_val
        existing.notes = notes_val
        existing.officer_id = current_user.id
        existing.decided_at = now
        db_obj = existing
    else:
        db_obj = LeadDecision(
            case_id=case.id,
            lead_id=lead_id,
            decision=decision_val,
            notes=notes_val,
            officer_id=current_user.id,
            decided_at=now
        )
        db.add(db_obj)

    # Append to SHA-256 chained audit log
    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="LEAD_DECISION_RECORDED",
        case_id=case.id,
        object_type="lead",
        object_id=lead_id,
        details={
            "decision": decision_val,
            "notes": notes_val,
            "officer": current_user.username,
            "lead_id": lead_id
        }
    )

    db.commit()
    db.refresh(db_obj)

    return {
        "status": "success",
        "lead_id": lead_id,
        "decision": db_obj.decision,
        "notes": db_obj.notes,
        "officer_id": current_user.id,
        "officer_username": current_user.username,
        "decided_at": db_obj.decided_at.isoformat()
    }


# -------------------------------------------------------------------------
# 10. ENTITY EXPLANATION CARD ("WHY IS THIS ENTITY IMPORTANT?")
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/entities/{entity_id}/why")
def get_entity_why_card(
    case_id: str,
    entity_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a deterministic explanation card detailing why a node or entity is critical to the case.
    Zero ML models or LLMs used — 100% data-driven and reproducible.
    """
    ent = db.query(Entity).filter(
        Entity.case_id == case.id,
        or_(Entity.id == entity_id, Entity.canonical_id == entity_id)
    ).first()

    canonical = ent.canonical_id if ent else entity_id
    disp_name = ent.display_name if ent and ent.display_name else canonical
    label = ent.label if ent else "Entity"

    # Fetch leads
    leads_res = get_leads_advisor(case_id=case.id, level=None, limit=200, case=case, current_user=current_user, db=db)
    lead_match = next((l for l in leads_res.get("leads", []) if l["entity_id"] == canonical or l["id"] == f"lead_{canonical}"), None)

    # Fetch links degree
    degree = db.query(EntityLink).filter(
        EntityLink.case_id == case.id,
        or_(EntityLink.source_entity_id == canonical, EntityLink.target_entity_id == canonical)
    ).count()

    # Calls summary
    calls_count = db.query(CallRecord).filter(
        CallRecord.case_id == case.id,
        or_(CallRecord.caller == canonical, CallRecord.receiver == canonical)
    ).count()

    # Txns summary
    inflow_sum = sum(
        t.amount_paise for t in db.query(Transaction).filter(
            Transaction.case_id == case.id,
            Transaction.to_account == canonical
        ).all()
    )
    outflow_sum = sum(
        t.amount_paise for t in db.query(Transaction).filter(
            Transaction.case_id == case.id,
            Transaction.from_account == canonical
        ).all()
    )

    alerts = db.query(Alert).filter(
        Alert.case_id == case.id,
        Alert.entity_id.like(f"%{canonical}%")
    ).all()

    # Construct plain-English fact narrative
    facts = []
    if lead_match:
        facts.append(f"Priority score {lead_match['priority']} ({lead_match['level']} priority level, confidence: {lead_match['confidence']}).")
        top_sig = max([s for s in lead_match.get("signals", []) if s.get("is_available")], key=lambda s: s.get("score", 0), default=None)
        if top_sig:
            facts.append(f"Primary driving signal: {top_sig.get('label')} ({top_sig.get('explanation')}).")
        if lead_match.get("matched_pattern"):
            facts.append(f"Correlates with operational archetype '{lead_match['matched_pattern']['name']}'.")

    if degree > 0:
        facts.append(f"Directly connected to {degree} relational link(s) across the investigated network.")
    if calls_count > 0:
        facts.append(f"Recorded in {calls_count} telecommunication interactions.")
    if (inflow_sum + outflow_sum) > 0:
        facts.append(f"Processed Rs. {((inflow_sum + outflow_sum) / 100):,.2f} in financial volume (inflow: Rs. {(inflow_sum / 100):,.2f}, outflow: Rs. {(outflow_sum / 100):,.2f}).")
    if alerts:
        facts.append(f"Flagged by {len(alerts)} automated pattern alert(s) (including {alerts[0].pattern_type}).")

    narrative = " ".join(facts) if facts else f"Entity '{disp_name}' appears in case repository without active alert escalations."

    return {
        "entity_id": canonical,
        "display_name": disp_name,
        "label": label,
        "priority": lead_match["priority"] if lead_match else 0.0,
        "level": lead_match["level"] if lead_match else "LOW",
        "confidence": lead_match["confidence"] if lead_match else "Low",
        "degree": degree,
        "calls_count": calls_count,
        "financial_volume_rs": round((inflow_sum + outflow_sum) / 100.0, 2),
        "alerts_count": len(alerts),
        "narrative": narrative,
        "signals": lead_match.get("signals", []) if lead_match else [],
        "matched_pattern": lead_match.get("matched_pattern") if lead_match else None,
        "missing_data": lead_match.get("missing_data", []) if lead_match else [],
        "suggested_next_steps": lead_match.get("suggested_next_steps", []) if lead_match else [],
        "disclaimer": "Analytical lead summary for review — not a finding of wrongdoing."
    }


# -------------------------------------------------------------------------
# 11. FORENSIC PROVENANCE ("WHY THIS LINK?" / "WHY THIS NODE?")
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/provenance")
def get_provenance(
    case_id: str,
    node_id: Optional[str] = Query(None),
    edge_id: Optional[str] = Query(None),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches forensic evidentiary provenance substantiating a specific graph node or relationship edge.
    Returns source evidence file, line/page reference, hash, method, confidence, and underlying raw records.
    """
    if not node_id and not edge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must supply either 'node_id' or 'edge_id' parameter to inspect evidentiary provenance."
        )

    res = get_provenance_details(db, case.id, node_id=node_id, edge_id=edge_id)
    return res


# -------------------------------------------------------------------------
# 12. UNIFIED INVESTIGATIVE TIMELINE (CHRONOLOGICAL EVENT STREAM)
# -------------------------------------------------------------------------
@router.get("/cases/{case_id}/timeline")
def get_case_timeline(
    case_id: str,
    entity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None, alias="type"),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unified chronological sequence aggregating:
    - Formal document registrations / FIR dates
    - Aggregated same-day same-pair financial transfer waves
    - Daily call-volume peaks & sudden communication spikes
    - SIM activations / KYC registrations
    - System pattern alerts (smurfing, mule fan-in/out, rapid pass-through, bridges)
    - Investigator decisions
    Provides 'First Alert vs First Document' pre-FIR lead analysis.
    """
    from typing import Tuple
    events: List[Dict[str, Any]] = []

    # 1. Documents & Evidence Files
    evidence_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()
    for ef in evidence_files:
        # Check if an explicit date was extracted from document text
        doc_date_ent = db.query(ExtractedEntity).filter(
            ExtractedEntity.evidence_id == ef.id,
            ExtractedEntity.entity_type.in_(["date", "fir_date", "incident_date"])
        ).first()
        d_val = doc_date_ent.normalized_value if doc_date_ent else (ef.created_at.strftime("%Y-%m-%d") if ef.created_at else datetime.utcnow().strftime("%Y-%m-%d"))
        d_str = str(d_val)[:10]

        # Extract names found in this document
        names_found = [
            ee.normalized_value for ee in db.query(ExtractedEntity).filter(
                ExtractedEntity.evidence_id == ef.id,
                ExtractedEntity.entity_type == "person"
            ).all()
        ]

        events.append({
            "id": f"doc-{ef.id}",
            "type": "document",
            "timestamp": d_str,
            "title": f"Document: {ef.original_name}",
            "summary": f"Format: {ef.detected_type or 'document'} | SHA-256: {ef.sha256[:12]}...",
            "severity": "info",
            "entities": names_found,
            "source_file": ef.original_name,
            "details": {
                "file_type": ef.detected_type,
                "file_size": ef.file_size,
                "sha256": ef.sha256
            }
        })

    # 2. Daily Same-Day Same-Pair Financial Transfer Waves
    txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()
    wave_map: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for t in txns:
        d_str = str(t.date_iso or "")[:10]
        if not d_str:
            continue
        key = (d_str, t.from_account, t.to_account)
        if key not in wave_map:
            wave_map[key] = {
                "date": d_str,
                "from_account": t.from_account,
                "to_account": t.to_account,
                "count": 0,
                "total_paise": 0,
                "source_file": t.source_file
            }
        wave_map[key]["count"] += 1
        wave_map[key]["total_paise"] += (t.amount_paise or 0)

    for (d_str, fa, ta), w in wave_map.items():
        amt_rs = round(w["total_paise"] / 100.0, 2)
        events.append({
            "id": f"wave-{d_str}-{fa[:6]}-{ta[:6]}",
            "type": "transaction_wave",
            "timestamp": d_str,
            "title": f"Transfer Wave: {fa} -> {ta}",
            "summary": f"{w['count']} transfer(s) totaling ₹{amt_rs:,.2f}",
            "severity": "medium" if amt_rs >= 100000 else "info",
            "entities": [fa, ta],
            "source_file": w["source_file"],
            "details": {
                "from_account": fa,
                "to_account": ta,
                "tx_count": w["count"],
                "total_rs": amt_rs,
                "total_paise": w["total_paise"]
            }
        })

    # 3. Communication Spikes & Communication Alerts
    alerts = db.query(Alert).filter(Alert.case_id == case.id).all()
    for a in alerts:
        a_date = a.alert_date or (a.created_at.strftime("%Y-%m-%d") if a.created_at else "")
        if not a_date:
            continue
        ev_type = "call_spike" if a.pattern_type == "sudden_spike" else "alert"
        events.append({
            "id": f"alert-{a.id}",
            "type": ev_type,
            "timestamp": str(a_date)[:10],
            "title": f"{a.pattern_type.replace('_', ' ').title()}: {a.entity_id}",
            "summary": a.explanation or "Pattern detected by algorithmic baseline.",
            "severity": a.severity or "medium",
            "entities": [a.entity_id] if a.entity_id else [],
            "source_file": None,
            "details": {"alert_id": a.id, "severity": a.severity}
        })

    # 4. Lead Decisions
    decisions = db.query(LeadDecision).filter(LeadDecision.case_id == case.id).all()
    for ld in decisions:
        d_str = ld.decided_at.strftime("%Y-%m-%d") if ld.decided_at else ""
        if d_str:
            events.append({
                "id": f"dec-{ld.id}",
                "type": "lead_decision",
                "timestamp": d_str,
                "title": f"Investigator Decision: {ld.decision.upper()}",
                "summary": f"Lead {ld.lead_id} | Notes: {ld.notes or 'No notes recorded'}",
                "severity": "success" if ld.decision == "accept" else "low",
                "entities": [ld.lead_id],
                "source_file": None,
                "details": {"decision": ld.decision, "notes": ld.notes, "user_id": ld.user_id}
            })

    # Filter by entity if requested
    if entity:
        ent_clean = str(entity).strip().lower()
        events = [
            e for e in events
            if any(ent_clean in str(ent).lower() for ent in e.get("entities", []))
            or ent_clean in e.get("title", "").lower()
            or ent_clean in e.get("summary", "").lower()
        ]

    # Filter by type if requested
    if event_type:
        type_clean = str(event_type).strip().lower()
        events = [e for e in events if e.get("type", "").lower() == type_clean]

    # Filter by date bounds
    if from_date:
        events = [e for e in events if e.get("timestamp", "") >= from_date]
    if to_date:
        events = [e for e in events if e.get("timestamp", "") <= to_date]

    # Sort chronologically by timestamp
    events.sort(key=lambda x: (x.get("timestamp", ""), x.get("type", "")))

    # Compute sequence timing analysis: "First Alert/Spike vs First Document"
    doc_dates = [e["timestamp"] for e in events if e["type"] in ("document", "document_upload") and e["timestamp"]]
    anomaly_dates = [e["timestamp"] for e in events if e["type"] in ("call_spike", "alert", "transaction_wave") and e["timestamp"]]

    earliest_doc = min(doc_dates) if doc_dates else None
    earliest_anomaly = min(anomaly_dates) if anomaly_dates else None

    timing_insight = None
    if earliest_doc and earliest_anomaly:
        try:
            d_doc = datetime.strptime(earliest_doc[:10], "%Y-%m-%d")
            d_anom = datetime.strptime(earliest_anomaly[:10], "%Y-%m-%d")
            delta_days = (d_doc - d_anom).days
            if delta_days > 0:
                timing_insight = {
                    "is_pre_document_anomaly": True,
                    "delta_days": delta_days,
                    "earliest_anomaly_date": earliest_anomaly,
                    "earliest_document_date": earliest_doc,
                    "description": f"Organized activity (call spike/transfer wave) detected {delta_days} day(s) BEFORE the first formal document registration ({earliest_doc})."
                }
            elif delta_days < 0:
                timing_insight = {
                    "is_pre_document_anomaly": False,
                    "delta_days": abs(delta_days),
                    "earliest_anomaly_date": earliest_anomaly,
                    "earliest_document_date": earliest_doc,
                    "description": f"First document filed on {earliest_doc}; network anomalies escalated {abs(delta_days)} day(s) afterwards."
                }
            else:
                timing_insight = {
                    "is_pre_document_anomaly": False,
                    "delta_days": 0,
                    "earliest_anomaly_date": earliest_anomaly,
                    "earliest_document_date": earliest_doc,
                    "description": f"First network anomaly coincided exactly with document registration on {earliest_doc}."
                }
        except Exception:
            pass

    return {
        "total_events": len(events),
        "capped": len(events) > limit,
        "timing_insight": timing_insight,
        "events": events[:limit]
    }


# -------------------------------------------------------------------------
# 12. AUTO-ANALYZE & CRIME DISCOVERY (ONE-CLICK FORENSIC ANALYSIS)
# -------------------------------------------------------------------------
@router.post("/cases/{case_id}/auto-analyze")
def auto_analyze_case(
    case_id: str,
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Automated One-Click Pipeline:
    1. Ingests and processes any uningested evidence files (CSVs, Excel, PDFs, Images/Photos via OCR).
    2. Auto-stages calls, transactions, and extracted entities.
    3. Rebuilds and synchronizes the investigation network graph.
    4. Runs multi-hop Money Trail, MAD call spike analysis, and 5-signal Lead Advisor.
    5. Returns prioritized suspects / leads with human-readable explanations.
    """
    from pathlib import Path
    from backend.app.services.ingestion.readers import read_tabular_file
    from backend.app.services.ingestion.detect import detect_file_type
    from backend.app.services.ingestion.mapping import suggest_column_mappings
    from backend.app.services.ingestion.stage import stage_evidence_file
    from backend.app.services.extraction.pipeline import run_document_extraction
    from backend.app.services.extraction.router import _commit_approved_entity
    from backend.app.services.graph.builder import invalidate_case_graph, build_detail_graph, CASE_GRAPH_CACHE
    from backend.app.services.graph.projection import build_entity_projection

    files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case.id).all()
    files_processed = 0

    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
    doc_exts = {".pdf", ".docx", ".txt", ".text"}
    tabular_exts = {".csv", ".xlsx", ".json", ".jsonl"}

    for ev in files:
        stored = Path(ev.stored_path)
        if not stored.exists():
            continue
        ext = stored.suffix.lower()

        # 1. Tabular Ingestion (CDR / Bank Transactions / SDR / IP Logs)
        if ext in tabular_exts and ev.status in ["uploaded", "mapped", "pending"]:
            try:
                records, headers, _ = read_tabular_file(stored)
                if records and headers:
                    detection = detect_file_type(headers, records, filename=ev.original_name)
                    best_type = detection.get("detected_type", "cdr")
                    if best_type == "unknown":
                        best_type = "cdr"
                    suggested = suggest_column_mappings(best_type, headers)
                    mapping = {h: v["canonical"] for h, v in suggested.items() if "canonical" in v}
                    stage_evidence_file(db, ev.id, current_user.id, best_type, mapping)
                    ev.status = "ingested"
                    files_processed += 1
            except Exception:
                pass

        # 2. Document & Image Extraction (FIRs, Bank Statement Photos, Cheques, Notes)
        elif (ext in doc_exts or ext in image_exts) and ev.status in ["uploaded", "pending"]:
            try:
                res = run_document_extraction(db, ev.id, case.id, str(stored))
                extracted_entities = db.query(ExtractedEntity).filter(
                    ExtractedEntity.evidence_id == ev.id,
                    ExtractedEntity.status == "pending_review"
                ).all()
                for ee in extracted_entities:
                    ee.status = "approved"
                    _commit_approved_entity(db, ee, current_user.id)
                ev.status = "extracted"
                files_processed += 1
            except Exception:
                pass

    db.commit()

    # 3. Synchronize Graph
    invalidate_case_graph(case.id)
    try:
        detail_g = build_detail_graph(db, case.id)
        entity_g = build_entity_projection(detail_g)
        CASE_GRAPH_CACHE[case.id] = (detail_g, entity_g)
    except Exception:
        pass

    # 4. Compute Patterns & Leads
    settings = get_effective_case_settings(db, case.id)
    all_txns = db.query(Transaction).filter(Transaction.case_id == case.id).all()
    money_alerts = detect_money_patterns(all_txns, settings)

    all_calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).all()
    comm_alerts = detect_communication_patterns(all_calls, settings)
    all_alerts = comm_alerts + money_alerts

    entities = db.query(Entity).filter(Entity.case_id == case.id).all()
    entity_links = db.query(EntityLink).filter(EntityLink.case_id == case.id).all()
    extracted_entities = db.query(ExtractedEntity).filter(ExtractedEntity.case_id == case.id).all()

    lead_data = compute_lead_advisor(
        case_id=case.id,
        entities=entities,
        entity_links=entity_links,
        call_records=all_calls,
        transactions=all_txns,
        evidence_files=files,
        extracted_entities=extracted_entities,
        alerts=all_alerts,
        settings=settings
    )
    raw_leads = lead_data.get("leads", [])

    # 5. Format Top Suspects List
    suspects = []
    for rank, ld in enumerate(raw_leads[:8], start=1):
        entity_id = ld["entity_id"]
        matching_alerts = [a for a in money_alerts + comm_alerts if a.get("entity_id") == entity_id]
        alert_notes = [a.get("explanation", "") for a in matching_alerts]

        reason = ld.get("narrative") or "High composite priority score across network activity"
        if alert_notes:
            reason = f"{alert_notes[0]} | {reason}"

        suspects.append({
            "rank": rank,
            "entity_id": entity_id,
            "display_name": ld.get("display_name") or entity_id,
            "type": ld.get("entity_type", "Entity"),
            "risk_level": ld.get("level", "MEDIUM"),
            "score": ld.get("priority", 0),
            "reason": reason,
            "signals": ld.get("signals", {}),
            "alerts_count": len(matching_alerts)
        })

    record_audit_log(
        db=db,
        user_id=current_user.id,
        action="auto_analyze_case",
        case_id=case.id,
        object_type="case",
        object_id=case.id,
        details={"files_processed": files_processed, "suspects_identified": len(suspects)}
    )

    total_entities = db.query(Entity).filter(Entity.case_id == case.id).count()
    total_txns = db.query(Transaction).filter(Transaction.case_id == case.id).count()
    total_calls = db.query(CallRecord).filter(CallRecord.case_id == case.id).count()

    return {
        "status": "success",
        "case_id": case.id,
        "files_processed": files_processed,
        "stats": {
            "total_entities": total_entities,
            "total_transactions": total_txns,
            "total_calls": total_calls,
            "suspects_found": len(suspects)
        },
        "suspects": suspects
    }
