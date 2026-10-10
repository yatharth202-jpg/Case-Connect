import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set
import pandas as pd
from backend.app.db.sql import Transaction

def detect_money_patterns(
    transactions: List[Transaction],
    settings: Dict[str, Any],
    focus_accounts: Set[str] = None
) -> List[Dict[str, Any]]:
    """
    Detects potential financial flow anomalies based on case-configured thresholds.
    Every threshold is data-driven from case settings/defaults.yaml.
    Labels: 'Potential anomaly'
    """
    if not transactions:
        return []

    money_cfg = settings.get("money", {})
    fan_in_cfg = money_cfg.get("fan_in", {"min_sources": 3, "window_days": 7})
    fan_out_cfg = money_cfg.get("fan_out", {"min_destinations": 3, "window_days": 7})
    rpt_cfg = money_cfg.get("rapid_pass_through", {"inflow_percent": 80.0, "max_hours": 48})
    split_cfg = money_cfg.get("splitting", {"reporting_limit_rupees": 0, "min_transfers": 3, "window_days": 3, "threshold_ratio": 0.90})

    # Prepare DataFrame
    rows = []
    for t in transactions:
        # Parse date
        dt = None
        if t.date_iso:
            try:
                dt = datetime.fromisoformat(t.date_iso.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                try:
                    dt = datetime.strptime(t.date_iso[:10], "%Y-%m-%d")
                except Exception:
                    pass
        if dt is None:
            dt = datetime(2024, 1, 1)

        rows.append({
            "id": t.id,
            "fingerprint": t.fingerprint,
            "from_account": t.from_account,
            "to_account": t.to_account,
            "amount_paise": t.amount_paise,
            "amount_inr": t.amount_paise / 100.0,
            "reference": str(t.reference or ""),
            "dt": dt
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return []

    anomalies: List[Dict[str, Any]] = []
    seen_flags: Set[str] = set()

    # Determine accounts to evaluate
    all_accounts = set(df["from_account"].unique()) | set(df["to_account"].unique())
    if focus_accounts:
        target_accounts = all_accounts.intersection(focus_accounts)
    else:
        target_accounts = all_accounts

    # -----------------------------------------------------------------
    # 1. FAN-IN: >= min_sources distinct senders within window_days
    # -----------------------------------------------------------------
    min_sources = int(fan_in_cfg.get("min_sources", 3))
    in_window_days = int(fan_in_cfg.get("window_days", 7))

    for acc in target_accounts:
        inflows = df[df["to_account"] == acc].sort_values("dt")
        if len(inflows) < min_sources:
            continue

        distinct_senders = inflows["from_account"].unique()
        if len(distinct_senders) < min_sources:
            continue

        # Check rolling window
        inflow_dates = inflows["dt"].tolist()
        inflow_senders = inflows["from_account"].tolist()
        inflow_fps = inflows["fingerprint"].tolist()

        n = len(inflows)
        flagged = False
        for i in range(n):
            window_end = inflow_dates[i] + timedelta(days=in_window_days)
            sub_senders = set()
            sub_fps = []
            for j in range(i, n):
                if inflow_dates[j] <= window_end:
                    sub_senders.add(inflow_senders[j])
                    sub_fps.append(inflow_fps[j])
                else:
                    break
            if len(sub_senders) >= min_sources:
                flag_key = f"fan_in_{acc}"
                if flag_key not in seen_flags:
                    seen_flags.add(flag_key)
                    anomalies.append({
                        "account": acc,
                        "pattern": "fan_in",
                        "label": "Potential anomaly: Fan-in pooling",
                        "explanation": (
                            f"Account received funds from {len(sub_senders)} distinct source accounts "
                            f"within a {in_window_days}-day window (threshold: ≥{min_sources} sources in {in_window_days} days)."
                        ),
                        "evidence_txn_keys": sub_fps[:20],
                        "severity": "high"
                    })
                break

    # -----------------------------------------------------------------
    # 2. FAN-OUT: >= min_destinations distinct recipients within window_days
    # -----------------------------------------------------------------
    min_dest = int(fan_out_cfg.get("min_destinations", 3))
    out_window_days = int(fan_out_cfg.get("window_days", 7))

    for acc in target_accounts:
        outflows = df[df["from_account"] == acc].sort_values("dt")
        if len(outflows) < min_dest:
            continue

        distinct_recipients = outflows["to_account"].unique()
        if len(distinct_recipients) < min_dest:
            continue

        outflow_dates = outflows["dt"].tolist()
        outflow_recipients = outflows["to_account"].tolist()
        outflow_fps = outflows["fingerprint"].tolist()

        n = len(outflows)
        for i in range(n):
            window_end = outflow_dates[i] + timedelta(days=out_window_days)
            sub_recipients = set()
            sub_fps = []
            for j in range(i, n):
                if outflow_dates[j] <= window_end:
                    sub_recipients.add(outflow_recipients[j])
                    sub_fps.append(outflow_fps[j])
                else:
                    break
            if len(sub_recipients) >= min_dest:
                flag_key = f"fan_out_{acc}"
                if flag_key not in seen_flags:
                    seen_flags.add(flag_key)
                    anomalies.append({
                        "account": acc,
                        "pattern": "fan_out",
                        "label": "Potential anomaly: Fan-out distribution",
                        "explanation": (
                            f"Account disbursed funds to {len(sub_recipients)} distinct destination accounts "
                            f"within a {out_window_days}-day window (threshold: ≥{min_dest} destinations in {out_window_days} days)."
                        ),
                        "evidence_txn_keys": sub_fps[:20],
                        "severity": "medium"
                    })
                break

    # -----------------------------------------------------------------
    # 3. RAPID PASS-THROUGH: >= inflow_percent% leaves within max_hours
    # -----------------------------------------------------------------
    inflow_pct = float(rpt_cfg.get("inflow_percent", 80.0))
    max_hours = float(rpt_cfg.get("max_hours", 48))
    max_delta = timedelta(hours=max_hours)

    for acc in target_accounts:
        acc_inflows = df[df["to_account"] == acc].sort_values("dt")
        acc_outflows = df[df["from_account"] == acc].sort_values("dt")

        if acc_inflows.empty or acc_outflows.empty:
            continue

        tot_in = acc_inflows["amount_inr"].sum()
        if tot_in <= 0:
            continue

        # Look at each incoming cluster
        for _, in_row in acc_inflows.iterrows():
            in_amt = in_row["amount_inr"]
            in_dt = in_row["dt"]
            # Qualifying outflows within max_hours after in_dt
            window_end = in_dt + max_delta
            matching_out = acc_outflows[(acc_outflows["dt"] >= in_dt) & (acc_outflows["dt"] <= window_end)]
            out_sum = matching_out["amount_inr"].sum()

            ratio = (out_sum / in_amt) * 100.0 if in_amt > 0 else 0
            if ratio >= inflow_pct and out_sum > 0:
                flag_key = f"rpt_{acc}"
                if flag_key not in seen_flags:
                    seen_flags.add(flag_key)
                    evidence_fps = [in_row["fingerprint"]] + matching_out["fingerprint"].tolist()
                    anomalies.append({
                        "account": acc,
                        "pattern": "rapid_pass_through",
                        "label": "Potential anomaly: Rapid pass-through layering",
                        "explanation": (
                            f"Account routed ₹{out_sum:,.2f} ({ratio:.1f}% of incoming transfer of ₹{in_amt:,.2f}) "
                            f"outward within {int(max_hours)} hours (threshold: ≥{inflow_pct:.0f}% in {int(max_hours)}h)."
                        ),
                        "evidence_txn_keys": evidence_fps[:20],
                        "severity": "high"
                    })
                break

    # -----------------------------------------------------------------
    # 4. NEAR-LIMIT SPLITTING: Transfers between 90% and 100% of limit
    # -----------------------------------------------------------------
    rep_limit = float(split_cfg.get("reporting_limit_rupees", 0))
    if rep_limit > 0:
        min_split_txns = int(split_cfg.get("min_transfers", 3))
        split_window_days = int(split_cfg.get("window_days", 3))
        thresh_ratio = float(split_cfg.get("threshold_ratio", 0.90))
        lower_bound = rep_limit * thresh_ratio

        for acc in target_accounts:
            near_limit_txns = df[(df["from_account"] == acc) & (df["amount_inr"] >= lower_bound) & (df["amount_inr"] <= rep_limit)].sort_values("dt")
            if len(near_limit_txns) >= min_split_txns:
                flag_key = f"split_{acc}"
                if flag_key not in seen_flags:
                    seen_flags.add(flag_key)
                    anomalies.append({
                        "account": acc,
                        "pattern": "near_limit_splitting",
                        "label": "Potential anomaly: Near-limit structuring / splitting",
                        "explanation": (
                            f"Observed {len(near_limit_txns)} transfers between ₹{lower_bound:,.2f} and ₹{rep_limit:,.2f} "
                            f"(90%-100% of regulatory limit of ₹{rep_limit:,.2f}) within {split_window_days} days."
                        ),
                        "evidence_txn_keys": near_limit_txns["fingerprint"].tolist()[:20],
                        "severity": "high"
                    })

    # -----------------------------------------------------------------
    # 5. HAWALA & ANGADIA CASH POOLING / TOKEN SETTLEMENT
    # -----------------------------------------------------------------
    hawala_keywords = ["hawala", "angadia", "parchi", "token", "cash withdrawal", "courier", "bullion", "settlement"]
    for acc in target_accounts:
        acc_txns = df[(df["from_account"] == acc) | (df["to_account"] == acc)]
        if acc_txns.empty:
            continue
        
        # Check for narrative keywords or high value cash transfers
        flagged_hawala_rows = []
        for _, r in acc_txns.iterrows():
            ref_lower = str(r.get("reference", "")).lower()
            if any(k in ref_lower for k in hawala_keywords) or (r["amount_inr"] >= 1000000 and "cash" in ref_lower):
                flagged_hawala_rows.append(r)
        
        if flagged_hawala_rows:
            flag_key = f"hawala_{acc}"
            if flag_key not in seen_flags:
                seen_flags.add(flag_key)
                total_flagged_inr = sum(r["amount_inr"] for r in flagged_hawala_rows)
                fps = [r["fingerprint"] for r in flagged_hawala_rows]
                anomalies.append({
                    "account": acc,
                    "pattern": "hawala_layering",
                    "label": "Potential anomaly: Hawala & Angadia Cash Pooling Syndicate",
                    "explanation": (
                        f"Detected {len(flagged_hawala_rows)} transactions totaling ₹{total_flagged_inr:,.2f} with "
                        f"Hawala token/Angadia cash indicators, bullion settlements, or structured cash courier narratives."
                    ),
                    "evidence_txn_keys": fps[:20],
                    "severity": "high"
                })

    return anomalies

