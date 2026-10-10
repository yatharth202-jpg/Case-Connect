from typing import Optional, List, Dict, Any
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.db.sql import get_db, Case, Transaction, User
from backend.app.auth.deps import get_current_user
from backend.app.cases.deps import get_case_for_user
from backend.app.cases.router import get_effective_case_settings
from backend.app.services.money.trail import build_money_trail

router = APIRouter()

@router.get("/cases/{case_id}/money-trail")
def get_money_trail_endpoint(
    case_id: str,
    account: Optional[str] = Query(None),
    min_amount: float = Query(0.0, ge=0.0),
    hops: int = Query(2, ge=1, le=4),
    direction: str = Query("both", pattern="^(in|out|both)$"),
    limit: int = Query(200, ge=10, le=500),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the BankAccount-level Money Trail graph.
    - account: seed account ID or holder name query.
    - min_amount: rupee threshold filter (edges below this appear in hidden_edges).
    - hops: 1 to 4 transaction hops.
    - direction: 'in', 'out', or 'both'.
    """
    settings = get_effective_case_settings(db, case.id)
    result = build_money_trail(
        db=db,
        case_id=case.id,
        account_query=account,
        min_amount_rupees=min_amount,
        hops=hops,
        direction=direction,
        limit=limit,
        case_settings=settings
    )
    return result

@router.get("/cases/{case_id}/analytics/txn-volume")
def get_transaction_volume_analytics(
    case_id: str,
    account: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes data-driven transaction distribution and amount quantiles (p50, p75, p90, p99)
    for quick filter chips with zero hardcoded rupee presets.
    """
    q_tx = db.query(Transaction).filter(Transaction.case_id == case.id)
    if account:
        q_tx = q_tx.filter((Transaction.from_account == account) | (Transaction.to_account == account))
    if from_date:
        q_tx = q_tx.filter(Transaction.date_iso >= from_date)
    if to_date:
        q_tx = q_tx.filter(Transaction.date_iso <= to_date)
    txns = q_tx.all()
    if not txns:
        return {
            "total_volume_paise": 0,
            "total_volume_inr": 0.0,
            "total_txns": 0,
            "quantiles": {
                "p50": 0.0,
                "p75": 0.0,
                "p90": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0
            },
            "daily_volume": []
        }

    amounts_inr = [t.amount_paise / 100.0 for t in txns]
    amounts_inr.sort()

    arr = np.array(amounts_inr)
    p50 = float(np.percentile(arr, 50))
    p75 = float(np.percentile(arr, 75))
    p90 = float(np.percentile(arr, 90))
    p99 = float(np.percentile(arr, 99))
    min_val = float(np.min(arr))
    max_val = float(np.max(arr))

    total_paise = sum(t.amount_paise for t in txns)

    # Group daily
    daily_map: Dict[str, Dict[str, Any]] = {}
    for t in txns:
        d = t.date_iso[:10] if t.date_iso else "unknown"
        if d not in daily_map:
            daily_map[d] = {"date": d, "total_paise": 0, "count": 0}
        daily_map[d]["total_paise"] += t.amount_paise
        daily_map[d]["count"] += 1

    daily_list = [
        {
            "date": d_info["date"],
            "amount_inr": d_info["total_paise"] / 100.0,
            "count": d_info["count"]
        }
        for d_info in sorted(daily_map.values(), key=lambda x: x["date"])
    ]

    return {
        "total_volume_paise": total_paise,
        "total_volume_inr": total_paise / 100.0,
        "total_txns": len(txns),
        "quantiles": {
            "p50": round(p50, 2),
            "p75": round(p75, 2),
            "p90": round(p90, 2),
            "p99": round(p99, 2),
            "min": round(min_val, 2),
            "max": round(max_val, 2)
        },
        "daily_volume": daily_list
    }

@router.get("/cases/{case_id}/transactions")
def list_case_transactions(
    case_id: str,
    account: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    case: Case = Depends(get_case_for_user),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists raw transactions with optional account and amount filtering for table inspection."""
    query = db.query(Transaction).filter(Transaction.case_id == case.id)
    if account:
        acc_clean = account.strip()
        query = query.filter((Transaction.from_account == acc_clean) | (Transaction.to_account == acc_clean))
    if min_amount is not None:
        min_paise = int(min_amount * 100)
        query = query.filter(Transaction.amount_paise >= min_paise)

    total_count = query.count()
    txns = query.order_by(Transaction.date_iso.desc()).offset(offset).limit(limit).all()

    items = [
        {
            "id": t.id,
            "fingerprint": t.fingerprint,
            "from_account": t.from_account,
            "from_name": t.from_name,
            "to_account": t.to_account,
            "to_name": t.to_name,
            "amount_paise": t.amount_paise,
            "amount_inr": t.amount_paise / 100.0,
            "date": t.date_iso,
            "reference": t.reference,
            "source_file": t.source_file,
            "source_ref": t.source_ref
        }
        for t in txns
    ]

    return {
        "total": total_count,
        "items": items,
        "limit": limit,
        "offset": offset
    }
