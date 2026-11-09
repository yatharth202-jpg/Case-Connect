import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.config import get_defaults, get_merge_config
from backend.app.db.sql import (
    ExtractionRecord,
    RecordSource,
    FieldClaim,
    GoldenField,
    MergeConflict,
    IngestRun,
    SchemaRegistry,
    CallRecord,
    Transaction,
    IPEvent,
    Entity,
    generate_uuid,
)
from backend.app.services.merge.match import (
    assign_occurrence_indices,
    split_known_and_extra_fields,
    KNOWN_FIELDS_BY_RECORD_TYPE,
)
from backend.app.services.merge.resolve import resolve_field_claims
from backend.app.services.graph.builder import rebuild_graph
from backend.app.audit.service import record_audit_log

_CASE_LOCKS_GUARD = threading.Lock()
_CASE_LOCKS: Dict[str, threading.Lock] = {}


class MergeConcurrencyError(RuntimeError):
    """Raised when a concurrent merge/rollback operation is already running for the same case."""
    def __init__(self, case_id: str):
        super().__init__(f"A merge operation is already in progress for case {case_id}")
        self.case_id = case_id
        self.reason_code = "CONCURRENT_MERGE_IN_PROGRESS"


def _get_case_lock(case_id: str) -> threading.Lock:
    with _CASE_LOCKS_GUARD:
        if case_id not in _CASE_LOCKS:
            _CASE_LOCKS[case_id] = threading.Lock()
        return _CASE_LOCKS[case_id]


def get_extractor_version() -> str:
    """Computes a deterministic extractor version string (app version + config hash)."""
    defaults = get_defaults()
    cfg_subset = {
        "extraction": defaults.get("extraction", {}),
        "merge": defaults.get("merge", {}),
    }
    cfg_hash = hashlib.sha256(
        json.dumps(cfg_subset, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:8]
    return f"v2.0.0+{cfg_hash}"


def _subject_type_for_record_type(record_type: str) -> str:
    return "entity" if record_type == "entity" else "record"


def _register_extra_field(db: Session, record_type: str, field_name: str):
    """Registers an unknown/dynamic field in schema_registry."""
    existing = (
        db.query(SchemaRegistry)
        .filter(
            SchemaRegistry.record_type == record_type,
            SchemaRegistry.field_name == field_name,
        )
        .first()
    )
    if existing:
        existing.seen_count += 1
    else:
        db.add(
            SchemaRegistry(
                record_type=record_type,
                field_name=field_name,
                seen_count=1,
                promoted=False,
            )
        )


def _sync_staged_row(
    db: Session,
    ext_rec: ExtractionRecord,
    golden_data: Dict[str, Any],
    source_file_name: str,
    is_active: bool = True,
):
    """
    Creates or updates the corresponding row in the legacy staging tables
    (call_records, transactions, ip_events, entities) so existing graph builder
    and analytics queries read only active, golden-resolved values.
    """
    rtype = ext_rec.record_type
    case_id = ext_rec.case_id
    src_ref = ext_rec.source_ref or "1"

    def _int_val(val: Any, default: int = 0) -> int:
        try:
            return int(float(str(val)))
        except Exception:
            return default

    if rtype == "call":
        caller = str(golden_data.get("caller") or "")
        receiver = str(golden_data.get("receiver") or "")
        if not caller or not receiver:
            return
        staged: Optional[CallRecord] = None
        if ext_rec.staged_id:
            staged = db.query(CallRecord).filter(CallRecord.id == ext_rec.staged_id).first()
        if not staged:
            staged = CallRecord(
                id=generate_uuid(),
                case_id=case_id,
                source_file=source_file_name,
                source_ref=src_ref,
                caller=caller,
                receiver=receiver,
                call_date=str(golden_data.get("call_date") or ""),
                call_time=str(golden_data.get("call_time") or ""),
                datetime_iso=str(golden_data.get("datetime_iso") or ""),
                tz_source=str(golden_data.get("tz_source") or "assumed_local"),
                duration_seconds=_int_val(golden_data.get("duration_seconds"), 0),
                call_type=str(golden_data.get("call_type") or "voice"),
                imei=str(golden_data.get("imei") or "") or None,
                imsi=str(golden_data.get("imsi") or "") or None,
                cell_id=str(golden_data.get("cell_id") or "") or None,
                raw_json=ext_rec.raw_json,
                is_active=is_active,
                fingerprint=f"{ext_rec.natural_key}:{ext_rec.occurrence_idx}",
            )
            db.add(staged)
            db.flush()
            ext_rec.staged_table = "call_records"
            ext_rec.staged_id = staged.id
        else:
            staged.caller = caller
            staged.receiver = receiver
            staged.call_date = str(golden_data.get("call_date") or staged.call_date or "")
            staged.call_time = str(golden_data.get("call_time") or staged.call_time or "")
            staged.datetime_iso = str(golden_data.get("datetime_iso") or staged.datetime_iso or "")
            staged.duration_seconds = _int_val(golden_data.get("duration_seconds"), staged.duration_seconds)
            staged.call_type = str(golden_data.get("call_type") or staged.call_type or "voice")
            if "imei" in golden_data:
                staged.imei = str(golden_data["imei"]) if golden_data["imei"] is not None else None
            if "imsi" in golden_data:
                staged.imsi = str(golden_data["imsi"]) if golden_data["imsi"] is not None else None
            if "cell_id" in golden_data:
                staged.cell_id = str(golden_data["cell_id"]) if golden_data["cell_id"] is not None else None
            staged.is_active = is_active

    elif rtype == "transaction":
        from_acc = str(golden_data.get("from_account") or golden_data.get("account") or "")
        to_acc = str(golden_data.get("to_account") or "COUNTERPARTY_UNKNOWN")
        amt_paise = _int_val(golden_data.get("amount_paise"), 0)
        if not from_acc or amt_paise == 0:
            return
        staged_txn: Optional[Transaction] = None
        if ext_rec.staged_id:
            staged_txn = db.query(Transaction).filter(Transaction.id == ext_rec.staged_id).first()
        if not staged_txn:
            staged_txn = Transaction(
                id=generate_uuid(),
                case_id=case_id,
                source_file=source_file_name,
                source_ref=src_ref,
                txn_id=str(golden_data.get("txn_id") or f"TXN-{ext_rec.occurrence_idx}"),
                from_account=from_acc,
                to_account=to_acc,
                from_name=str(golden_data.get("from_name")) if golden_data.get("from_name") else None,
                to_name=str(golden_data.get("to_name")) if golden_data.get("to_name") else None,
                amount_paise=abs(amt_paise),
                date_iso=str(golden_data.get("date_iso") or ""),
                tz_source=str(golden_data.get("tz_source") or "assumed_local"),
                reference=str(golden_data.get("reference") or golden_data.get("narration") or "") or None,
                direction=str(golden_data.get("direction") or "transfer"),
                raw_json=ext_rec.raw_json,
                is_active=is_active,
                fingerprint=f"{ext_rec.natural_key}:{ext_rec.occurrence_idx}",
            )
            db.add(staged_txn)
            db.flush()
            ext_rec.staged_table = "transactions"
            ext_rec.staged_id = staged_txn.id
        else:
            staged_txn.from_account = from_acc
            staged_txn.to_account = to_acc
            if "from_name" in golden_data:
                staged_txn.from_name = str(golden_data["from_name"]) if golden_data["from_name"] else None
            if "to_name" in golden_data:
                staged_txn.to_name = str(golden_data["to_name"]) if golden_data["to_name"] else None
            staged_txn.amount_paise = abs(amt_paise)
            staged_txn.date_iso = str(golden_data.get("date_iso") or staged_txn.date_iso or "")
            if "reference" in golden_data or "narration" in golden_data:
                staged_txn.reference = str(golden_data.get("reference") or golden_data.get("narration") or "") or None
            if "direction" in golden_data:
                staged_txn.direction = str(golden_data["direction"])
            staged_txn.is_active = is_active

    elif rtype == "ip_event":
        ident = str(golden_data.get("identifier") or "")
        ip_addr = str(golden_data.get("ip_address") or "")
        if not ident or not ip_addr:
            return
        staged_ip: Optional[IPEvent] = None
        if ext_rec.staged_id:
            staged_ip = db.query(IPEvent).filter(IPEvent.id == ext_rec.staged_id).first()
        if not staged_ip:
            staged_ip = IPEvent(
                id=generate_uuid(),
                case_id=case_id,
                source_file=source_file_name,
                source_ref=src_ref,
                identifier=ident,
                ip_address=ip_addr,
                datetime_iso=str(golden_data.get("datetime_iso") or ""),
                tz_source=str(golden_data.get("tz_source") or "assumed_local"),
                raw_json=ext_rec.raw_json,
                is_active=is_active,
            )
            db.add(staged_ip)
            db.flush()
            ext_rec.staged_table = "ip_events"
            ext_rec.staged_id = staged_ip.id
        else:
            staged_ip.identifier = ident
            staged_ip.ip_address = ip_addr
            staged_ip.datetime_iso = str(golden_data.get("datetime_iso") or staged_ip.datetime_iso or "")
            staged_ip.is_active = is_active

    elif rtype == "entity":
        label = str(golden_data.get("label") or golden_data.get("entity_type") or "Entity")
        canon_id = str(golden_data.get("canonical_id") or golden_data.get("normalized_value") or "")
        disp = str(golden_data.get("display_name") or canon_id)
        if not canon_id:
            return
        staged_ent: Optional[Entity] = None
        if ext_rec.staged_id:
            staged_ent = db.query(Entity).filter(Entity.id == ext_rec.staged_id).first()
        if not staged_ent:
            staged_ent = Entity(
                id=generate_uuid(),
                case_id=case_id,
                label=label,
                canonical_id=canon_id,
                display_name=disp,
                properties_json=json.dumps(golden_data, default=str),
                source_file=source_file_name,
                source_ref=src_ref,
                method=ext_rec.method,
                confidence=ext_rec.confidence,
                is_active=is_active,
            )
            db.add(staged_ent)
            db.flush()
            ext_rec.staged_table = "entities"
            ext_rec.staged_id = staged_ent.id
        else:
            staged_ent.display_name = disp
            staged_ent.properties_json = json.dumps(golden_data, default=str)
            staged_ent.confidence = ext_rec.confidence
            staged_ent.is_active = is_active


def _recompute_record_golden_state(
    db: Session,
    ext_rec: ExtractionRecord,
    source_file_name: str,
) -> Dict[str, Any]:
    """
    Recomputes golden_fields, merge_conflicts, data_json, extra_json, and staged table row
    for a single ExtractionRecord from all its current claims.
    Returns summary of changes on this record: {updated_fields, conflict_fields, notices}.
    """
    subject_type = _subject_type_for_record_type(ext_rec.record_type)
    subject_id = ext_rec.id

    all_claims = (
        db.query(FieldClaim)
        .filter(
            FieldClaim.subject_type == subject_type,
            FieldClaim.subject_id == subject_id,
        )
        .order_by(FieldClaim.observed_at.asc(), FieldClaim.id.asc())
        .all()
    )

    active_claims = [c for c in all_claims if c.status == "active"]
    if not active_claims:
        ext_rec.status = "retracted"
        # Deactivate linked staged row
        if ext_rec.staged_id and ext_rec.staged_table:
            model_map = {
                "call_records": CallRecord,
                "transactions": Transaction,
                "ip_events": IPEvent,
                "entities": Entity,
            }
            m_cls = model_map.get(ext_rec.staged_table)
            if m_cls:
                s_row = db.query(m_cls).filter(m_cls.id == ext_rec.staged_id).first()
                if s_row:
                    s_row.is_active = False

        # Dismiss any open conflicts on this retracted record
        open_confs = (
            db.query(MergeConflict)
            .filter(
                MergeConflict.subject_type == subject_type,
                MergeConflict.subject_id == subject_id,
                MergeConflict.status == "open",
            )
            .all()
        )
        for oc in open_confs:
            oc.status = "dismissed"
            oc.reason_code = "RECORD_RETRACTED"

        return {"updated_fields": [], "conflict_fields": [], "notices": [], "retracted": True}

    ext_rec.status = "active"
    claims_by_field: Dict[str, List[FieldClaim]] = {}
    for c in all_claims:
        claims_by_field.setdefault(c.field_name, []).append(c)

    known_set = KNOWN_FIELDS_BY_RECORD_TYPE.get(ext_rec.record_type, set())
    new_data_dict: Dict[str, Any] = {}
    new_extra_dict: Dict[str, Any] = {}
    updated_fields: List[str] = []
    conflict_fields: List[str] = []
    notices: List[Dict[str, Any]] = []
    effective_confidences: List[float] = []

    for fname, f_claims in claims_by_field.items():
        golden_row = (
            db.query(GoldenField)
            .filter(
                GoldenField.subject_type == subject_type,
                GoldenField.subject_id == subject_id,
                GoldenField.field_name == fname,
            )
            .first()
        )

        curr_golden_dict = None
        prev_selected_val = None
        if golden_row:
            prev_claim = next((c for c in f_claims if c.id == golden_row.selected_claim_id), None)
            prev_selected_val = prev_claim.value_norm if prev_claim else None
            curr_golden_dict = {
                "selected_claim_id": golden_row.selected_claim_id,
                "selected_by": golden_row.selected_by,
                "locked": golden_row.locked,
                "reason_code": golden_row.reason_code,
            }

        claim_dicts = [
            {
                "id": c.id,
                "evidence_id": c.evidence_id,
                "value_norm": c.value_norm,
                "value_raw": c.value_raw,
                "source_kind": c.source_kind,
                "method": c.method,
                "confidence": c.confidence,
                "validator_ok": c.validator_ok,
                "status": c.status,
                "observed_at": c.observed_at.isoformat() if c.observed_at else "",
            }
            for c in f_claims
        ]

        res = resolve_field_claims(claim_dicts, current_golden=curr_golden_dict)
        if res["notice"]:
            notices.append({"field_name": fname, "notice": res["notice"]})

        if res["selected_claim_id"] is None:
            # All claims for this specific field were retracted
            if golden_row:
                golden_row.selected_claim_id = None
                golden_row.reason_code = "NO_ACTIVE_CLAIMS"
                golden_row.updated_at = datetime.now(timezone.utc)
            open_c = (
                db.query(MergeConflict)
                .filter(
                    MergeConflict.subject_type == subject_type,
                    MergeConflict.subject_id == subject_id,
                    MergeConflict.field_name == fname,
                    MergeConflict.status == "open",
                )
                .first()
            )
            if open_c:
                open_c.status = "dismissed"
            continue

        effective_confidences.append(res["effective_confidence"])

        if golden_row is None:
            golden_row = GoldenField(
                subject_type=subject_type,
                subject_id=subject_id,
                field_name=fname,
                selected_claim_id=res["selected_claim_id"],
                selected_by=res["selected_by"],
                locked=res["locked"],
                reason_code=res["reason_code"],
                updated_at=datetime.now(timezone.utc),
            )
            db.add(golden_row)
        else:
            if prev_selected_val is not None and str(prev_selected_val) != str(res["selected_value"]):
                updated_fields.append(fname)
            if golden_row.selected_claim_id != res["selected_claim_id"] or golden_row.reason_code != res["reason_code"]:
                golden_row.selected_claim_id = res["selected_claim_id"]
                golden_row.selected_by = res["selected_by"]
                golden_row.locked = res["locked"]
                golden_row.reason_code = res["reason_code"]
                golden_row.updated_at = datetime.now(timezone.utc)

        # Manage MergeConflict rows
        open_conf = (
            db.query(MergeConflict)
            .filter(
                MergeConflict.subject_type == subject_type,
                MergeConflict.subject_id == subject_id,
                MergeConflict.field_name == fname,
                MergeConflict.status == "open",
            )
            .first()
        )
        if res["has_conflict"]:
            conflict_fields.append(fname)
            if open_conf is None:
                open_conf = MergeConflict(
                    case_id=ext_rec.case_id,
                    subject_type=subject_type,
                    subject_id=subject_id,
                    field_name=fname,
                    claim_ids_json=json.dumps(res["conflicting_claim_ids"]),
                    status="open",
                    reason_code=res["reason_code"],
                )
                db.add(open_conf)
            else:
                open_conf.claim_ids_json = json.dumps(res["conflicting_claim_ids"])
                open_conf.reason_code = res["reason_code"]
        elif open_conf is not None:
            open_conf.status = "resolved"
            open_conf.resolution_claim_id = res["selected_claim_id"]
            open_conf.resolved_at = datetime.now(timezone.utc)
            open_conf.reason_code = res["reason_code"]

        # Deserialize integer if appropriate for amount_paise / duration_seconds
        val_out: Any = res["selected_value"]
        if fname in ("amount_paise", "duration_seconds", "balance_after_paise"):
            try:
                val_out = int(float(str(val_out)))
            except Exception:
                pass

        if fname in known_set:
            new_data_dict[fname] = val_out
        else:
            new_extra_dict[fname] = val_out

    ext_rec.data_json = json.dumps(new_data_dict, sort_keys=True, default=str)
    ext_rec.extra_json = json.dumps(new_extra_dict, sort_keys=True, default=str)
    if effective_confidences:
        ext_rec.confidence = round(sum(effective_confidences) / len(effective_confidences), 4)

    _sync_staged_row(
        db=db,
        ext_rec=ext_rec,
        golden_data={**new_data_dict, **new_extra_dict},
        source_file_name=source_file_name,
        is_active=True,
    )

    return {
        "updated_fields": updated_fields,
        "conflict_fields": conflict_fields,
        "notices": notices,
        "retracted": False,
    }


def apply_evidence_merge(
    db: Session,
    case_id: str,
    evidence_id: str,
    record_type: str,
    records: List[Dict[str, Any]],
    user_id: str,
    source_kind: str = "structured_file",
    method: str = "structured",
    default_confidence: float = 1.0,
    job_id: Optional[str] = None,
    preview: bool = False,
    source_file_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes the deterministic Merge Engine for a batch of records from an evidence file.
    - Guarded by a per-case lock (rejects concurrent applies with MergeConcurrencyError).
    - When preview=True, executes the full algorithm inside a savepoint and rolls back at the end,
      returning exact counts and preview changes without mutating SQLite or the graph.
    - When preview=False, writes SQLite in one transaction, calls rebuild_graph(db, case_id),
      and appends to audit_log.
    """
    case_lock = _get_case_lock(case_id)
    if not case_lock.acquire(blocking=False):
        raise MergeConcurrencyError(case_id)

    try:
        ext_version = get_extractor_version()
        run_id = generate_uuid()
        started_at = datetime.now(timezone.utc)
        src_file = source_file_name or evidence_id

        savepoint = db.begin_nested() if preview else None

        counts = {
            "new": 0,
            "same": 0,
            "updated": 0,
            "new_fields": 0,
            "conflicts": 0,
            "rejected": 0,
        }
        changes_preview: List[Dict[str, Any]] = []

        indexed_batch = assign_occurrence_indices(
            case_id=case_id,
            record_type=record_type,
            records=records,
            evidence_id=evidence_id,
        )

        subject_type = _subject_type_for_record_type(record_type)

        for item in indexed_batch:
            rec_dict = item["record"]
            nat_key = item["natural_key"]
            occ_idx = item["occurrence_idx"]
            src_ref = str(item["source_ref"])

            known_fields, extra_fields = split_known_and_extra_fields(record_type, rec_dict)
            all_incoming_fields = {**known_fields, **extra_fields}
            if not all_incoming_fields:
                counts["rejected"] += 1
                continue

            rec_conf = float(rec_dict.get("_confidence", default_confidence))
            rec_method = str(rec_dict.get("_method", method))
            rec_source_kind = str(rec_dict.get("_source_kind", source_kind))
            rec_page_no = rec_dict.get("_page_no")
            rec_bbox = json.dumps(rec_dict["_bbox"]) if "_bbox" in rec_dict and rec_dict["_bbox"] is not None else None
            rec_ts_sec = float(rec_dict["_timestamp_sec"]) if "_timestamp_sec" in rec_dict and rec_dict["_timestamp_sec"] is not None else None
            raw_payload = rec_dict.get("_raw") or {k: v for k, v in rec_dict.items() if not k.startswith("_")}
            validator_map: Dict[str, bool] = rec_dict.get("_validator_ok_map") or {}

            # Register any unknown/extra fields in schema_registry
            for ef_name in extra_fields:
                _register_extra_field(db, record_type, ef_name)

            # Lookup existing active ExtractionRecord for (case_id, record_type, natural_key, occurrence_idx)
            existing_rec = (
                db.query(ExtractionRecord)
                .filter(
                    ExtractionRecord.case_id == case_id,
                    ExtractionRecord.record_type == record_type,
                    ExtractionRecord.natural_key == nat_key,
                    ExtractionRecord.occurrence_idx == occ_idx,
                    ExtractionRecord.status == "active",
                )
                .first()
            )

            if existing_rec is None:
                # 1. NEW RECORD
                new_rec = ExtractionRecord(
                    id=generate_uuid(),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    record_type=record_type,
                    natural_key=nat_key,
                    occurrence_idx=occ_idx,
                    data_json=json.dumps(known_fields, sort_keys=True, default=str),
                    extra_json=json.dumps(extra_fields, sort_keys=True, default=str),
                    raw_json=json.dumps(raw_payload, sort_keys=True, default=str),
                    source_ref=src_ref,
                    page_no=int(rec_page_no) if rec_page_no is not None else None,
                    bbox_json=rec_bbox,
                    timestamp_sec=rec_ts_sec,
                    method=rec_method,
                    source_kind=rec_source_kind,
                    confidence=rec_conf,
                    extractor_version=ext_version,
                    status="active",
                    first_seen_run_id=run_id,
                    last_seen_run_id=run_id,
                )
                db.add(new_rec)
                db.flush()

                db.add(
                    RecordSource(
                        record_id=new_rec.id,
                        evidence_id=evidence_id,
                        source_ref=src_ref,
                    )
                )

                for fname, fval in all_incoming_fields.items():
                    v_ok = bool(validator_map.get(fname, True))
                    claim = FieldClaim(
                        id=generate_uuid(),
                        case_id=case_id,
                        subject_type=subject_type,
                        subject_id=new_rec.id,
                        field_name=fname,
                        value_norm=str(fval),
                        value_raw=str(raw_payload.get(fname, fval)),
                        evidence_id=evidence_id,
                        source_ref=src_ref,
                        source_kind=rec_source_kind,
                        method=rec_method,
                        confidence=rec_conf,
                        validator_ok=v_ok,
                        status="active",
                        run_id=run_id,
                    )
                    db.add(claim)

                db.flush()
                _recompute_record_golden_state(db, new_rec, src_file)
                counts["new"] += 1
                changes_preview.append({
                    "action": "new",
                    "record_id": new_rec.id,
                    "record_type": record_type,
                    "natural_key": nat_key,
                    "occurrence_idx": occ_idx,
                    "fields": all_incoming_fields,
                })
                continue

            # 2. EXISTING RECORD FOUND -> Compare fields and claims
            existing_claims = (
                db.query(FieldClaim)
                .filter(
                    FieldClaim.subject_type == subject_type,
                    FieldClaim.subject_id == existing_rec.id,
                    FieldClaim.status == "active",
                )
                .all()
            )
            existing_fields_set = {c.field_name for c in existing_claims}

            # Check if this exact evidence_id already has identical active claims for all incoming fields
            same_ev_claims = {
                c.field_name: c
                for c in existing_claims
                if c.evidence_id == evidence_id
            }
            if same_ev_claims and all(
                fname in same_ev_claims
                and str(same_ev_claims[fname].value_norm) == str(fval)
                and same_ev_claims[fname].source_kind == rec_source_kind
                and abs(float(same_ev_claims[fname].confidence) - rec_conf) < 1e-6
                for fname, fval in all_incoming_fields.items()
            ):
                # Exact idempotent re-ingest of the same evidence file -> zero mutations
                counts["same"] += 1
                continue

            # Ensure RecordSource row exists for (existing_rec.id, evidence_id)
            has_src = (
                db.query(RecordSource)
                .filter(
                    RecordSource.record_id == existing_rec.id,
                    RecordSource.evidence_id == evidence_id,
                )
                .first()
            )
            if not has_src:
                db.add(
                    RecordSource(
                        record_id=existing_rec.id,
                        evidence_id=evidence_id,
                        source_ref=src_ref,
                    )
                )

            existing_rec.last_seen_run_id = run_id

            added_new_field = False
            had_value_diff = False

            for fname, fval in all_incoming_fields.items():
                v_ok = bool(validator_map.get(fname, True))
                if fname not in existing_fields_set:
                    added_new_field = True
                else:
                    field_existing_vals = {
                        str(c.value_norm) for c in existing_claims if c.field_name == fname
                    }
                    if str(fval) not in field_existing_vals:
                        had_value_diff = True

                # Check if this evidence_id already had a claim on this field
                ev_claim = same_ev_claims.get(fname)
                if ev_claim is not None:
                    ev_claim.value_norm = str(fval)
                    ev_claim.value_raw = str(raw_payload.get(fname, fval))
                    ev_claim.source_kind = rec_source_kind
                    ev_claim.method = rec_method
                    ev_claim.confidence = rec_conf
                    ev_claim.validator_ok = v_ok
                    ev_claim.run_id = run_id
                else:
                    db.add(
                        FieldClaim(
                            id=generate_uuid(),
                            case_id=case_id,
                            subject_type=subject_type,
                            subject_id=existing_rec.id,
                            field_name=fname,
                            value_norm=str(fval),
                            value_raw=str(raw_payload.get(fname, fval)),
                            evidence_id=evidence_id,
                            source_ref=src_ref,
                            source_kind=rec_source_kind,
                            method=rec_method,
                            confidence=rec_conf,
                            validator_ok=v_ok,
                            status="active",
                            run_id=run_id,
                        )
                    )

            db.flush()
            recomp = _recompute_record_golden_state(db, existing_rec, src_file)

            if recomp["conflict_fields"]:
                counts["conflicts"] += 1
                action_label = "conflict"
            elif added_new_field and not had_value_diff:
                counts["new_fields"] += 1
                action_label = "new_fields"
            elif recomp["updated_fields"] or had_value_diff:
                if added_new_field:
                    counts["new_fields"] += 1
                counts["updated"] += 1
                action_label = "updated"
            else:
                counts["same"] += 1
                action_label = "same"

            changes_preview.append({
                "action": action_label,
                "record_id": existing_rec.id,
                "record_type": record_type,
                "natural_key": nat_key,
                "occurrence_idx": occ_idx,
                "updated_fields": recomp["updated_fields"],
                "conflict_fields": recomp["conflict_fields"],
                "notices": recomp["notices"],
            })

        finished_at = datetime.now(timezone.utc)

        if preview:
            if savepoint is not None:
                savepoint.rollback()
            return {
                "run_id": run_id,
                "mode": "preview",
                "case_id": case_id,
                "evidence_id": evidence_id,
                "extractor_version": ext_version,
                "counts": counts,
                "changes": changes_preview[:50],
            }

        run_row = IngestRun(
            id=run_id,
            case_id=case_id,
            evidence_id=evidence_id,
            job_id=job_id,
            mode="apply",
            counts_json=json.dumps(counts),
            status="done",
            extractor_version=ext_version,
            started_at=started_at,
            finished_at=finished_at,
        )
        db.add(run_row)
        db.commit()

        # Rebuild graph from authoritative SQLite active records
        rebuild_graph(db, case_id)

        # Append to cryptographic audit log chain
        record_audit_log(
            db=db,
            user_id=user_id,
            action="merge_apply",
            case_id=case_id,
            object_type="evidence_file",
            object_id=evidence_id,
            details={
                "run_id": run_id,
                "record_type": record_type,
                "counts": counts,
                "extractor_version": ext_version,
            },
        )

        return {
            "run_id": run_id,
            "mode": "apply",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "extractor_version": ext_version,
            "counts": counts,
            "changes": changes_preview[:50],
        }
    finally:
        case_lock.release()


def resolve_conflict_by_officer(
    db: Session,
    conflict_id: str,
    selected_claim_id: str,
    officer_id: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Officer resolves an open MergeConflict by choosing a claim:
    - Sets golden_fields.selected_by = 'officer', locked = True
    - Marks MergeConflict status = 'resolved'
    - Updates ExtractionRecord data_json/extra_json and staged row
    - Rebuilds case graph and writes to audit_log.
    """
    conflict = db.query(MergeConflict).filter(MergeConflict.id == conflict_id).first()
    if not conflict:
        raise ValueError(f"Merge conflict {conflict_id} not found")

    claim = (
        db.query(FieldClaim)
        .filter(
            FieldClaim.id == selected_claim_id,
            FieldClaim.subject_type == conflict.subject_type,
            FieldClaim.subject_id == conflict.subject_id,
            FieldClaim.field_name == conflict.field_name,
        )
        .first()
    )
    if not claim:
        raise ValueError(f"Claim {selected_claim_id} does not belong to conflict {conflict_id}")

    now_utc = datetime.now(timezone.utc)
    conflict.status = "resolved"
    conflict.resolution_claim_id = claim.id
    conflict.resolved_by = officer_id
    conflict.resolved_at = now_utc
    conflict.reason_code = "OFFICER_RESOLUTION"

    golden = (
        db.query(GoldenField)
        .filter(
            GoldenField.subject_type == conflict.subject_type,
            GoldenField.subject_id == conflict.subject_id,
            GoldenField.field_name == conflict.field_name,
        )
        .first()
    )
    if golden is None:
        golden = GoldenField(
            subject_type=conflict.subject_type,
            subject_id=conflict.subject_id,
            field_name=conflict.field_name,
            selected_claim_id=claim.id,
            selected_by="officer",
            locked=True,
            reason_code="OFFICER_RESOLUTION",
            updated_at=now_utc,
        )
        db.add(golden)
    else:
        golden.selected_claim_id = claim.id
        golden.selected_by = "officer"
        golden.locked = True
        golden.reason_code = "OFFICER_RESOLUTION"
        golden.updated_at = now_utc

    db.flush()

    ext_rec = db.query(ExtractionRecord).filter(ExtractionRecord.id == conflict.subject_id).first()
    if ext_rec:
        _recompute_record_golden_state(db, ext_rec, ext_rec.evidence_id)

    db.commit()
    rebuild_graph(db, conflict.case_id)

    record_audit_log(
        db=db,
        user_id=officer_id,
        action="merge_conflict_resolve",
        case_id=conflict.case_id,
        object_type="merge_conflict",
        object_id=conflict.id,
        details={
            "subject_id": conflict.subject_id,
            "field_name": conflict.field_name,
            "selected_claim_id": claim.id,
            "selected_value": claim.value_norm,
            "note": note,
        },
    )

    return {
        "conflict_id": conflict.id,
        "status": conflict.status,
        "subject_id": conflict.subject_id,
        "field_name": conflict.field_name,
        "selected_claim_id": claim.id,
        "selected_value": claim.value_norm,
        "locked": True,
    }


def rollback_evidence_merge(
    db: Session,
    case_id: str,
    evidence_id: str,
    user_id: str,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rolls back an evidence file without deleting any historical rows or touching other files' data:
    - Marks all FieldClaims from `evidence_id` as `status = 'retracted'`
    - Recomputes golden_fields from remaining active claims across other files
    - Marks ExtractionRecords with zero remaining active claims as `status = 'retracted'`
      and sets their staged row `is_active = False`
    - Logs to IngestRun and audit_log, then calls rebuild_graph(db, case_id).
    """
    case_lock = _get_case_lock(case_id)
    if not case_lock.acquire(blocking=False):
        raise MergeConcurrencyError(case_id)

    try:
        started_at = datetime.now(timezone.utc)
        ext_version = get_extractor_version()

        claims_to_retract = (
            db.query(FieldClaim)
            .filter(
                FieldClaim.case_id == case_id,
                FieldClaim.evidence_id == evidence_id,
                FieldClaim.status == "active",
            )
            .all()
        )

        affected_record_ids = sorted({c.subject_id for c in claims_to_retract})
        for c in claims_to_retract:
            c.status = "retracted"

        # Remove active RecordSource links for this evidence file
        db.query(RecordSource).filter(RecordSource.evidence_id == evidence_id).delete()
        db.flush()

        records_retracted = 0
        records_restored = 0

        for rid in affected_record_ids:
            ext_rec = db.query(ExtractionRecord).filter(ExtractionRecord.id == rid).first()
            if not ext_rec:
                continue
            recomp = _recompute_record_golden_state(db, ext_rec, ext_rec.evidence_id)
            if recomp["retracted"]:
                records_retracted += 1
            else:
                records_restored += 1

        counts = {
            "claims_retracted": len(claims_to_retract),
            "records_retracted": records_retracted,
            "records_restored_to_prior_evidence": records_restored,
        }

        run_id = generate_uuid()
        run_row = IngestRun(
            id=run_id,
            case_id=case_id,
            evidence_id=evidence_id,
            job_id=job_id,
            mode="rollback",
            counts_json=json.dumps(counts),
            status="done",
            extractor_version=ext_version,
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )
        db.add(run_row)
        db.commit()

        rebuild_graph(db, case_id)

        record_audit_log(
            db=db,
            user_id=user_id,
            action="merge_rollback",
            case_id=case_id,
            object_type="evidence_file",
            object_id=evidence_id,
            details={
                "run_id": run_id,
                "counts": counts,
            },
        )

        return {
            "run_id": run_id,
            "mode": "rollback",
            "case_id": case_id,
            "evidence_id": evidence_id,
            "counts": counts,
        }
    finally:
        case_lock.release()

