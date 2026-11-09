from typing import List, Dict, Any, Optional, Tuple
from backend.app.config import get_merge_config


def get_source_trust_rank(source_kind: str, trust_order: Optional[List[str]] = None) -> int:
    """
    Returns an integer trust rank for source_kind based on `merge.source_trust_order` in defaults.yaml.
    Higher integer = higher trust.
    """
    if trust_order is None:
        trust_order = get_merge_config().get("source_trust_order", [
            "officer",
            "structured_file",
            "text_layer_pdf",
            "ocr_printed",
            "ocr_handwritten",
            "asr_audio",
            "vision_cloud",
        ])
    sk = (source_kind or "").strip().lower()
    if sk in trust_order:
        return len(trust_order) - trust_order.index(sk)
    return 0


def claim_ordering_key(claim: Dict[str, Any], trust_order: Optional[List[str]] = None) -> Tuple[int, int, float, str, str]:
    """
    Deterministic ordering key per Phase 3 specification:
    (trust_rank, validator_ok, confidence, observed_at, claim_id)
    """
    t_rank = get_source_trust_rank(str(claim.get("source_kind", "")), trust_order)
    v_ok = 1 if bool(claim.get("validator_ok", True)) else 0
    conf = round(float(claim.get("confidence", 0.0)), 6)
    obs = str(claim.get("observed_at") or "")
    cid = str(claim.get("id") or "")
    return (t_rank, v_ok, conf, obs, cid)


def resolve_field_claims(
    claims: List[Dict[str, Any]],
    current_golden: Optional[Dict[str, Any]] = None,
    merge_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Pure, deterministic, order-independent field resolution across active claims for a single (subject, field).

    Returns:
      {
        "selected_claim_id": str | None,
        "selected_value": str | None,
        "selected_by": "auto" | "officer",
        "locked": bool,
        "has_conflict": bool,
        "conflicting_claim_ids": List[str],
        "reason_code": str,
        "notice": str | None,
        "effective_confidence": float,
      }
    """
    cfg = merge_config or get_merge_config()
    trust_order: List[str] = cfg.get("source_trust_order", [
        "officer",
        "structured_file",
        "text_layer_pdf",
        "ocr_printed",
        "ocr_handwritten",
        "asr_audio",
        "vision_cloud",
    ])
    margin = float(cfg.get("conflict_confidence_margin", 0.08))
    min_auto = float(cfg.get("min_confidence_auto_accept", 0.70))
    boost_step = float(cfg.get("same_value_confidence_boost", 0.05))
    max_boosted = float(cfg.get("max_boosted_confidence", 0.99))

    active_claims = [
        c for c in claims
        if c.get("status", "active") == "active"
        and c.get("value_norm") is not None
        and str(c.get("value_norm")).strip() != ""
    ]

    if not active_claims:
        return {
            "selected_claim_id": None,
            "selected_value": None,
            "selected_by": "auto",
            "locked": False,
            "has_conflict": False,
            "conflicting_claim_ids": [],
            "reason_code": "NO_ACTIVE_CLAIMS",
            "notice": None,
            "effective_confidence": 0.0,
        }

    # 1. Officer Lock Check: locked fields are never overwritten by subsequent ingests
    if current_golden and bool(current_golden.get("locked")):
        locked_cid = current_golden.get("selected_claim_id")
        locked_claim = next((c for c in active_claims if c.get("id") == locked_cid), None)
        if locked_claim is not None:
            locked_val = str(locked_claim["value_norm"])
            differs = any(str(c["value_norm"]) != locked_val for c in active_claims)
            return {
                "selected_claim_id": locked_claim["id"],
                "selected_value": locked_val,
                "selected_by": "officer",
                "locked": True,
                "has_conflict": False,
                "conflicting_claim_ids": [],
                "reason_code": current_golden.get("reason_code") or "OFFICER_LOCKED",
                "notice": "NEW_EVIDENCE_DIFFERS_FROM_LOCKED" if differs else None,
                "effective_confidence": 1.0,
            }

    # 2. Group active claims by normalized value
    by_val: Dict[str, List[Dict[str, Any]]] = {}
    for c in active_claims:
        v_str = str(c["value_norm"])
        by_val.setdefault(v_str, []).append(c)

    value_groups: List[Dict[str, Any]] = []
    for v_str, group in by_val.items():
        # Order claims within the same value group deterministically;
        # prefer earliest/deterministic claim id so re-ingest does not churn selected_claim_id
        sorted_group = sorted(
            group,
            key=lambda c: (
                get_source_trust_rank(str(c.get("source_kind", "")), trust_order),
                1 if bool(c.get("validator_ok", True)) else 0,
                round(float(c.get("confidence", 0.0)), 6),
            ),
            reverse=True,
        )
        rep = sorted_group[0]
        t_rank = get_source_trust_rank(str(rep.get("source_kind", "")), trust_order)
        v_ok = 1 if bool(rep.get("validator_ok", True)) else 0
        base_conf = round(float(rep.get("confidence", 0.0)), 6)
        distinct_ev = len({c.get("evidence_id") for c in group if c.get("evidence_id")})
        eff_conf = (
            min(max_boosted, round(base_conf + boost_step * (distinct_ev - 1), 4))
            if distinct_ev > 1
            else base_conf
        )
        value_groups.append({
            "value_norm": v_str,
            "representative": rep,
            "all_claims": sorted_group,
            "trust_rank": t_rank,
            "validator_ok": v_ok,
            "base_confidence": base_conf,
            "effective_confidence": eff_conf,
            "distinct_sources": distinct_ev,
        })

    # 3. Single distinct normalized value -> Unanimous auto-selection
    if len(value_groups) == 1:
        vg = value_groups[0]
        rep = vg["representative"]
        # If current_golden already points to an active claim in this group with equal strength, keep it stable
        if current_golden and current_golden.get("selected_claim_id"):
            existing_match = next(
                (
                    c for c in vg["all_claims"]
                    if c.get("id") == current_golden.get("selected_claim_id")
                    and get_source_trust_rank(str(c.get("source_kind", "")), trust_order) == vg["trust_rank"]
                    and (1 if bool(c.get("validator_ok", True)) else 0) == vg["validator_ok"]
                    and round(float(c.get("confidence", 0.0)), 6) == vg["base_confidence"]
                ),
                None,
            )
            if existing_match is not None:
                rep = existing_match

        is_officer = str(rep.get("source_kind", "")) == "officer"
        reason = (
            "OFFICER_CORRECTION"
            if is_officer
            else ("CORROBORATED_BY_MULTIPLE_SOURCES" if vg["distinct_sources"] > 1 else "SINGLE_UNCONTESTED_VALUE")
        )
        return {
            "selected_claim_id": rep["id"],
            "selected_value": vg["value_norm"],
            "selected_by": "officer" if is_officer else "auto",
            "locked": True if is_officer else False,
            "has_conflict": False,
            "conflicting_claim_ids": [],
            "reason_code": reason,
            "notice": None,
            "effective_confidence": 1.0 if is_officer else vg["effective_confidence"],
        }

    # 4. Multiple distinct normalized values -> Compare top two using order-independent rank
    # Order-independent sort key across distinct value groups: (validator_ok, trust_rank, base_confidence, value_norm)
    value_groups.sort(
        key=lambda g: (g["validator_ok"], g["trust_rank"], g["base_confidence"], g["value_norm"]),
        reverse=True,
    )
    top1 = value_groups[0]
    top2 = value_groups[1]

    auto_win = False
    win_reason = ""

    if top1["validator_ok"] > top2["validator_ok"]:
        auto_win = True
        win_reason = "VALIDATOR_PASSED_OVER_INVALID"
    elif top1["trust_rank"] > top2["trust_rank"] and top1["base_confidence"] >= min_auto:
        auto_win = True
        win_reason = "HIGHER_SOURCE_TRUST"
    elif (
        top1["trust_rank"] == top2["trust_rank"]
        and (top1["base_confidence"] - top2["base_confidence"]) >= (margin - 1e-9)
        and top1["base_confidence"] >= min_auto
    ):
        auto_win = True
        win_reason = "CONFIDENCE_EXCEEDS_MARGIN"

    if auto_win:
        rep = top1["representative"]
        is_officer = str(rep.get("source_kind", "")) == "officer"
        return {
            "selected_claim_id": rep["id"],
            "selected_value": top1["value_norm"],
            "selected_by": "officer" if is_officer else "auto",
            "locked": True if is_officer else False,
            "has_conflict": False,
            "conflicting_claim_ids": [],
            "reason_code": "OFFICER_CORRECTION" if is_officer else win_reason,
            "notice": None,
            "effective_confidence": 1.0 if is_officer else top1["effective_confidence"],
        }

    # 5. Conflict: top two have different normalized values and cannot be auto-resolved
    competing_ids = [g["representative"]["id"] for g in value_groups]

    # Keep the previous golden value until an officer decides (if still active)
    prev_cid = current_golden.get("selected_claim_id") if current_golden else None
    prev_claim = next((c for c in active_claims if c.get("id") == prev_cid), None) if prev_cid else None
    chosen_claim = prev_claim if prev_claim is not None else top1["representative"]

    return {
        "selected_claim_id": chosen_claim["id"],
        "selected_value": str(chosen_claim["value_norm"]),
        "selected_by": "auto",
        "locked": False,
        "has_conflict": True,
        "conflicting_claim_ids": competing_ids,
        "reason_code": "CONFLICTING_CLAIMS_WITHIN_MARGIN",
        "notice": "OPEN_CONFLICT_REQUIRES_OFFICER_REVIEW",
        "effective_confidence": float(chosen_claim.get("confidence", 0.0)),
    }

