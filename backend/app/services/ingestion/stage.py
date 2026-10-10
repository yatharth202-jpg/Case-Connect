import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.db.sql import (
    CallRecord, Transaction, IPEvent, Entity, RejectedRow,
    EvidenceFile, ColumnMapping
)
from backend.app.services.ingestion.readers import read_tabular_file
from backend.app.services.ingestion.normalize import (
    normalize_phone, normalize_account, normalize_amount,
    normalize_datetime, normalize_duration, normalize_name,
    normalize_vehicle, normalize_email, normalize_ip
)
from backend.app.services.ingestion.statement import parse_statement_narration
from backend.app.audit.service import record_audit_log

def compute_row_fingerprint(case_id: str, payload_dict: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 fingerprint for deduplicating identical records."""
    norm_str = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{case_id}|{norm_str}".encode("utf-8")).hexdigest()

def stage_evidence_file(
    db: Session,
    evidence_id: str,
    user_id: str,
    file_type: str,
    column_mapping: Dict[str, str],
    statement_account: str = None
) -> Dict[str, Any]:
    """
    Executes end-to-end staging: reads raw file, normalizes fields,
    filters rejected rows, deduplicates by fingerprint, stages into SQLite.
    """
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_id).first()
    if not ev:
        raise ValueError(f"Evidence file {evidence_id} not found")

    file_path = Path(ev.stored_path)
    records, headers, banners = read_tabular_file(file_path)

    # If statement_account wasn't explicitly given, check banner rows for "Account No: ..."
    if file_type == "bank_statement" and not statement_account and banners:
        for b in banners:
            if "account no" in b.lower() or "a/c no" in b.lower():
                digits = [s for s in b.split() if s.isdigit() and len(s) >= 8]
                if digits:
                    statement_account = digits[0]
                    break

    # Reverse mapping: canonical_field -> list of raw headers
    canon_to_raw = {}
    for raw_col, canon_field in column_mapping.items():
        if canon_field and canon_field != "ignore":
            canon_to_raw.setdefault(canon_field, []).append(raw_col)

    rows_read = len(records)
    rows_ingested = 0
    rows_rejected = 0
    duplicates_skipped = 0
    rejections_by_reason = {}

    distinct_phones = set()
    distinct_accounts = set()
    total_volume_paise = 0
    dates_seen = []

    for idx, raw_row in enumerate(records, 1):
        def get_val(canon_name):
            headers_list = canon_to_raw.get(canon_name, [])
            for h in headers_list:
                v = raw_row.get(h)
                if v is not None and str(v).strip():
                    return v
            return None

        # -----------------------------------------------------------------
        # 1. CDR Staging
        # -----------------------------------------------------------------
        if file_type == "cdr":
            raw_caller = get_val("caller")
            raw_receiver = get_val("receiver")

            p_caller = normalize_phone(raw_caller)
            p_receiver = normalize_phone(raw_receiver)

            if not p_caller or not p_receiver:
                reason = "MISSING_OR_INVALID_PHONE_NUMBER"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            raw_d = get_val("datetime") or get_val("date")
            raw_t = get_val("time")
            d_str, t_str, iso_str = normalize_datetime(raw_d, raw_t)
            dates_seen.append(d_str)

            dur = normalize_duration(get_val("duration"))
            c_type = str(get_val("call_type") or "voice").lower()

            fp = compute_row_fingerprint(ev.case_id, {
                "t": "cdr",
                "c": p_caller["number"],
                "r": p_receiver["number"],
                "dt": iso_str,
                "d": dur
            })

            # Check duplicate
            existing = db.query(CallRecord).filter(CallRecord.fingerprint == fp).first()
            if existing:
                duplicates_skipped += 1
                continue

            record = CallRecord(
                case_id=ev.case_id,
                source_file=ev.original_name,
                source_ref=str(idx),
                caller=p_caller["number"],
                receiver=p_receiver["number"],
                call_date=d_str,
                call_time=t_str,
                datetime_iso=iso_str,
                duration_seconds=dur,
                call_type=c_type,
                imei=str(get_val("imei") or "") or None,
                imsi=str(get_val("imsi") or "") or None,
                cell_id=str(get_val("cell_id") or "") or None,
                fingerprint=fp
            )
            db.add(record)
            distinct_phones.add(p_caller["number"])
            distinct_phones.add(p_receiver["number"])
            rows_ingested += 1

        # -----------------------------------------------------------------
        # 2. Bank Transactions Staging
        # -----------------------------------------------------------------
        elif file_type == "bank_transactions":
            from_acc = normalize_account(get_val("from_account"))
            to_acc = normalize_account(get_val("to_account"))

            if not from_acc or not to_acc:
                reason = "MISSING_REMITTER_OR_BENEFICIARY_ACCOUNT"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            # Amount logic
            amt_val = get_val("amount") or get_val("debit") or get_val("credit")
            amt_paise = normalize_amount(amt_val)
            if amt_paise is None or amt_paise == 0:
                reason = "INVALID_OR_MISSING_TRANSACTION_AMOUNT"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            d_str, t_str, iso_str = normalize_datetime(get_val("datetime") or get_val("date"), get_val("time"))
            dates_seen.append(d_str)

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

            from_orig, from_canon = normalize_name(get_val("from_name"))
            to_orig, to_canon = normalize_name(get_val("to_name"))

            txn = Transaction(
                case_id=ev.case_id,
                source_file=ev.original_name,
                source_ref=str(idx),
                txn_id=str(get_val("txn_id") or f"TXN-{idx}"),
                from_account=from_acc,
                to_account=to_acc,
                from_name=from_orig or None,
                to_name=to_orig or None,
                amount_paise=abs(amt_paise),
                date_iso=d_str,
                reference=ref or None,
                direction="transfer",
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
        elif file_type == "bank_statement":
            stmt_acct = normalize_account(statement_account or get_val("statement_account") or "PRIMARY_ACCOUNT")
            narration = get_val("narration") or get_val("reference") or ""
            parsed_nar = parse_statement_narration(narration)

            # Determine amount & direction
            debit_amt = normalize_amount(get_val("debit"))
            credit_amt = normalize_amount(get_val("credit"))
            generic_amt = normalize_amount(get_val("amount"))

            if debit_amt is not None and debit_amt > 0:
                direction = "debit"
                amt_paise = debit_amt
            elif credit_amt is not None and credit_amt > 0:
                direction = "credit"
                amt_paise = credit_amt
            elif generic_amt is not None and generic_amt != 0:
                direction = "debit" if generic_amt < 0 else "credit"
                amt_paise = abs(generic_amt)
            else:
                reason = "UNPARSABLE_TRANSACTION_AMOUNT"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            d_str, t_str, iso_str = normalize_datetime(get_val("date"))
            dates_seen.append(d_str)

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
                source_ref=str(idx),
                txn_id=f"STMT-{idx}",
                from_account=from_acc,
                to_account=to_acc,
                from_name=None if direction == "debit" else parsed_nar.get("counterparty_name"),
                to_name=parsed_nar.get("counterparty_name") if direction == "debit" else None,
                amount_paise=amt_paise,
                date_iso=d_str,
                reference=ref,
                direction=direction,
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
        elif file_type == "identity_table":
            orig_name, canon_name = normalize_name(get_val("name"))
            if not orig_name:
                reason = "MISSING_NAME_IDENTIFIER"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            # Stage Person entity
            p_entity = Entity(
                case_id=ev.case_id,
                label="Person",
                canonical_id=canon_name,
                display_name=orig_name,
                properties_json=json.dumps({"name": orig_name}),
                source_file=ev.original_name,
                source_ref=str(idx),
                method="identity_table",
                confidence=1.0
            )
            db.add(p_entity)

            # Stage associated identifiers
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
                    source_ref=str(idx),
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
                    properties_json=json.dumps({"account": acct_clean}),
                    source_file=ev.original_name,
                    source_ref=str(idx),
                    method="identity_table",
                    confidence=1.0
                ))

            veh_clean = normalize_vehicle(get_val("vehicle") or get_val("registration"))
            if veh_clean:
                db.add(Entity(
                    case_id=ev.case_id,
                    label="Vehicle",
                    canonical_id=veh_clean,
                    display_name=veh_clean,
                    properties_json=json.dumps({"registration": veh_clean}),
                    source_file=ev.original_name,
                    source_ref=str(idx),
                    method="identity_table",
                    confidence=1.0
                ))

            rows_ingested += 1

        # -----------------------------------------------------------------
        # 5. IP Log Staging
        # -----------------------------------------------------------------
        elif file_type == "ip_log":
            identifier = str(get_val("identifier") or "").strip()
            raw_ip = get_val("ip") or get_val("ip_address")
            ip_val, is_valid_ip = normalize_ip(raw_ip)

            if not identifier or not ip_val or not is_valid_ip:
                reason = "INVALID_IP_ADDRESS_OR_IDENTIFIER"
                _record_rejection(db, ev.id, ev.case_id, idx, raw_row, reason, rejections_by_reason)
                rows_rejected += 1
                continue

            d_str, t_str, iso_str = normalize_datetime(get_val("datetime") or get_val("date"))
            dates_seen.append(d_str)

            ip_ev = IPEvent(
                case_id=ev.case_id,
                source_file=ev.original_name,
                source_ref=str(idx),
                identifier=identifier,
                ip_address=ip_val,
                datetime_iso=iso_str
            )
            db.add(ip_ev)
            rows_ingested += 1

    # Update evidence status
    ev.status = "ingested"
    ev.detected_type = file_type
    db.commit()

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
            "duplicates_skipped": duplicates_skipped
        }
    )

    date_min = min(dates_seen) if dates_seen else None
    date_max = max(dates_seen) if dates_seen else None

    return {
        "evidence_id": ev.id,
        "file_name": ev.original_name,
        "file_type": file_type,
        "rows_read": rows_read,
        "rows_ingested": rows_ingested,
        "rows_rejected": rows_rejected,
        "duplicates_skipped": duplicates_skipped,
        "rejections_by_reason": rejections_by_reason,
        "distinct_phones": len(distinct_phones),
        "distinct_accounts": len(distinct_accounts),
        "total_volume_paise": total_volume_paise,
        "total_volume_inr": total_volume_paise / 100.0,
        "date_range": {"min": date_min, "max": date_max}
    }

def _record_rejection(db: Session, ev_id: str, case_id: str, row_no: int, raw_dict: dict, reason: str, counts_map: dict):
    """Logs rejected row to rejected_rows table and updates memory counter."""
    rej = RejectedRow(
        evidence_id=ev_id,
        case_id=case_id,
        row_number=row_no,
        raw_data_json=json.dumps(raw_dict),
        reason=reason,
        created_at=datetime.utcnow()
    )
    db.add(rej)
    counts_map[reason] = counts_map.get(reason, 0) + 1
