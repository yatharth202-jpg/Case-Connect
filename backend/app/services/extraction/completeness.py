"""
Phase 7 — Phone Intelligence, Potential Anomaly Flags, Completeness Engine,
Cross-File Consistency Checks & Evidence Quality Scoring.

All thresholds, required fields, optional detector columns, and pattern types
are loaded from `backend/config/defaults.yaml` via `backend.app.config`.
All outputs use strictly objective, non-prejudicial forensic terminology:
never "real", "fake", "fraud number", or any banned terms.
"""

from datetime import date, datetime, timedelta, timezone
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.config import get_defaults, get_extraction_config
from backend.app.db.sql import (
    Alert,
    CallRecord,
    CaseMember,
    ColumnMapping,
    Entity,
    EvidenceFile,
    EvidencePage,
    ExtractedEntity,
    ExtractionRecord,
    FieldClaim,
    IPEvent,
    MergeConflict,
    RejectedRow,
    Transaction,
    User,
)
from backend.app.services.analytics.comm_patterns import (
    compute_curfew_call_summary,
    detect_communication_patterns,
    parse_date_str,
)
from backend.app.services.extraction.rules import (
    compute_fir_completeness,
    extract_incident_facts,
)
from backend.app.services.ingestion.validators import (
    get_phone_status_model,
    to_ascii_digits,
    validate_phone,
)

DOCUMENTED_COMPLETENESS_FORMULA = (
    "completeness_score = 100 * ("
    "w_req * required_fields_completeness_ratio + "
    "w_valid * valid_rows_ratio + "
    "w_date * date_continuity_ratio + "
    "w_det * detector_columns_present_ratio"
    ")"
)


# ---------------------------------------------------------------------------
# 1. Phone Intelligence & Digit Pattern Anomaly Helpers
# ---------------------------------------------------------------------------

def detect_digit_pattern_anomaly(
    identifier: str,
    min_run: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Checks whether a numeric identifier (phone or account) contains:
      - a repeated identical digit run of length >= `min_run` (e.g. 999999...), or
      - a strictly ascending or descending contiguous digit sequence of length >= `min_run`
        (e.g. 987654... or 612345...).
    Returns a dict with `reason_code`, `pattern_kind`, `run_length`, and `matched_substring`
    when triggered, or None when normal.
    """
    if not identifier:
        return None
    digits = re.sub(r"\D", "", to_ascii_digits(identifier))
    if len(digits) < 6:
        return None

    if min_run is None:
        anom_cfg = (get_extraction_config() or {}).get("anomalies", {}) or {}
        min_run = int(anom_cfg.get("pattern_min_run", 5))

    # 1. Repeated identical digits (e.g. 99999, 000000)
    rep_match = re.search(rf"(\d)\1{{{min_run - 1},}}", digits)
    if rep_match:
        sub = rep_match.group(0)
        return {
            "reason_code": "PATTERN_ANOMALY_REPEATED_DIGITS",
            "pattern_kind": "repeated_digits",
            "run_length": len(sub),
            "matched_substring": sub,
            "explanation": (
                f"Potential Anomaly: identifier {identifier} contains {len(sub)} consecutive identical "
                f"digits ('{sub}', threshold >= {min_run})."
            ),
        }

    # 2. Ascending or descending contiguous digit sequence of length >= min_run
    asc_len = 1
    desc_len = 1
    for i in range(1, len(digits)):
        d_prev = int(digits[i - 1])
        d_cur = int(digits[i])
        if d_cur - d_prev == 1:
            asc_len += 1
            desc_len = 1
            if asc_len >= min_run:
                sub = digits[i - asc_len + 1 : i + 1]
                return {
                    "reason_code": "PATTERN_ANOMALY_ASCENDING_SEQUENCE",
                    "pattern_kind": "ascending_sequence",
                    "run_length": asc_len,
                    "matched_substring": sub,
                    "explanation": (
                        f"Potential Anomaly: identifier {identifier} contains an ascending sequential "
                        f"digit run of length {asc_len} ('{sub}', threshold >= {min_run})."
                    ),
                }
        elif d_prev - d_cur == 1:
            desc_len += 1
            asc_len = 1
            if desc_len >= min_run:
                sub = digits[i - desc_len + 1 : i + 1]
                return {
                    "reason_code": "PATTERN_ANOMALY_DESCENDING_SEQUENCE",
                    "pattern_kind": "descending_sequence",
                    "run_length": desc_len,
                    "matched_substring": sub,
                    "explanation": (
                        f"Potential Anomaly: identifier {identifier} contains a descending sequential "
                        f"digit run of length {desc_len} ('{sub}', threshold >= {min_run})."
                    ),
                }
        else:
            asc_len = 1
            desc_len = 1

    return None


def get_number_intelligence(
    raw_phone: Any,
    db: Optional[Session] = None,
    case_id: Optional[str] = None,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Task 1: Builds the complete Number Status & Intelligence Model for a telephone/mobile number:
      - `format_valid` (bool)
      - `number_type` (str)
      - `region` (str)
      - `carrier_hint` (original allocation, with `carrier_disclaimer`)
      - `line_status` = "unverified" (always — no live lookup exists)
      - `status_label` = "Format valid — ownership unverified" (or "Format invalid — ownership unverified")
      - `potential_anomalies`: list of any pattern, international/VoIP, multi-name, or cross-case flags.
    Never outputs "real", "fake", or prejudicial words.
    """
    ext_cfg = get_extraction_config() or {}
    default_region = str(ext_cfg.get("default_region", "IN")).upper()
    status_model = get_phone_status_model(raw_phone, default_region=default_region)
    norm_num = status_model.get("number") or str(raw_phone or "").strip()

    anomalies: List[Dict[str, Any]] = []
    pat_anom = detect_digit_pattern_anomaly(norm_num)
    if pat_anom:
        anomalies.append(pat_anom)

    if status_model.get("kind") == "international" or status_model.get("region") != default_region or status_model.get("number_type") == "VOIP":
        anomalies.append({
            "reason_code": "INTERNATIONAL_OR_VOIP_NUMBER",
            "pattern_kind": "international_or_voip",
            "region": status_model.get("region"),
            "number_type": status_model.get("number_type"),
            "explanation": (
                f"Potential Anomaly: number {norm_num} has region '{status_model.get('region')}' and "
                f"type '{status_model.get('number_type')}' in a domestic ({default_region}) investigation context."
            ),
        })

    cross_case_summary = None
    if db is not None and norm_num:
        cross_case_summary = _lookup_cross_case_identifier(
            db=db,
            current_case_id=case_id,
            identifier=norm_num,
            current_user=current_user,
        )
        anom_cfg = ext_cfg.get("anomalies", {}) or {}
        min_cases = int(anom_cfg.get("cross_case_min_cases", 2))
        if cross_case_summary["total_cases_count"] >= min_cases:
            anomalies.append({
                "reason_code": "CROSS_CASE_IDENTIFIER",
                "pattern_kind": "cross_case",
                "total_cases_count": cross_case_summary["total_cases_count"],
                "accessible_case_ids": cross_case_summary["accessible_case_ids"],
                "restricted_cases_count": cross_case_summary["restricted_cases_count"],
                "explanation": cross_case_summary["explanation"],
            })

    return {
        **status_model,
        "potential_anomalies": anomalies,
        "has_potential_anomaly": len(anomalies) > 0,
        "cross_case_summary": cross_case_summary,
    }


def _get_user_accessible_case_ids(db: Session, current_user: Optional[User]) -> Optional[Set[str]]:
    """
    Returns None if user is admin (can view all cases), or the set of case_ids
    where `current_user` is a `CaseMember`. If `current_user` is None, returns empty set.
    """
    if current_user is None:
        return set()
    if getattr(current_user, "role", "") == "admin":
        return None
    rows = db.query(CaseMember.case_id).filter(CaseMember.user_id == current_user.id).all()
    return {r[0] for r in rows}


def _lookup_cross_case_identifier(
    db: Session,
    current_case_id: Optional[str],
    identifier: str,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Looks up an identifier (phone or bank account) across all cases in SQLite.
    STRICT PRIVACY & BOLA RULE:
      - Never leaks titles or details of cases where `current_user` is not a member.
      - Shows `accessible_case_ids` ONLY for cases where `current_user` is a member (or admin),
        and reports `restricted_cases_count` for any other cases.
    """
    case_ids_found: Set[str] = set()
    if current_case_id:
        case_ids_found.add(current_case_id)

    for row in db.query(Entity.case_id).filter(Entity.canonical_id == identifier, Entity.is_active == True).distinct().all():
        if row[0]:
            case_ids_found.add(row[0])

    for row in db.query(CallRecord.case_id).filter(
        (CallRecord.caller == identifier) | (CallRecord.receiver == identifier),
        CallRecord.is_active == True,
    ).distinct().all():
        if row[0]:
            case_ids_found.add(row[0])

    for row in db.query(Transaction.case_id).filter(
        (Transaction.from_account == identifier) | (Transaction.to_account == identifier),
        Transaction.is_active == True,
    ).distinct().all():
        if row[0]:
            case_ids_found.add(row[0])

    accessible_set = _get_user_accessible_case_ids(db, current_user)
    if accessible_set is None:
        accessible_ids = sorted(case_ids_found)
        restricted_count = 0
    else:
        allowed = set(accessible_set)
        if current_case_id:
            allowed.add(current_case_id)
        accessible_ids = sorted(cid for cid in case_ids_found if cid in allowed)
        restricted_count = len(case_ids_found) - len(accessible_ids)

    total_count = len(case_ids_found)
    other_count = max(0, total_count - (1 if current_case_id in case_ids_found else 0))

    explanation = (
        f"Identifier {identifier} appears in {total_count} case(s) across the repository "
        f"({len(accessible_ids)} accessible to current officer, {restricted_count} restricted)."
    )
    return {
        "identifier": identifier,
        "total_cases_count": total_count,
        "other_cases_count": other_count,
        "accessible_case_ids": accessible_ids,
        "restricted_cases_count": restricted_count,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# 2. Potential Anomaly Rules Engine (Task 2)
# ---------------------------------------------------------------------------

def evaluate_potential_anomalies(
    db: Session,
    case_id: str,
    current_user: Optional[User] = None,
    persist_alerts: bool = True,
) -> Dict[str, Any]:
    """
    Task 2: Evaluates all Potential Anomaly rules on a case using thresholds from `defaults.yaml`:
      1. Pattern anomalies (repeated digits, ascending/descending sequences of length >= `pattern_min_run`).
      2. International / VoIP-type numbers in domestic context.
      3. Identifiers appearing in many cases (cross-case lookup scoped by membership) or with many different names.
      4. Behavioral CDR anomalies (reusing `analytics/comm_patterns.py` for MAD spikes/pairs/bridges/curfew):
         - night-call ratio in IST (`compute_curfew_call_summary`),
         - many unique counterparties with short call durations,
         - one IMEI with many MSISDNs and one MSISDN with many IMEIs,
         - first/last-seen activity window very short (`<= short_window_hours`).
    Stores generated findings in the `alerts` table (`Alert`) and returns them with `reason_code`,
    `explanation`, `severity`, and `evidence_ids`.
    """
    defaults = get_defaults() or {}
    ext_cfg = get_extraction_config() or {}
    anom_cfg = ext_cfg.get("anomalies", {}) or {}
    default_region = str(ext_cfg.get("default_region", "IN")).upper()

    pattern_min_run = int(anom_cfg.get("pattern_min_run", 5))
    night_ratio_thresh = float(anom_cfg.get("night_ratio_threshold", 0.50))
    min_calls_for_ratio = int(anom_cfg.get("min_calls_for_ratio", 5))
    unique_cp_thresh = int(anom_cfg.get("unique_counterparty_threshold", 10))
    short_call_sec = int(anom_cfg.get("short_call_seconds", 15))
    short_call_ratio_thresh = float(anom_cfg.get("short_call_ratio_threshold", 0.60))
    imei_min_msisdns = int(anom_cfg.get("imei_min_msisdns", 2))
    msisdn_min_imeis = int(anom_cfg.get("msisdn_min_imeis", 2))
    short_window_hours = float(anom_cfg.get("short_window_hours", 24))
    short_window_min_calls = int(anom_cfg.get("short_window_min_calls", 5))
    cross_case_min = int(anom_cfg.get("cross_case_min_cases", 2))
    multi_name_min = int(anom_cfg.get("multi_name_min_distinct", 2))

    # Map evidence original_name -> evidence_id for linking
    ev_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case_id).all()
    ev_name_to_id = {ev.original_name: ev.id for ev in ev_files}
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    call_records = (
        db.query(CallRecord)
        .filter(CallRecord.case_id == case_id, CallRecord.is_active == True)
        .all()
    )
    txns = (
        db.query(Transaction)
        .filter(Transaction.case_id == case_id, Transaction.is_active == True)
        .all()
    )
    entities = (
        db.query(Entity)
        .filter(Entity.case_id == case_id, Entity.is_active == True)
        .all()
    )
    extracted_ents = (
        db.query(ExtractedEntity)
        .filter(ExtractedEntity.case_id == case_id)
        .all()
    )

    findings: List[Dict[str, Any]] = []
    seen_alert_keys: Set[Tuple[str, str]] = set()

    def _add_finding(
        pattern_type: str,
        reason_code: str,
        entity_id: str,
        severity: str,
        explanation: str,
        evidence_ids: List[str],
        alert_date: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ):
        key = (pattern_type, entity_id)
        if key in seen_alert_keys:
            return
        seen_alert_keys.add(key)
        clean_ev_ids = sorted({str(eid) for eid in evidence_ids if eid})
        findings.append({
            "pattern_type": pattern_type,
            "reason_code": reason_code,
            "entity_id": entity_id,
            "severity": severity,
            "date": alert_date or today_iso,
            "explanation": explanation,
            "evidence_ids": clean_ev_ids,
            "metrics": metrics or {},
        })

    # Collect all distinct phone numbers and accounts with their supporting evidence IDs
    phone_ev_map: Dict[str, Set[str]] = {}
    account_ev_map: Dict[str, Set[str]] = {}
    raw_phone_samples: Dict[str, str] = {}

    for c in call_records:
        ev_id = ev_name_to_id.get(c.source_file, c.source_file or c.id)
        for ph in (c.caller, c.receiver):
            if ph:
                phone_ev_map.setdefault(ph, set()).add(ev_id)
                raw_phone_samples.setdefault(ph, ph)
                try:
                    rj = json.loads(c.raw_json or "{}")
                    for rk, rv in rj.items():
                        if rv and str(ph) in str(rv):
                            raw_phone_samples[ph] = str(rv)
                except Exception:
                    pass

    for t in txns:
        ev_id = ev_name_to_id.get(t.source_file, t.source_file or t.id)
        for acc in (t.from_account, t.to_account):
            if acc and acc != "UNKNOWN":
                account_ev_map.setdefault(acc, set()).add(ev_id)

    for e in entities:
        ev_id = ev_name_to_id.get(e.source_file, e.source_file or e.id)
        if e.label == "Phone":
            phone_ev_map.setdefault(e.canonical_id, set()).add(ev_id)
            raw_phone_samples.setdefault(e.canonical_id, e.display_name or e.canonical_id)
        elif e.label == "BankAccount":
            account_ev_map.setdefault(e.canonical_id, set()).add(ev_id)

    for ee in extracted_ents:
        if ee.entity_type == "PHONE":
            phone_ev_map.setdefault(ee.normalized_value, set()).add(ee.evidence_id)
            raw_phone_samples.setdefault(ee.normalized_value, ee.raw_value or ee.normalized_value)
        elif ee.entity_type == "BANK_ACCOUNT":
            account_ev_map.setdefault(ee.normalized_value, set()).add(ee.evidence_id)

    # ------------------------------------------------------------------
    # Rule 2a & 2b: Pattern anomalies & International / VoIP numbers
    # ------------------------------------------------------------------
    for ph, ev_set in sorted(phone_ev_map.items()):
        pat_res = detect_digit_pattern_anomaly(ph, min_run=pattern_min_run)
        if pat_res:
            _add_finding(
                pattern_type="pattern_anomaly_number",
                reason_code=pat_res["reason_code"],
                entity_id=ph,
                severity="medium",
                explanation=pat_res["explanation"],
                evidence_ids=list(ev_set),
                metrics={"run_length": pat_res["run_length"], "pattern_kind": pat_res["pattern_kind"]},
            )

        raw_sample = raw_phone_samples.get(ph, ph)
        # If stored canonical starts with non-91 country code and has 11-15 digits, prefix '+' for phonenumbers
        probe = raw_sample
        if not str(probe).startswith("+") and len(re.sub(r"\D", "", str(probe))) >= 11 and not str(probe).startswith("91") and not str(probe).startswith("0"):
            probe = "+" + re.sub(r"\D", "", str(probe))
        v_res = validate_phone(probe, default_region=default_region)
        v_meta = v_res.get("meta") or {}
        if (
            v_meta.get("kind") == "international"
            or (v_meta.get("region") and v_meta.get("region") != default_region)
            or v_meta.get("number_type") == "VOIP"
        ):
            _add_finding(
                pattern_type="international_or_voip_in_domestic",
                reason_code="INTERNATIONAL_OR_VOIP_NUMBER",
                entity_id=ph,
                severity="medium",
                explanation=(
                    f"Potential Anomaly: number {ph} has region '{v_meta.get('region')}' and type "
                    f"'{v_meta.get('number_type')}' in a domestic ({default_region}) context."
                ),
                evidence_ids=list(ev_set),
                metrics={"region": v_meta.get("region"), "number_type": v_meta.get("number_type")},
            )

    for acc, ev_set in sorted(account_ev_map.items()):
        pat_res = detect_digit_pattern_anomaly(acc, min_run=pattern_min_run)
        if pat_res:
            _add_finding(
                pattern_type="pattern_anomaly_number",
                reason_code=pat_res["reason_code"],
                entity_id=acc,
                severity="low",
                explanation=pat_res["explanation"],
                evidence_ids=list(ev_set),
                metrics={"run_length": pat_res["run_length"], "pattern_kind": pat_res["pattern_kind"]},
            )

    # ------------------------------------------------------------------
    # Rule 2c: Cross-Case Identifiers & Multi-Name Identifiers
    # ------------------------------------------------------------------
    all_identifiers: Dict[str, Set[str]] = {}
    for k, v in phone_ev_map.items():
        all_identifiers.setdefault(k, set()).update(v)
    for k, v in account_ev_map.items():
        all_identifiers.setdefault(k, set()).update(v)

    for ident, ev_set in sorted(all_identifiers.items()):
        cc_info = _lookup_cross_case_identifier(db, case_id, ident, current_user=current_user)
        if cc_info["total_cases_count"] >= cross_case_min:
            _add_finding(
                pattern_type="cross_case_identifier",
                reason_code="CROSS_CASE_IDENTIFIER",
                entity_id=ident,
                severity="high" if cc_info["total_cases_count"] >= 3 else "medium",
                explanation=cc_info["explanation"],
                evidence_ids=list(ev_set),
                metrics={
                    "total_cases_count": cc_info["total_cases_count"],
                    "accessible_case_ids": cc_info["accessible_case_ids"],
                    "restricted_cases_count": cc_info["restricted_cases_count"],
                },
            )

    # Multi-name check per identifier within the case
    ident_names_map: Dict[str, Dict[str, Set[str]]] = {}  # ident -> {norm_name -> set(evidence_ids)}
    for t in txns:
        ev_id = ev_name_to_id.get(t.source_file, t.source_file or t.id)
        if t.from_account and t.from_name and t.from_name.strip():
            ident_names_map.setdefault(t.from_account, {}).setdefault(t.from_name.strip().lower(), set()).add(ev_id)
        if t.to_account and t.to_name and t.to_name.strip():
            ident_names_map.setdefault(t.to_account, {}).setdefault(t.to_name.strip().lower(), set()).add(ev_id)

    # Also check ExtractionRecord (SDR / entity records) and FieldClaims
    active_recs = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.status == "active")
        .all()
    )
    for rec in active_recs:
        try:
            d = json.loads(rec.data_json or "{}")
            ex = json.loads(rec.extra_json or "{}")
            merged_d = {**ex, **d}
            ident_val = merged_d.get("phone") or merged_d.get("account") or merged_d.get("canonical_id")
            name_val = merged_d.get("name") or merged_d.get("subscriber_name") or merged_d.get("holder_name") or merged_d.get("from_name")
            if ident_val and name_val and str(name_val).strip() and str(ident_val).strip() != str(name_val).strip():
                ident_names_map.setdefault(str(ident_val).strip(), {}).setdefault(str(name_val).strip().lower(), set()).add(rec.evidence_id)
        except Exception:
            pass

    # Check FieldClaims for name/display_name claims on records
    rec_by_id = {r.id: r for r in active_recs}
    name_claims = (
        db.query(FieldClaim)
        .filter(
            FieldClaim.case_id == case_id,
            FieldClaim.status == "active",
            FieldClaim.field_name.in_(["name", "subscriber_name", "holder_name", "from_name", "to_name", "display_name"]),
        )
        .all()
    )
    for fc in name_claims:
        rec_obj = rec_by_id.get(fc.subject_id)
        if not rec_obj or not fc.value_norm:
            continue
        try:
            d = json.loads(rec_obj.data_json or "{}")
            ident_val = d.get("phone") or d.get("account") or d.get("canonical_id") or d.get("from_account")
            if ident_val and str(ident_val).strip() != str(fc.value_norm).strip():
                ident_names_map.setdefault(str(ident_val).strip(), {}).setdefault(str(fc.value_norm).strip().lower(), set()).add(fc.evidence_id)
        except Exception:
            pass

    # Also check Entity table (e.g. staged identity tables linking Person to Phone/Account by source_ref)
    case_entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    entity_row_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for ent in case_entities:
        ref_key = (ent.source_file or "", ent.source_ref or "")
        bucket = entity_row_map.setdefault(ref_key, {"names": set(), "identifiers": set(), "ev_id": ev_name_to_id.get(ent.source_file, ent.source_file)})
        if ent.label == "Person" and ent.display_name:
            bucket["names"].add(ent.display_name.strip())
        elif ent.label in ("Phone", "BankAccount") and ent.canonical_id:
            bucket["identifiers"].add(ent.canonical_id.strip())
    for b in entity_row_map.values():
        for name in b["names"]:
            for ident in b["identifiers"]:
                ident_names_map.setdefault(ident, {}).setdefault(name.lower(), set()).add(b["ev_id"])

    # Multi-name check per identifier within the case
    for ident, name_dict in sorted(ident_names_map.items()):
        if len(name_dict) >= multi_name_min:
            distinct_names = sorted(name_dict.keys())
            ev_union: Set[str] = set()
            for s in name_dict.values():
                ev_union.update(s)
            _add_finding(
                pattern_type="multi_name_identifier",
                reason_code="MULTI_NAME_IDENTIFIER",
                entity_id=ident,
                severity="medium",
                explanation=(
                    f"Potential Anomaly: identifier {ident} is associated with {len(distinct_names)} distinct "
                    f"names across evidence sources ({', '.join(distinct_names[:4])})."
                ),
                evidence_ids=list(ev_union),
                metrics={"distinct_names_count": len(distinct_names), "names": distinct_names},
            )

    # ------------------------------------------------------------------
    # Rule 2d: Behavioral CDR Anomalies (reusing analytics/comm_patterns.py)
    # ------------------------------------------------------------------
    if call_records:
        # 1. Reuse detect_communication_patterns (MAD spike, frequent pair, sudden new connection, shared device, bridge)
        comm_alerts = detect_communication_patterns(call_records, defaults)
        for ca in comm_alerts:
            p_type = str(ca.get("pattern_type") or "comm_anomaly")
            _add_finding(
                pattern_type=p_type,
                reason_code=p_type.upper(),
                entity_id=str(ca.get("entity_id") or ""),
                severity=str(ca.get("severity") or "medium"),
                explanation=str(ca.get("explanation") or ""),
                evidence_ids=ca.get("evidence_ids") or [],
                alert_date=ca.get("date"),
                metrics=ca.get("metrics") or {},
            )

        # 2. Night-call ratio in IST via compute_curfew_call_summary (from comm_patterns.py)
        curfew_summary = compute_curfew_call_summary(call_records)
        for ph, c_stats in sorted(curfew_summary.items()):
            tot = int(c_stats.get("total_calls", 0))
            c_ratio = float(c_stats.get("curfew_ratio", 0.0))
            if tot >= min_calls_for_ratio and c_ratio >= night_ratio_thresh:
                _add_finding(
                    pattern_type="high_night_call_ratio",
                    reason_code="HIGH_NIGHT_CALL_RATIO",
                    entity_id=ph,
                    severity="high" if c_ratio >= 0.75 else "medium",
                    explanation=(
                        f"Potential Anomaly: number {ph} has a nocturnal/curfew call ratio of "
                        f"{c_ratio * 100:.1f}% ({c_stats['curfew_calls']}/{tot} calls in 00:00–05:00 IST, "
                        f"threshold >= {night_ratio_thresh * 100:.0f}%)."
                    ),
                    evidence_ids=list(phone_ev_map.get(ph, set())) or c_stats.get("curfew_call_ids", [])[:10],
                    metrics={
                        "total_calls": tot,
                        "curfew_calls": c_stats["curfew_calls"],
                        "curfew_ratio": c_ratio,
                    },
                )

        # 3. Many unique counterparties with short durations, IMEI<->MSISDN ratios, and short activity window
        per_phone_counterparties: Dict[str, Set[str]] = {}
        per_phone_durations: Dict[str, List[int]] = {}
        per_phone_timestamps: Dict[str, List[datetime]] = {}
        imei_to_msisdns: Dict[str, Set[str]] = {}
        msisdn_to_imeis: Dict[str, Set[str]] = {}

        for c in call_records:
            dur = int(c.duration_seconds or 0)
            dt = parse_date_str(c.datetime_iso or c.call_date)
            if c.caller and c.receiver:
                per_phone_counterparties.setdefault(c.caller, set()).add(c.receiver)
                per_phone_counterparties.setdefault(c.receiver, set()).add(c.caller)
            for ph in (c.caller, c.receiver):
                if not ph:
                    continue
                per_phone_durations.setdefault(ph, []).append(dur)
                if dt is not None:
                    per_phone_timestamps.setdefault(ph, []).append(dt)
            imei_val = (c.imei or "").strip()
            if len(imei_val) >= 8 and c.caller:
                imei_to_msisdns.setdefault(imei_val, set()).add(c.caller)
                msisdn_to_imeis.setdefault(c.caller, set()).add(imei_val)

        for ph, cp_set in sorted(per_phone_counterparties.items()):
            durs = per_phone_durations.get(ph, [])
            if len(cp_set) >= unique_cp_thresh and durs:
                short_cnt = sum(1 for d in durs if d <= short_call_sec)
                short_ratio = round(short_cnt / len(durs), 4)
                if short_ratio >= short_call_ratio_thresh:
                    _add_finding(
                        pattern_type="high_unique_short_calls",
                        reason_code="HIGH_UNIQUE_SHORT_CALLS",
                        entity_id=ph,
                        severity="medium",
                        explanation=(
                            f"Potential Anomaly: number {ph} contacted {len(cp_set)} distinct counterparties "
                            f"(threshold >= {unique_cp_thresh}) with {short_ratio * 100:.1f}% of calls lasting "
                            f"<= {short_call_sec}s ({short_cnt}/{len(durs)} calls)."
                        ),
                        evidence_ids=list(phone_ev_map.get(ph, set())),
                        metrics={
                            "unique_counterparties": len(cp_set),
                            "short_calls_count": short_cnt,
                            "total_calls": len(durs),
                            "short_call_ratio": short_ratio,
                        },
                    )

        for imei_val, msisdns in sorted(imei_to_msisdns.items()):
            if len(msisdns) >= imei_min_msisdns:
                m_list = sorted(msisdns)
                _add_finding(
                    pattern_type="imei_multiple_msisdns",
                    reason_code="IMEI_MULTIPLE_MSISDNS",
                    entity_id=imei_val,
                    severity="high",
                    explanation=(
                        f"Potential Anomaly: handset IMEI {imei_val} was associated with {len(m_list)} distinct "
                        f"MSISDNs ({', '.join(m_list[:4])}, threshold >= {imei_min_msisdns})."
                    ),
                    evidence_ids=[ev_id for m in m_list for ev_id in phone_ev_map.get(m, set())],
                    metrics={"msisdn_count": len(m_list), "msisdns": m_list},
                )

        for msisdn_val, imeis in sorted(msisdn_to_imeis.items()):
            if len(imeis) >= msisdn_min_imeis:
                i_list = sorted(imeis)
                _add_finding(
                    pattern_type="msisdn_multiple_imeis",
                    reason_code="MSISDN_MULTIPLE_IMEIS",
                    entity_id=msisdn_val,
                    severity="medium",
                    explanation=(
                        f"Potential Anomaly: number {msisdn_val} was operated across {len(i_list)} distinct "
                        f"handset IMEIs ({', '.join(i_list[:4])}, threshold >= {msisdn_min_imeis})."
                    ),
                    evidence_ids=list(phone_ev_map.get(msisdn_val, set())),
                    metrics={"imei_count": len(i_list), "imeis": i_list},
                )

        for ph, dt_list in sorted(per_phone_timestamps.items()):
            if len(dt_list) >= short_window_min_calls:
                min_dt = min(dt_list)
                max_dt = max(dt_list)
                span_hours = round((max_dt - min_dt).total_seconds() / 3600.0, 2)
                if 0.0 <= span_hours <= short_window_hours:
                    _add_finding(
                        pattern_type="short_activity_window",
                        reason_code="SHORT_ACTIVITY_WINDOW",
                        entity_id=ph,
                        severity="medium",
                        explanation=(
                            f"Potential Anomaly: number {ph} recorded {len(dt_list)} calls within a compact "
                            f"{span_hours:.1f}-hour first-to-last-seen window (threshold <= {short_window_hours}h)."
                        ),
                        evidence_ids=list(phone_ev_map.get(ph, set())),
                        metrics={
                            "call_count": len(dt_list),
                            "span_hours": span_hours,
                            "first_seen": min_dt.isoformat(),
                            "last_seen": max_dt.isoformat(),
                        },
                    )

    if persist_alerts and findings:
        existing_alerts = db.query(Alert).filter(Alert.case_id == case_id).all()
        existing_pairs = {(a.pattern_type, a.entity_id) for a in existing_alerts}
        for f in findings:
            pair = (f["pattern_type"], f["entity_id"])
            if pair not in existing_pairs:
                existing_pairs.add(pair)
                db.add(
                    Alert(
                        case_id=case_id,
                        entity_id=f["entity_id"],
                        pattern_type=f["pattern_type"],
                        severity=f["severity"],
                        alert_date=f["date"],
                        explanation=f["explanation"],
                        evidence_ids_json=json.dumps(f["evidence_ids"]),
                    )
                )
        db.commit()

    return {
        "case_id": case_id,
        "total_flags": len(findings),
        "flags": findings,
        "total_anomalies": len(findings),
        "anomalies": findings,
    }


# ---------------------------------------------------------------------------
# 3. Completeness Engine & Per-Evidence Quality Score (Tasks 3, 4, 5)
# ---------------------------------------------------------------------------

def _find_date_range_gaps(dates: List[date], gap_days_threshold: int) -> List[Dict[str, Any]]:
    """
    Finds contiguous gaps of days with no data between `min(dates)` and `max(dates)`
    where the number of missing days is `>= gap_days_threshold`.
    """
    if not dates:
        return []
    unique_dates = sorted(set(dates))
    if len(unique_dates) < 2:
        return []

    gaps: List[Dict[str, Any]] = []
    for i in range(1, len(unique_dates)):
        prev_d = unique_dates[i - 1]
        cur_d = unique_dates[i]
        missing_days = (cur_d - prev_d).days - 1
        if missing_days >= gap_days_threshold:
            gap_start = prev_d + timedelta(days=1)
            gap_end = cur_d - timedelta(days=1)
            gaps.append({
                "start_date": gap_start.isoformat(),
                "end_date": gap_end.isoformat(),
                "gap_days": missing_days,
                "explanation": (
                    f"{missing_days} consecutive day(s) with no records between "
                    f"{gap_start.isoformat()} and {gap_end.isoformat()} (threshold >= {gap_days_threshold} days)."
                ),
            })
    return gaps


def _extract_date_from_iso(iso_str: Optional[str]) -> Optional[date]:
    if not iso_str:
        return None
    dt = parse_date_str(iso_str)
    if dt is not None:
        return dt.date()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso_str).strip())
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def compute_evidence_completeness(
    db: Session,
    evidence_id: str,
    persist_quality: bool = True,
) -> Dict[str, Any]:
    """
    Task 3 & 5: Computes completeness and quality score for a single evidence file:
      - `record_type` and `required_fields` from `defaults.yaml`
      - `missing_field_counts`: count of rows missing each required field
      - `date_range_gaps`: gaps >= `gap_days_threshold` between min and max date
      - `disabled_detectors`: absent optional columns and the exact detectors they disable
      - `quality_score` & `completeness_score` (0.0 to 100.0) with `score_formula` documented,
        persisted onto `EvidenceFile.quality_json`.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise ValueError(f"Evidence file {evidence_id} not found")

    ext_cfg = get_extraction_config() or {}
    comp_cfg = ext_cfg.get("completeness", {}) or {}
    req_by_type = comp_cfg.get("required_fields", {}) or {}
    opt_detectors_by_type = comp_cfg.get("optional_detector_columns", {}) or {}
    gap_threshold = int(comp_cfg.get("gap_days_threshold", 3))
    weights = comp_cfg.get("score_weights", {}) or {}
    w_req = float(weights.get("required_fields_weight", 0.50))
    w_valid = float(weights.get("valid_rows_weight", 0.25))
    w_date = float(weights.get("date_continuity_weight", 0.15))
    w_det = float(weights.get("detector_columns_weight", 0.10))

    det_type = (ev.detected_type or "").lower()
    if det_type in ("cdr", "call", "calls"):
        rec_type = "call"
    elif det_type in ("bank_transactions", "bank_statement", "transaction", "transactions"):
        rec_type = "transaction"
    elif det_type in ("sdr", "subscriber"):
        rec_type = "sdr"
    elif det_type in ("ipdr", "ip_logs", "ip_event"):
        rec_type = "ip_event"
    else:
        rec_type = "fir"

    req_fields: List[str] = list(req_by_type.get(rec_type, []))
    opt_det_map: Dict[str, str] = dict(opt_detectors_by_type.get(rec_type, {}) or {})

    rejected_count = (
        db.query(RejectedRow)
        .filter(RejectedRow.evidence_id == evidence_id)
        .count()
    )

    pages = (
        db.query(EvidencePage)
        .filter(EvidencePage.evidence_id == evidence_id)
        .all()
    )
    ocr_conf_mean = (
        round(sum(float(p.mean_confidence or 1.0) for p in pages) / len(pages), 4)
        if pages
        else 1.0
    )

    missing_field_counts: Dict[str, int] = {f: 0 for f in req_fields}
    present_opt_columns: Set[str] = set()
    dates_observed: List[date] = []
    valid_rows_count = 0

    # Also check confirmed ColumnMapping if present
    col_map_row = (
        db.query(ColumnMapping)
        .filter(ColumnMapping.evidence_id == evidence_id)
        .order_by(ColumnMapping.confirmed_at.desc())
        .first()
    )
    mapped_targets: Set[str] = set()
    if col_map_row and col_map_row.mapping_json:
        try:
            mp = json.loads(col_map_row.mapping_json)
            if isinstance(mp, dict):
                mapped_targets = {str(v) for v in mp.values() if v}
        except Exception:
            pass

    if rec_type == "call":
        calls = (
            db.query(CallRecord)
            .filter(
                CallRecord.case_id == ev.case_id,
                CallRecord.source_file == ev.original_name,
                CallRecord.is_active == True,
            )
            .all()
        )
        valid_rows_count = len(calls)
        for c in calls:
            row_dict = {
                "caller": c.caller,
                "receiver": c.receiver,
                "datetime_iso": c.datetime_iso or c.call_date,
                "duration_seconds": c.duration_seconds,
                "imei": c.imei,
                "imsi": c.imsi,
                "cell_id": c.cell_id,
            }
            for rf in req_fields:
                val = row_dict.get(rf)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_field_counts[rf] = missing_field_counts.get(rf, 0) + 1
            for opt_col in opt_det_map:
                val = row_dict.get(opt_col)
                if val is not None and str(val).strip() != "":
                    present_opt_columns.add(opt_col)
            d_obj = _extract_date_from_iso(c.datetime_iso or c.call_date)
            if d_obj:
                dates_observed.append(d_obj)

    elif rec_type == "transaction":
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.case_id == ev.case_id,
                Transaction.source_file == ev.original_name,
                Transaction.is_active == True,
            )
            .all()
        )
        valid_rows_count = len(txns)
        for t in txns:
            raw_d = {}
            try:
                raw_d = json.loads(t.raw_json or "{}")
            except Exception:
                pass
            row_dict = {
                "from_account": None if t.from_account in (None, "", "UNKNOWN") else t.from_account,
                "to_account": None if t.to_account in (None, "", "UNKNOWN") else t.to_account,
                "amount_paise": t.amount_paise,
                "date_iso": t.date_iso,
                "reference": t.reference,
                "balance_paise": raw_d.get("balance_paise") or raw_d.get("balance_after_paise") or raw_d.get("Balance"),
            }
            for rf in req_fields:
                val = row_dict.get(rf)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_field_counts[rf] = missing_field_counts.get(rf, 0) + 1
            for opt_col in opt_det_map:
                val = row_dict.get(opt_col)
                if val is not None and str(val).strip() != "":
                    present_opt_columns.add(opt_col)
            d_obj = _extract_date_from_iso(t.date_iso)
            if d_obj:
                dates_observed.append(d_obj)

    elif rec_type == "sdr":
        recs = (
            db.query(ExtractionRecord)
            .filter(
                ExtractionRecord.case_id == ev.case_id,
                ExtractionRecord.evidence_id == evidence_id,
                ExtractionRecord.status == "active",
            )
            .all()
        )
        valid_rows_count = len(recs)
        for r in recs:
            d = json.loads(r.data_json or "{}")
            ex = json.loads(r.extra_json or "{}")
            merged = {**ex, **d}
            row_dict = {
                "phone": merged.get("phone") or merged.get("canonical_id"),
                "name": merged.get("name") or merged.get("subscriber_name") or merged.get("display_name"),
                "address": merged.get("address"),
            }
            for rf in req_fields:
                val = row_dict.get(rf)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_field_counts[rf] = missing_field_counts.get(rf, 0) + 1

    elif rec_type == "ip_event":
        ips = (
            db.query(IPEvent)
            .filter(
                IPEvent.case_id == ev.case_id,
                IPEvent.source_file == ev.original_name,
                IPEvent.is_active == True,
            )
            .all()
        )
        valid_rows_count = len(ips)
        for ip_row in ips:
            row_dict = {
                "identifier": ip_row.identifier,
                "ip_address": ip_row.ip_address,
                "datetime_iso": ip_row.datetime_iso,
            }
            for rf in req_fields:
                val = row_dict.get(rf)
                if val is None or (isinstance(val, str) and not val.strip()):
                    missing_field_counts[rf] = missing_field_counts.get(rf, 0) + 1
            d_obj = _extract_date_from_iso(ip_row.datetime_iso)
            if d_obj:
                dates_observed.append(d_obj)

    else:
        # FIR / narrative document
        ext_ents = (
            db.query(ExtractedEntity)
            .filter(ExtractedEntity.evidence_id == evidence_id)
            .all()
        )
        valid_rows_count = max(1, len(ext_ents))
        full_text = "\n".join(p.corrected_text if p.corrected_text is not None else p.raw_text for p in pages)
        if not full_text and ev.stored_path and Path_exists_safe(ev.stored_path):
            try:
                from backend.app.services.extraction.text import read_document_text

                full_text = read_document_text(ev.stored_path).get("full_text") or ""
            except Exception:
                full_text = ""
        ent_dicts = [
            {
                "entity_type": e.entity_type,
                "raw_value": e.raw_value,
                "normalized_value": e.normalized_value,
                "char_span_start": e.char_span_start or 0,
                "char_span_end": e.char_span_end or 0,
                "page_or_paragraph": e.page_or_paragraph,
                "confidence": e.confidence,
            }
            for e in ext_ents
        ]
        facts_res = extract_incident_facts(full_text, extracted_entities=ent_dicts)
        fir_comp = compute_fir_completeness(facts_res, ent_dicts)
        for rf in req_fields:
            missing_field_counts[rf] = 1 if rf in fir_comp["missing_fields"] else 0
        for t_ev in facts_res.get("timeline", []):
            d_obj = _extract_date_from_iso(t_ev.get("timestamp_iso"))
            if d_obj:
                dates_observed.append(d_obj)

    present_opt_columns.update(mapped_targets.intersection(opt_det_map.keys()))

    disabled_detectors: List[Dict[str, str]] = []
    for opt_col, msg in opt_det_map.items():
        if opt_col not in present_opt_columns:
            disabled_detectors.append({
                "missing_column": opt_col,
                "message": msg,
            })

    date_gaps = _find_date_range_gaps(dates_observed, gap_days_threshold=gap_threshold)
    min_date_str = min(dates_observed).isoformat() if dates_observed else None
    max_date_str = max(dates_observed).isoformat() if dates_observed else None
    span_days = ((max(dates_observed) - min(dates_observed)).days + 1) if len(dates_observed) >= 2 else 1
    total_gap_days = sum(g["gap_days"] for g in date_gaps)
    date_continuity_ratio = max(0.0, min(1.0, 1.0 - (total_gap_days / max(1, span_days)))) if dates_observed else 1.0

    total_rows_considered = valid_rows_count + rejected_count
    valid_rows_ratio = (valid_rows_count / total_rows_considered) if total_rows_considered > 0 else 1.0

    if valid_rows_count > 0 and req_fields:
        total_req_cells = valid_rows_count * len(req_fields) if rec_type != "fir" else len(req_fields)
        missing_cells = sum(missing_field_counts.values())
        req_completeness_ratio = max(0.0, min(1.0, 1.0 - (missing_cells / max(1, total_req_cells))))
    else:
        req_completeness_ratio = 0.0 if valid_rows_count == 0 else 1.0

    if opt_det_map:
        det_present_ratio = len(present_opt_columns) / len(opt_det_map)
    else:
        det_present_ratio = 1.0

    completeness_score = round(
        100.0
        * (
            w_req * req_completeness_ratio
            + w_valid * valid_rows_ratio
            + w_date * date_continuity_ratio
            + w_det * det_present_ratio
        ),
        2,
    )

    quality_score = round(
        100.0
        * (
            0.40 * valid_rows_ratio
            + 0.35 * req_completeness_ratio
            + 0.25 * ocr_conf_mean
        ),
        2,
    )

    quality_payload = {
        "quality_score": quality_score,
        "completeness_score": completeness_score,
        "valid_rows_count": valid_rows_count,
        "rejected_rows_count": rejected_count,
        "valid_rows_ratio": round(valid_rows_ratio, 4),
        "required_fields_completeness_ratio": round(req_completeness_ratio, 4),
        "missing_fields_ratio": round(1.0 - req_completeness_ratio, 4),
        "ocr_confidence_mean": ocr_conf_mean,
    }

    if persist_quality:
        try:
            existing_q = json.loads(ev.quality_json or "{}")
            if not isinstance(existing_q, dict):
                existing_q = {}
        except Exception:
            existing_q = {}
        existing_q.update(quality_payload)
        ev.quality_json = json.dumps(existing_q, default=str)
        db.commit()

    return {
        "evidence_id": ev.id,
        "case_id": ev.case_id,
        "file_name": ev.original_name,
        "detected_type": ev.detected_type,
        "record_type": rec_type,
        "required_fields": req_fields,
        "missing_field_counts": missing_field_counts,
        "missing_fields": [k for k, cnt in missing_field_counts.items() if cnt > 0],
        "date_range": {
            "min_date": min_date_str,
            "max_date": max_date_str,
            "gap_days_threshold": gap_threshold,
            "gaps": date_gaps,
        },
        "date_range_gaps": date_gaps,
        "disabled_detectors": disabled_detectors,
        "completeness_score": completeness_score,
        "score_formula": DOCUMENTED_COMPLETENESS_FORMULA,
        "quality": quality_payload,
    }


def Path_exists_safe(p: Optional[str]) -> bool:
    if not p:
        return False
    try:
        from pathlib import Path

        return Path(p).exists()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 4. Cross-File Consistency Checks ("Data Quality Findings", Task 4)
# ---------------------------------------------------------------------------

def run_cross_file_consistency_checks(
    db: Session,
    case_id: str,
) -> List[Dict[str, Any]]:
    """
    Task 4: Runs cross-file consistency checks across all evidence in `case_id` and outputs
    "Data Quality Findings" with `severity`, `finding_type`, `reason_code`, `explanation`, and `evidence_ids`:
      1. Closing balance of one bank statement vs opening balance of the next (same account).
      2. Overlapping periods with conflicting values (surfaces Phase 3 `MergeConflict`s and overlapping statements).
      3. Same identifier with different names across files.
      4. Statement owner mismatches (unconfirmed owner or transactions not matching declared owner).
    """
    findings: List[Dict[str, Any]] = []
    ev_files = db.query(EvidenceFile).filter(EvidenceFile.case_id == case_id).all()
    ev_by_name = {e.original_name: e for e in ev_files}

    # 1 & 4. Bank statement balance continuity & statement owner checks
    txns = (
        db.query(Transaction)
        .filter(Transaction.case_id == case_id, Transaction.is_active == True)
        .all()
    )
    txns_by_file: Dict[str, List[Transaction]] = {}
    for t in txns:
        txns_by_file.setdefault(t.source_file, []).append(t)

    # Group statement metadata by owner_account
    statements_by_owner: Dict[str, List[Dict[str, Any]]] = {}

    for ev in ev_files:
        file_txns = txns_by_file.get(ev.original_name, [])
        q_meta = {}
        try:
            q_meta = json.loads(ev.quality_json or "{}")
        except Exception:
            pass

        stmt_meta = q_meta.get("statement_metadata") or {}
        owner_acct = q_meta.get("owner_account") or stmt_meta.get("owner_account")
        open_paise = q_meta.get("opening_balance_paise") if q_meta.get("opening_balance_paise") is not None else stmt_meta.get("opening_balance_paise")
        close_paise = q_meta.get("closing_balance_paise") if q_meta.get("closing_balance_paise") is not None else stmt_meta.get("closing_balance_paise")

        # Also inspect raw_json on transactions if statement metadata was embedded per row
        for ft in file_txns:
            try:
                rj = json.loads(ft.raw_json or "{}")
                if not owner_acct and rj.get("_owner_account"):
                    owner_acct = rj["_owner_account"]
                if open_paise is None and rj.get("_opening_balance_paise") is not None:
                    open_paise = int(rj["_opening_balance_paise"])
                if close_paise is None and rj.get("_closing_balance_paise") is not None:
                    close_paise = int(rj["_closing_balance_paise"])
            except Exception:
                pass

        # Check 4a: Statement flagged as needing owner confirmation or having UNKNOWN accounts
        unknown_cnt = sum(
            1 for ft in file_txns if ft.from_account == "UNKNOWN" or ft.to_account == "UNKNOWN"
        )
        if ev.status == "needs_owner_confirmation" or (
            ev.detected_type == "bank_statement" and unknown_cnt > 0 and not owner_acct
        ):
            findings.append({
                "finding_type": "statement_owner_mismatch",
                "reason_code": "STATEMENT_OWNER_UNCONFIRMED",
                "severity": "high",
                "account": owner_acct,
                "evidence_ids": [ev.id],
                "explanation": (
                    f"Data Quality Finding: bank statement '{ev.original_name}' has {unknown_cnt} transaction(s) "
                    f"with unconfirmed statement owner account."
                ),
            })

        # Check 4b: Declared owner_account does not appear in a majority of the statement's transactions
        if owner_acct and file_txns:
            matching_owner_rows = sum(
                1 for ft in file_txns if ft.from_account == owner_acct or ft.to_account == owner_acct
            )
            if matching_owner_rows < len(file_txns) * 0.5:
                findings.append({
                    "finding_type": "statement_owner_mismatch",
                    "reason_code": "STATEMENT_OWNER_ACCOUNT_MISMATCH",
                    "severity": "high",
                    "account": owner_acct,
                    "evidence_ids": [ev.id],
                    "explanation": (
                        f"Data Quality Finding: declared statement owner account {owner_acct} in "
                        f"'{ev.original_name}' appears in only {matching_owner_rows}/{len(file_txns)} rows."
                    ),
                })

        if file_txns or (owner_acct and open_paise is not None and close_paise is not None):
            dates_in_file = sorted(ft.date_iso for ft in file_txns if ft.date_iso)
            min_d = q_meta.get("period_start") or (dates_in_file[0] if dates_in_file else "0000-00-00")
            max_d = q_meta.get("period_end") or (dates_in_file[-1] if dates_in_file else "9999-99-99")
            if owner_acct:
                statements_by_owner.setdefault(str(owner_acct), []).append({
                    "evidence_id": ev.id,
                    "file_name": ev.original_name,
                    "owner_account": str(owner_acct),
                    "min_date": str(min_d),
                    "max_date": str(max_d),
                    "opening_balance_paise": int(open_paise) if open_paise is not None else None,
                    "closing_balance_paise": int(close_paise) if close_paise is not None else None,
                })

    # Check 1: Closing balance of statement N vs opening balance of statement N+1 (same owner_account)
    for acct, stmts in sorted(statements_by_owner.items()):
        if len(stmts) < 2:
            continue
        stmts_sorted = sorted(stmts, key=lambda x: (x["min_date"], x["max_date"], x["file_name"]))
        for i in range(len(stmts_sorted) - 1):
            s_prev = stmts_sorted[i]
            s_next = stmts_sorted[i + 1]
            c_prev = s_prev["closing_balance_paise"]
            o_next = s_next["opening_balance_paise"]
            if c_prev is not None and o_next is not None and c_prev != o_next:
                diff_paise = o_next - c_prev
                findings.append({
                    "finding_type": "balance_continuity_mismatch",
                    "reason_code": "STATEMENT_BALANCE_CONTINUITY_MISMATCH",
                    "severity": "high",
                    "account": acct,
                    "evidence_ids": [s_prev["evidence_id"], s_next["evidence_id"]],
                    "metrics": {
                        "previous_closing_paise": c_prev,
                        "next_opening_paise": o_next,
                        "difference_paise": diff_paise,
                    },
                    "explanation": (
                        f"Data Quality Finding: for account {acct}, closing balance of '{s_prev['file_name']}' "
                        f"({c_prev} paise) does not match opening balance of subsequent statement "
                        f"'{s_next['file_name']}' ({o_next} paise; difference: {diff_paise} paise)."
                    ),
                })

            # Check 2a: Overlapping statement periods for the same account
            if (
                s_prev["max_date"] != "9999-99-99"
                and s_next["min_date"] != "0000-00-00"
                and s_next["min_date"] <= s_prev["max_date"]
                and s_prev["evidence_id"] != s_next["evidence_id"]
            ):
                findings.append({
                    "finding_type": "overlapping_period",
                    "reason_code": "OVERLAPPING_STATEMENT_PERIODS",
                    "severity": "medium",
                    "account": acct,
                    "evidence_ids": [s_prev["evidence_id"], s_next["evidence_id"]],
                    "explanation": (
                        f"Data Quality Finding: statements '{s_prev['file_name']}' ({s_prev['min_date']} to "
                        f"{s_prev['max_date']}) and '{s_next['file_name']}' ({s_next['min_date']} to "
                        f"{s_next['max_date']}) have overlapping periods for account {acct}."
                    ),
                })

    # Check 2b: Surface open Phase 3 MergeConflicts as cross-file conflicting value findings
    open_conflicts = (
        db.query(MergeConflict)
        .filter(MergeConflict.case_id == case_id, MergeConflict.status == "open")
        .all()
    )
    for mc in open_conflicts:
        c_ids = json.loads(mc.claim_ids_json or "[]")
        claims = db.query(FieldClaim).filter(FieldClaim.id.in_(c_ids)).all() if c_ids else []
        ev_ids = sorted({c.evidence_id for c in claims if c.evidence_id})
        vals = sorted({str(c.value_norm) for c in claims if c.value_norm is not None})
        findings.append({
            "finding_type": "conflicting_overlapping_values",
            "reason_code": "OVERLAPPING_PERIOD_CONFLICT",
            "severity": "medium",
            "conflict_id": mc.id,
            "subject_id": mc.subject_id,
            "field_name": mc.field_name,
            "evidence_ids": ev_ids,
            "explanation": (
                f"Data Quality Finding: conflicting values ({', '.join(vals[:4])}) observed for field "
                f"'{mc.field_name}' on subject {mc.subject_id} across {len(ev_ids)} evidence source(s)."
            ),
        })

    # Check 3: Same identifier with different names across files
    ident_to_names: Dict[str, Dict[str, Set[str]]] = {}
    for t in txns:
        ev_obj = ev_by_name.get(t.source_file)
        ev_id = ev_obj.id if ev_obj else t.source_file
        if t.from_account and t.from_name and t.from_name.strip():
            ident_to_names.setdefault(t.from_account, {}).setdefault(t.from_name.strip().lower(), set()).add(ev_id)
        if t.to_account and t.to_name and t.to_name.strip():
            ident_to_names.setdefault(t.to_account, {}).setdefault(t.to_name.strip().lower(), set()).add(ev_id)

    active_recs = (
        db.query(ExtractionRecord)
        .filter(ExtractionRecord.case_id == case_id, ExtractionRecord.status == "active")
        .all()
    )
    for rec in active_recs:
        try:
            d = json.loads(rec.data_json or "{}")
            ex = json.loads(rec.extra_json or "{}")
            merged = {**ex, **d}
            ident_val = merged.get("phone") or merged.get("account") or merged.get("canonical_id")
            name_val = merged.get("name") or merged.get("subscriber_name") or merged.get("holder_name")
            if ident_val and name_val and str(name_val).strip() and str(ident_val).strip() != str(name_val).strip():
                ident_to_names.setdefault(str(ident_val).strip(), {}).setdefault(str(name_val).strip().lower(), set()).add(rec.evidence_id)
        except Exception:
            pass

    case_entities = db.query(Entity).filter(Entity.case_id == case_id).all()
    entity_row_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for ent in case_entities:
        ref_key = (ent.source_file or "", ent.source_ref or "")
        ev_obj = ev_by_name.get(ent.source_file)
        ev_id = ev_obj.id if ev_obj else ent.source_file
        bucket = entity_row_map.setdefault(ref_key, {"names": set(), "identifiers": set(), "ev_id": ev_id})
        if ent.label == "Person" and ent.display_name:
            bucket["names"].add(ent.display_name.strip())
        elif ent.label in ("Phone", "BankAccount") and ent.canonical_id:
            bucket["identifiers"].add(ent.canonical_id.strip())
    for b in entity_row_map.values():
        for name in b["names"]:
            for ident in b["identifiers"]:
                ident_to_names.setdefault(ident, {}).setdefault(name.lower(), set()).add(b["ev_id"])

    for ident, name_map in sorted(ident_to_names.items()):
        if len(name_map) >= 2:
            ev_union: Set[str] = set()
            for s in name_map.values():
                ev_union.update(s)
            names_sorted = sorted(name_map.keys())
            findings.append({
                "finding_type": "identifier_name_mismatch",
                "reason_code": "IDENTIFIER_NAME_MISMATCH",
                "severity": "medium",
                "identifier": ident,
                "names": names_sorted,
                "evidence_ids": sorted(ev_union),
                "explanation": (
                    f"Data Quality Finding: identifier {ident} appears under {len(names_sorted)} different "
                    f"names ({', '.join(names_sorted[:4])}) across evidence files."
                ),
            })

    return findings


def compute_case_completeness(
    db: Session,
    case_id: str,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Task 3, 4, 5: Produces the case-level completeness & data quality report:
      - Per-evidence completeness & quality scores
      - Aggregated missing field counts per record_type
      - Case-wide date-range gaps per record_type
      - Columns absent that disable detectors
      - Cross-file consistency "Data Quality Findings"
      - Overall case `completeness_score` and documented `score_formula`.
    """
    ev_files = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.case_id == case_id)
        .order_by(EvidenceFile.created_at.asc())
        .all()
    )

    per_file_reports: List[Dict[str, Any]] = []
    missing_by_record_type: Dict[str, Dict[str, int]] = {}
    disabled_detectors_map: Dict[str, Dict[str, str]] = {}
    all_gaps: List[Dict[str, Any]] = []

    for ev in ev_files:
        rep = compute_evidence_completeness(db, ev.id, persist_quality=True)
        per_file_reports.append(rep)
        rt = rep["record_type"]
        rt_bucket = missing_by_record_type.setdefault(rt, {})
        for f_name, cnt in rep["missing_field_counts"].items():
            rt_bucket[f_name] = rt_bucket.get(f_name, 0) + cnt
        for dd in rep["disabled_detectors"]:
            disabled_detectors_map[f"{rt}:{dd['missing_column']}"] = {
                "record_type": rt,
                "missing_column": dd["missing_column"],
                "message": dd["message"],
            }
        for g in rep["date_range"]["gaps"]:
            all_gaps.append({
                "evidence_id": ev.id,
                "file_name": ev.original_name,
                "record_type": rt,
                **g,
            })

    overall_score = (
        round(sum(r["completeness_score"] for r in per_file_reports) / len(per_file_reports), 2)
        if per_file_reports
        else 0.0
    )

    data_quality_findings = run_cross_file_consistency_checks(db, case_id)
    anomaly_report = evaluate_potential_anomalies(
        db=db,
        case_id=case_id,
        current_user=current_user,
        persist_alerts=True,
    )

    return {
        "case_id": case_id,
        "evidence_count": len(per_file_reports),
        "completeness_score": overall_score,
        "score_formula": DOCUMENTED_COMPLETENESS_FORMULA,
        "missing_fields_by_record_type": missing_by_record_type,
        "date_range_gaps": all_gaps,
        "disabled_detectors": list(disabled_detectors_map.values()),
        "data_quality_findings": data_quality_findings,
        "cross_file_consistency": data_quality_findings,
        "potential_anomalies": anomaly_report["flags"],
        "files": per_file_reports,
    }

