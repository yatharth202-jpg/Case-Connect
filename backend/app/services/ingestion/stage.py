import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    CallRecord, Transaction, IPEvent, Entity, RejectedRow,
    EvidenceFile, ColumnMapping, RawRow, RawSheet
)
from backend.app.services.ingestion.raw_store import (
    capture_raw_file_lossless,
    reconcile_evidence_file,
)
from backend.app.config import get_extraction_config
from backend.app.services.ingestion.readers import (
    read_tabular_file_detailed,
    iter_tabular_chunks,
)
from backend.app.services.ingestion.detect import detect_file_type
from backend.app.services.ingestion.mapping import suggest_column_mappings
from backend.app.services.ingestion.normalize import (
    normalize_phone, normalize_account, normalize_amount,
    normalize_datetime, normalize_datetime_detailed, infer_column_dayfirst,
    normalize_duration, normalize_name,
    normalize_vehicle, normalize_email, normalize_ip
)
from backend.app.services.ingestion.statement import (
    parse_statement_narration,
    extract_statement_owner_metadata,
)
from backend.app.audit.service import record_audit_log


def compute_row_fingerprint(case_id: str, payload_dict: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 fingerprint for deduplicating identical records."""
    norm_str = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{case_id}|{norm_str}".encode("utf-8")).hexdigest()


def preview_normalized_rows(
    file_type: str,
    records: List[Dict[str, Any]],
    column_mapping: Dict[str, str],
    statement_account: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Produces a normalized preview of the first N rows using the candidate column_mapping,
    so officers can inspect normalized phones, integer paise amounts, and UTC/IST dates before confirming.
    """
    sample = records[:limit]
    if not sample:
        return []

    canon_to_raw: Dict[str, List[str]] = {}
    for raw_col, canon_field in column_mapping.items():
        if canon_field and canon_field != "ignore":
            canon_to_raw.setdefault(canon_field, []).append(raw_col)

    date_raw_headers = canon_to_raw.get("datetime", []) + canon_to_raw.get("date", [])
    column_date_samples = []
    for r_row in sample:
        for dh in date_raw_headers:
            dv = r_row.get(dh)
            if dv is not None and str(dv).strip():
                column_date_samples.append(dv)
                break
    inferred_dayfirst, _ = infer_column_dayfirst(column_date_samples)

    normalized_out: List[Dict[str, Any]] = []
    for idx, raw_row in enumerate(sample, 1):
        def get_val(canon_name: str):
            for h in canon_to_raw.get(canon_name, []):
                v = raw_row.get(h)
                if v is not None and str(v).strip():
                    return v
            return None

        if file_type == "cdr":
            p_caller = normalize_phone(get_val("caller"))
            p_receiver = normalize_phone(get_val("receiver"))
            dt_res = normalize_datetime_detailed(get_val("datetime") or get_val("date"), get_val("time"), dayfirst=inferred_dayfirst)
            normalized_out.append({
                "row_number": idx,
                "caller": p_caller["number"] if p_caller else None,
                "receiver": p_receiver["number"] if p_receiver else None,
                "datetime_utc": dt_res["meta"]["utc_iso"] if dt_res["ok"] else None,
                "local_date": dt_res["meta"]["local_date"] if dt_res["ok"] else None,
                "duration_seconds": normalize_duration(get_val("duration")),
                "valid": bool(p_caller and p_receiver),
            })
        elif file_type == "bank_transactions":
            from_acc = normalize_account(get_val("from_account"))
            to_acc = normalize_account(get_val("to_account"))
            amt_paise = normalize_amount(get_val("amount") or get_val("debit") or get_val("credit"))
            dt_res = normalize_datetime_detailed(get_val("datetime") or get_val("date"), get_val("time"), dayfirst=inferred_dayfirst)
            normalized_out.append({
                "row_number": idx,
                "from_account": from_acc,
                "to_account": to_acc,
                "amount_paise": abs(amt_paise) if amt_paise is not None else None,
                "date_iso": dt_res["meta"]["local_date"] if dt_res["ok"] else None,
                "valid": bool(from_acc and to_acc and amt_paise),
            })
        elif file_type == "bank_statement":
            debit_amt = normalize_amount(get_val("debit"))
            credit_amt = normalize_amount(get_val("credit"))
            generic_amt = normalize_amount(get_val("amount"))
            amt_paise = debit_amt or credit_amt or (abs(generic_amt) if generic_amt else None)
            dt_res = normalize_datetime_detailed(get_val("date"), dayfirst=inferred_dayfirst)
            normalized_out.append({
                "row_number": idx,
                "statement_account": normalize_account(statement_account or get_val("statement_account")),
                "narration": get_val("narration") or get_val("reference"),
                "amount_paise": amt_paise,
                "date_iso": dt_res["meta"]["local_date"] if dt_res["ok"] else None,
                "valid": bool(amt_paise),
            })
        else:
            normalized_out.append({"row_number": idx, "raw": raw_row, "valid": True})

    return normalized_out


def stage_evidence_file(
    db: Session,
    evidence_id: str,
    user_id: str,
    file_type: str,
    column_mapping: Dict[str, str],
    statement_account: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    chunk_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Executes end-to-end staging: reads raw file (supporting multi-section/multi-sheet & chunked streaming),
    normalizes fields, records every rejected row with a reason_code, deduplicates by fingerprint,
    and stages into SQLite.
    For single-account bank statements without an identified owner account, enters
    `needs_owner_confirmation` and blocks edge creation until confirmed by an officer.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise ValueError(f"Evidence file {evidence_id} not found")

    file_path = Path(ev.stored_path)
    cfg = get_extraction_config()
    effective_chunk_size = chunk_size or int(cfg.get("table", {}).get("chunk_size_rows", 5000))

    # Clear prior rejected rows for this evidence file on re-ingest to keep rejection audit exact
    db.query(RejectedRow).filter(RejectedRow.evidence_id == ev.id).delete()
    db.flush()

    # Phase 1: Lossless Raw Store Capture before any parsing or validation
    raw_capture_res = capture_raw_file_lossless(
        db=db,
        evidence_file_id=ev.id,
        file_path=file_path,
        chunk_size=effective_chunk_size,
    )
    raw_row_lookup = raw_capture_res.get("raw_row_lookup", {})

    detailed = read_tabular_file_detailed(file_path)
    records = detailed["records"]
    headers = detailed["headers"]
    banners = detailed["banner_rows"]
    file_meta = detailed.get("file_metadata", {})

    # Resolve bank statement owner account (explicit param -> banner metadata -> column value)
    owner_meta = file_meta.get("statement_owner") or extract_statement_owner_metadata(banners, headers, records)
    if file_type == "bank_statement":
        resolved_stmt_acct = normalize_account(statement_account) or owner_meta.get("account_number")
        if not resolved_stmt_acct:
            # Check if statement_account is mapped in column_mapping and present in rows
            stmt_cols = [raw_c for raw_c, can_f in column_mapping.items() if can_f == "statement_account"]
            for r in records[:25]:
                for sc in stmt_cols:
                    cand = normalize_account(r.get(sc))
                    if cand:
                        resolved_stmt_acct = cand
                        break
                if resolved_stmt_acct:
                    break

        if not resolved_stmt_acct:
            ev.status = "needs_owner_confirmation"
            ev.detected_type = "bank_statement"
            db.commit()

            record_audit_log(
                db=db,
                user_id=user_id,
                action="ingest_blocked_owner_unconfirmed",
                case_id=ev.case_id,
                object_type="evidence_file",
                object_id=ev.id,
                details={
                    "file_type": file_type,
                    "reason_code": "NEEDS_OWNER_CONFIRMATION",
                    "rows_read": len(records),
                },
            )
            return {
                "evidence_id": ev.id,
                "status": "needs_owner_confirmation",
                "needs_owner_confirmation": True,
                "reason_code": "NEEDS_OWNER_CONFIRMATION",
                "file_type": file_type,
                "rows_read": len(records),
                "rows_ingested": 0,
                "rows_rejected": 0,
                "duplicates_skipped": 0,
                "rejections_by_reason": {},
                "distinct_phones": 0,
                "distinct_accounts": 0,
                "total_volume_paise": 0,
                "date_range": {"min": None, "max": None},
                "file_metadata": file_meta,
            }
        statement_account = resolved_stmt_acct

    # Build list of (section_file_type, section_mapping, section_records) to stage
    sections_to_stage: List[Dict[str, Any]] = []
    if file_meta.get("is_mixed_file") and len(file_meta.get("sections", [])) > 1:
        for s_idx, sec in enumerate(file_meta["sections"]):
            if s_idx == 0:
                sections_to_stage.append({
                    "file_type": file_type,
                    "mapping": column_mapping,
                    "records": sec["records"],
                })
            else:
                sec_det = detect_file_type(sec["headers"], sec["records"])
                sec_type = sec_det["detected_type"]
                if sec_type != "unknown":
                    sec_sug = suggest_column_mappings(sec_type, sec["headers"], sec["records"])
                    sec_map = {h: v["canonical"] for h, v in sec_sug.items()}
                    sections_to_stage.append({
                        "file_type": sec_type,
                        "mapping": sec_map,
                        "records": sec["records"],
                    })
    elif file_meta.get("multi_sheet") and len(file_meta.get("sheets", [])) > 1:
        for s_idx, sh in enumerate(file_meta["sheets"]):
            if s_idx == 0:
                sections_to_stage.append({
                    "file_type": file_type,
                    "mapping": column_mapping,
                    "records": sh["records"],
                })
            else:
                sh_det = detect_file_type(sh["headers"], sh["records"], banners=sh.get("banner_rows"))
                sh_type = sh_det["detected_type"]
                if sh_type != "unknown" and sh_det["confidence"] >= 0.40:
                    sh_sug = suggest_column_mappings(sh_type, sh["headers"], sh["records"])
                    sh_map = {h: v["canonical"] for h, v in sh_sug.items()}
                    sections_to_stage.append({
                        "file_type": sh_type,
                        "mapping": sh_map,
                        "records": sh["records"],
                    })
    else:
        sections_to_stage.append({
            "file_type": file_type,
            "mapping": column_mapping,
            "records": records,
        })

    rows_read = sum(len(s["records"]) for s in sections_to_stage)
    rows_ingested = 0
    rows_rejected = 0
    duplicates_skipped = 0
    rejections_by_reason: Dict[str, int] = {}

    distinct_phones = set()
    distinct_accounts = set()
    total_volume_paise = 0
    dates_seen: List[str] = []

    global_row_idx = 0

    for sec_block in sections_to_stage:
        cur_type = sec_block["file_type"]
        cur_mapping = sec_block["mapping"]
        cur_records = sec_block["records"]

        canon_to_raw: Dict[str, List[str]] = {}
        for raw_col, canon_field in cur_mapping.items():
            if canon_field and canon_field != "ignore":
                canon_to_raw.setdefault(canon_field, []).append(raw_col)

        # Per-column dayfirst inference across the section
        date_raw_headers = canon_to_raw.get("datetime", []) + canon_to_raw.get("date", [])
        column_date_samples = []
        for r_row in cur_records:
            for dh in date_raw_headers:
                dv = r_row.get(dh)
                if dv is not None and str(dv).strip():
                    column_date_samples.append(dv)
                    break
        inferred_dayfirst, _ = infer_column_dayfirst(column_date_samples)

        # Process in chunks for bounded transaction batching & progress reporting
        for chunk_start in range(0, len(cur_records), effective_chunk_size):
            batch = cur_records[chunk_start : chunk_start + effective_chunk_size]
            for raw_row in batch:
                global_row_idx += 1
                idx = global_row_idx
                page_no = raw_row.get("_page_no")
                source_ref_str = f"p{page_no}:{idx}" if page_no else str(idx)
                phys_row_no = file_meta.get("header_row_no", 1) + idx
                cur_raw_row_id = raw_row_lookup.get(("default", phys_row_no)) or raw_row_lookup.get(("document", phys_row_no))

                def get_val(canon_name: str):
                    headers_list = canon_to_raw.get(canon_name, [])
                    for h in headers_list:
                        v = raw_row.get(h)
                        if v is not None and str(v).strip():
                            return v
                    return None

                # -----------------------------------------------------------------
                # 1. CDR Staging
                # -----------------------------------------------------------------
                if cur_type == "cdr":
                    raw_caller = get_val("caller")
                    raw_receiver = get_val("receiver")

                    p_caller = normalize_phone(raw_caller)
                    p_receiver = normalize_phone(raw_receiver)

                    if not p_caller or not p_receiver:
                        reason = "MISSING_OR_INVALID_PHONE_NUMBER"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    raw_d = get_val("datetime") or get_val("date")
                    raw_t = get_val("time")
                    dt_res = normalize_datetime_detailed(raw_d, raw_t, dayfirst=inferred_dayfirst)
                    if dt_res["ok"]:
                        d_str = dt_res["meta"]["local_date"]
                        t_str = dt_res["meta"]["local_time"]
                        iso_str = dt_res["meta"]["utc_iso"]
                        tz_src = dt_res["meta"]["tz_source"]
                        dates_seen.append(d_str)
                    else:
                        d_str, t_str, iso_str, tz_src = "", "", "", "assumed_local"

                    dur = normalize_duration(get_val("duration"))
                    c_type = str(get_val("call_type") or "voice").lower()

                    fp = compute_row_fingerprint(ev.case_id, {
                        "t": "cdr",
                        "c": p_caller["number"],
                        "r": p_receiver["number"],
                        "dt": iso_str,
                        "d": dur
                    })

                    existing = db.query(CallRecord).filter(CallRecord.fingerprint == fp).first()
                    if existing:
                        duplicates_skipped += 1
                        continue

                    record = CallRecord(
                        case_id=ev.case_id,
                        source_file=ev.original_name,
                        source_ref=source_ref_str,
                        caller=p_caller["number"],
                        receiver=p_receiver["number"],
                        call_date=d_str,
                        call_time=t_str,
                        datetime_iso=iso_str,
                        tz_source=tz_src,
                        duration_seconds=dur,
                        call_type=c_type,
                        imei=str(get_val("imei") or "") or None,
                        imsi=str(get_val("imsi") or "") or None,
                        cell_id=str(get_val("cell_id") or "") or None,
                        raw_json=json.dumps(raw_row, default=str),
                        raw_row_id=cur_raw_row_id,
                        fingerprint=fp
                    )
                    db.add(record)
                    distinct_phones.add(p_caller["number"])
                    distinct_phones.add(p_receiver["number"])
                    rows_ingested += 1

                # -----------------------------------------------------------------
                # 2. Bank Transactions Staging
                # -----------------------------------------------------------------
                elif cur_type == "bank_transactions":
                    from_acc = normalize_account(get_val("from_account"))
                    to_acc = normalize_account(get_val("to_account"))

                    if not from_acc or not to_acc:
                        reason = "MISSING_REMITTER_OR_BENEFICIARY_ACCOUNT"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    amt_val = get_val("amount") or get_val("debit") or get_val("credit")
                    amt_paise = normalize_amount(amt_val)
                    if amt_paise is None or amt_paise == 0:
                        reason = "INVALID_OR_MISSING_TRANSACTION_AMOUNT"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    dt_res = normalize_datetime_detailed(get_val("datetime") or get_val("date"), get_val("time"), dayfirst=inferred_dayfirst)
                    if dt_res["ok"]:
                        d_str = dt_res["meta"]["local_date"]
                        iso_str = dt_res["meta"]["utc_iso"]
                        tz_src = dt_res["meta"]["tz_source"]
                        dates_seen.append(d_str)
                    else:
                        d_str, iso_str, tz_src = "", "", "assumed_local"

                    ref = str(get_val("reference") or get_val("txn_id") or "")

                    fp = compute_row_fingerprint(ev.case_id, {
                        "t": "txn",
                        "fa": from_acc,
                        "ta": to_acc,
                        "amt": amt_paise,
                        "dt": iso_str,
                        "ref": ref
                    })

                    existing = db.query(Transaction).filter(Transaction.fingerprint == fp).first()
                    if existing:
                        duplicates_skipped += 1
                        continue

                    from_orig, _ = normalize_name(get_val("from_name"))
                    to_orig, _ = normalize_name(get_val("to_name"))

                    txn = Transaction(
                        case_id=ev.case_id,
                        source_file=ev.original_name,
                        source_ref=source_ref_str,
                        txn_id=str(get_val("txn_id") or f"TXN-{idx}"),
                        from_account=from_acc,
                        to_account=to_acc,
                        from_name=from_orig or None,
                        to_name=to_orig or None,
                        amount_paise=abs(amt_paise),
                        date_iso=d_str,
                        tz_source=tz_src,
                        reference=ref or None,
                        direction="transfer",
                        raw_json=json.dumps(raw_row, default=str),
                        raw_row_id=cur_raw_row_id,
                        fingerprint=fp
                    )
                    db.add(txn)
                    distinct_accounts.add(from_acc)
                    distinct_accounts.add(to_acc)
                    total_volume_paise += abs(amt_paise)
                    rows_ingested += 1

                # -----------------------------------------------------------------
                # 3. Bank Statement Staging (Single-Account)
                # -----------------------------------------------------------------
                elif cur_type == "bank_statement":
                    stmt_acct = normalize_account(statement_account or get_val("statement_account"))
                    if not stmt_acct:
                        reason = "MISSING_STATEMENT_OWNER_ACCOUNT"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    narration = get_val("narration") or get_val("reference") or ""
                    parsed_nar = parse_statement_narration(narration)

                    debit_amt = normalize_amount(get_val("debit"))
                    credit_amt = normalize_amount(get_val("credit"))
                    generic_amt = normalize_amount(get_val("amount"))

                    if debit_amt is not None and debit_amt != 0:
                        direction = "debit"
                        amt_paise = abs(debit_amt)
                    elif credit_amt is not None and credit_amt != 0:
                        direction = "credit"
                        amt_paise = abs(credit_amt)
                    elif generic_amt is not None and generic_amt != 0:
                        direction = "debit" if generic_amt < 0 else "credit"
                        amt_paise = abs(generic_amt)
                    else:
                        reason = "UNPARSABLE_TRANSACTION_AMOUNT"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    dt_res = normalize_datetime_detailed(get_val("date"), dayfirst=inferred_dayfirst)
                    if dt_res["ok"]:
                        d_str = dt_res["meta"]["local_date"]
                        tz_src = dt_res["meta"]["tz_source"]
                        dates_seen.append(d_str)
                    else:
                        d_str, tz_src = "", "assumed_local"

                    counterparty = (
                        parsed_nar.get("counterparty_account")
                        or parsed_nar.get("counterparty_vpa")
                        or "COUNTERPARTY_UNKNOWN"
                    )

                    from_acc = stmt_acct if direction == "debit" else counterparty
                    to_acc = counterparty if direction == "debit" else stmt_acct

                    ref = parsed_nar.get("reference") or str(narration)[:40]

                    fp = compute_row_fingerprint(ev.case_id, {
                        "t": "stmt",
                        "fa": from_acc,
                        "ta": to_acc,
                        "amt": amt_paise,
                        "d": d_str,
                        "ref": ref
                    })

                    existing = db.query(Transaction).filter(Transaction.fingerprint == fp).first()
                    if existing:
                        duplicates_skipped += 1
                        continue

                    txn = Transaction(
                        case_id=ev.case_id,
                        source_file=ev.original_name,
                        source_ref=source_ref_str,
                        txn_id=f"STMT-{idx}",
                        from_account=from_acc,
                        to_account=to_acc,
                        from_name=None if direction == "debit" else parsed_nar.get("counterparty_name"),
                        to_name=parsed_nar.get("counterparty_name") if direction == "debit" else None,
                        amount_paise=amt_paise,
                        date_iso=d_str,
                        tz_source=tz_src,
                        reference=ref,
                        direction=direction,
                        raw_json=json.dumps(raw_row, default=str),
                        raw_row_id=cur_raw_row_id,
                        fingerprint=fp
                    )
                    db.add(txn)
                    distinct_accounts.add(stmt_acct)
                    if counterparty != "COUNTERPARTY_UNKNOWN":
                        distinct_accounts.add(counterparty)
                    total_volume_paise += amt_paise
                    rows_ingested += 1

                # -----------------------------------------------------------------
                # 4. Identity Table Staging (SDR, KYC, persons, vehicles)
                # -----------------------------------------------------------------
                elif cur_type == "identity_table":
                    orig_name, canon_name = normalize_name(get_val("name"))
                    if not orig_name:
                        reason = "MISSING_NAME_IDENTIFIER"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    p_entity = Entity(
                        case_id=ev.case_id,
                        label="Person",
                        canonical_id=canon_name,
                        display_name=orig_name,
                        properties_json=json.dumps({"name": orig_name}),
                        source_file=ev.original_name,
                        source_ref=source_ref_str,
                        method="identity_table",
                        confidence=1.0
                    )
                    db.add(p_entity)

                    raw_phone = get_val("phone") or get_val("registered_mobile")
                    phone_res = normalize_phone(raw_phone)
                    if phone_res:
                        distinct_phones.add(phone_res["number"])
                        db.add(Entity(
                            case_id=ev.case_id,
                            label="Phone",
                            canonical_id=phone_res["number"],
                            display_name=phone_res["number"],
                            properties_json=json.dumps(phone_res),
                            source_file=ev.original_name,
                            source_ref=source_ref_str,
                            method="identity_table",
                            confidence=1.0
                        ))

                    raw_acct = get_val("account") or get_val("account_no")
                    acct_clean = normalize_account(raw_acct)
                    if acct_clean:
                        distinct_accounts.add(acct_clean)
                        db.add(Entity(
                            case_id=ev.case_id,
                            label="BankAccount",
                            canonical_id=acct_clean,
                            display_name=acct_clean,
                            properties_json=json.dumps({
                                "account": acct_clean,
                                "source_raw": str(raw_acct) if raw_acct is not None else None
                            }),
                            source_file=ev.original_name,
                            source_ref=source_ref_str,
                            method="identity_table",
                            confidence=1.0
                        ))

                    raw_veh = get_val("vehicle") or get_val("registration")
                    veh_clean = normalize_vehicle(raw_veh)
                    if veh_clean:
                        db.add(Entity(
                            case_id=ev.case_id,
                            label="Vehicle",
                            canonical_id=veh_clean,
                            display_name=veh_clean,
                            properties_json=json.dumps({
                                "registration": veh_clean,
                                "source_raw": str(raw_veh) if raw_veh is not None else None
                            }),
                            source_file=ev.original_name,
                            source_ref=source_ref_str,
                            method="identity_table",
                            confidence=1.0
                        ))

                    rows_ingested += 1

                # -----------------------------------------------------------------
                # 5. IP Log Staging
                # -----------------------------------------------------------------
                elif cur_type == "ip_log":
                    identifier = str(get_val("identifier") or "").strip()
                    raw_ip = get_val("ip") or get_val("ip_address")
                    ip_val, is_valid_ip = normalize_ip(raw_ip)

                    if not identifier or not ip_val or not is_valid_ip:
                        reason = "INVALID_IP_ADDRESS_OR_IDENTIFIER"
                        _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                        rows_rejected += 1
                        continue

                    dt_res = normalize_datetime_detailed(get_val("datetime") or get_val("date"), dayfirst=inferred_dayfirst)
                    if dt_res["ok"]:
                        d_str = dt_res["meta"]["local_date"]
                        iso_str = dt_res["meta"]["utc_iso"]
                        tz_src = dt_res["meta"]["tz_source"]
                        dates_seen.append(d_str)
                    else:
                        d_str, iso_str, tz_src = "", "", "assumed_local"

                    ip_ev = IPEvent(
                        case_id=ev.case_id,
                        source_file=ev.original_name,
                        source_ref=source_ref_str,
                        identifier=identifier,
                        ip_address=ip_val,
                        datetime_iso=iso_str,
                        tz_source=tz_src,
                        raw_json=json.dumps(raw_row, default=str),
                        raw_row_id=cur_raw_row_id
                    )
                    db.add(ip_ev)
                    rows_ingested += 1
                else:
                    reason = f"UNSUPPORTED_RECORD_TYPE_{cur_type.upper()}"
                    _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason, raw_row_id=cur_raw_row_id)
                    rows_rejected += 1

            db.flush()
            if progress_callback and rows_read > 0:
                pct = min(95, int(20 + (global_row_idx / max(1, rows_read)) * 75))
                progress_callback(pct, f"Processed {global_row_idx}/{rows_read} rows")

    # Update evidence status and store statement metadata + completeness in quality_json
    ev.status = "ingested"
    ev.detected_type = file_type
    try:
        existing_qual = json.loads(ev.quality_json or "{}")
    except Exception:
        existing_qual = {}
    if file_type == "bank_statement" or file_meta.get("opening_balance_paise") is not None or file_meta.get("closing_balance_paise") is not None:
        existing_qual["statement_metadata"] = {
            "owner_account": statement_account or (owner_meta.get("account_number") if owner_meta else None),
            "owner_name": owner_meta.get("account_holder") if owner_meta else None,
            "opening_balance_paise": file_meta.get("opening_balance_paise"),
            "closing_balance_paise": file_meta.get("closing_balance_paise"),
        }
        ev.quality_json = json.dumps(existing_qual, default=str)
    db.commit()

    try:
        from backend.app.services.extraction.completeness import compute_evidence_completeness
        compute_evidence_completeness(db, ev.id, persist_quality=True)
    except Exception:
        pass

    # Log action to immutable audit trail
    record_audit_log(
        db=db,
        user_id=user_id,
        action="ingest_evidence",
        case_id=ev.case_id,
        object_type="evidence_file",
        object_id=ev.id,
        details={
            "file_type": file_type,
            "rows_read": rows_read,
            "rows_ingested": rows_ingested,
            "rows_rejected": rows_rejected,
            "duplicates_skipped": duplicates_skipped,
            "opening_balance_paise": file_meta.get("opening_balance_paise"),
            "closing_balance_paise": file_meta.get("closing_balance_paise"),
        }
    )

    min_date = min(dates_seen) if dates_seen else None
    max_date = max(dates_seen) if dates_seen else None

    # Phase 1: Enforce independent reconciliation invariant
    recon_res = reconcile_evidence_file(db=db, evidence_file_id=ev.id, file_path=file_path)
    if not recon_res.get("is_reconciled", True):
        ev.status = "failed"
        db.commit()
        raise ValueError(
            f"RECONCILIATION_FAILED: Ingestion row count mismatch: {recon_res.get('sheets')}"
        )

    return {
        "evidence_id": ev.id,
        "status": "ingested",
        "needs_owner_confirmation": False,
        "file_type": file_type,
        "reconciliation": recon_res,
        "rows_read": rows_read,
        "rows_ingested": rows_ingested,
        "rows_rejected": rows_rejected,
        "duplicates_skipped": duplicates_skipped,
        "rejections_by_reason": rejections_by_reason,
        "distinct_phones": len(distinct_phones),
        "distinct_accounts": len(distinct_accounts),
        "total_volume_paise": total_volume_paise,
        "date_range": {"min": min_date, "max": max_date},
        "file_metadata": file_meta,
    }


def _record_rejection(
    db: Session,
    ev_id: str,
    case_id: str,
    row_num: int,
    raw_row: dict,
    reason: str,
    counter: dict,
    raw_row_id: Optional[str] = None,
):
    """Records a rejected row with its failure reason in SQLite and updates raw_row status."""
    counter[reason] = counter.get(reason, 0) + 1
    rej = RejectedRow(
        evidence_id=ev_id,
        case_id=case_id,
        row_number=row_num,
        raw_data_json=json.dumps(raw_row, default=str),
        raw_row_id=raw_row_id,
        reason=reason
    )
    db.add(rej)
    if raw_row_id:
        db.query(RawRow).filter(RawRow.id == raw_row_id).update({"status": "rejected"})
