# Database Map (database-map.md) — Case Connect AI

This document provides a comprehensive schema reference for the authoritative SQLite database (31 SQLAlchemy models) and the disposable Neo4j graph index.

---

## 1. Relational Database Architecture (SQLite WAL)

All tables use UUID or prefixed string primary keys (`usr_`, `cas_`, `evi_`, `rec_`, `clm_`), UTC ISO-8601 timestamps, and strictly integer monetary values (`amount_paise`).

### 1.1 System, Auth & Audit Tables
1. **`users`**:
   - `id` (PK, String), `username` (Unique, String), `password_hash` (String, 12 rounds bcrypt), `role` (`admin` | `investigator` | `viewer`), `is_active` (Boolean), `created_at` (DateTime).
2. **`audit_log`**:
   - `id` (PK, Integer Auto-increment), `ts` (DateTime UTC), `user_id` (String), `action` (String), `case_id` (FK -> `cases.id`), `details_json` (Text), `prev_hash` (String, SHA-256), `hash` (String, SHA-256).
   - *Invariant:* Cryptographic hash chain: `hash = SHA256(prev_hash + ts + user_id + action + case_id + details_json)`.

### 1.2 Case Docket Management
3. **`cases`**:
   - `id` (PK, String), `case_number` (String), `title` (String), `description` (Text), `status` (String), `created_by` (FK -> `users.id`), `created_at` (DateTime), `updated_at` (DateTime).
4. **`case_members`**:
   - `id` (PK, String), `case_id` (FK -> `cases.id`), `user_id` (FK -> `users.id`), `role` (String), `assigned_at` (DateTime).
5. **`case_settings`**:
   - `id` (PK, String), `case_id` (FK -> `cases.id`), `key` (String), `value_json` (Text), `updated_at` (DateTime).
6. **`saved_views`**:
   - `id` (PK, String), `case_id` (FK -> `cases.id`), `name` (String), `filter_json` (Text), `created_at` (DateTime).
7. **`annotations`**:
   - `id` (PK, String), `case_id` (FK -> `cases.id`), `target_type` (`entity` | `record`), `target_id` (String), `note` (Text), `tags_json` (Text), `officer_id` (String), `is_deleted` (Boolean), `created_at` (DateTime).

### 1.3 Evidence Staging & Jobs
8. **`evidence_files`**:
   - `id` (PK, String), `case_id` (FK -> `cases.id`), `filename` (String), `file_path` (String), `file_size_bytes` (Integer), `mime_type` (String), `sha256` (String), `status` (String), `source_kind` (String), `uploaded_by` (String), `created_at` (DateTime).
9. **`evidence_pages`**:
   - `id` (PK, String), `evidence_id` (FK -> `evidence_files.id`), `page_number` (Integer), `raw_text` (Text), `words_json` (Text), `quality_score` (Float), `blur_score` (Float), `is_handwritten` (Boolean), `created_at` (DateTime).
10. **`column_mappings`**:
    - `id` (PK, String), `evidence_id` (FK -> `evidence_files.id`), `raw_header` (String), `target_field` (String), `confidence` (Float).
11. **`mapping_templates`**:
    - `id` (PK, String), `template_name` (String), `source_type` (String), `mapping_json` (Text), `created_at` (DateTime).
12. **`jobs`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (String), `job_type` (String), `status` (`pending` | `processing` | `completed` | `failed` | `cancelled`), `progress_pct` (Integer), `steps_json` (Text), `error_message` (Text), `reason_code` (String), `created_at` (DateTime), `updated_at` (DateTime).
13. **`rejected_rows`**:
    - `id` (PK, String), `evidence_id` (FK -> `evidence_files.id`), `row_index` (Integer), `raw_row_json` (Text), `reason_code` (String), `created_at` (DateTime).

### 1.4 Unified Extraction & Merge Engine (Phases 3–8)
14. **`extraction_records`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (FK -> `evidence_files.id`), `record_type` (`call` | `transaction` | `ip_event` | `entity`), `natural_key` (String, SHA-256), `occurrence_idx` (Integer), `data_json` (Text), `extra_json` (Text, dynamic unknown fields), `raw_json` (Text), `source_ref` (String), `page_no` (Integer), `bbox_json` (Text), `timestamp_sec` (Float), `method` (String), `source_kind` (String), `confidence` (Float), `extractor_version` (String), `status` (`active` | `merged` | `retracted` | `rejected`), `merged_into_id` (String), `staged_table` (String), `staged_id` (String), `first_seen_run_id` (String), `last_seen_run_id` (String), `created_at` (DateTime).
    - *Constraint:* `UNIQUE(case_id, record_type, natural_key, occurrence_idx, evidence_id)`.
15. **`record_sources`**:
    - `id` (PK, String), `record_id` (FK -> `extraction_records.id`), `evidence_id` (FK -> `evidence_files.id`), `source_ref` (String), `seen_at` (DateTime).
16. **`field_claims`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `subject_type` (`entity` | `record`), `subject_id` (String), `field_name` (String), `value_norm` (String), `value_raw` (String), `evidence_id` (String), `source_ref` (String), `source_kind` (String), `method` (String), `confidence` (Float), `validator_ok` (Boolean), `status` (`active` | `retracted`), `observed_at` (DateTime), `run_id` (String).
17. **`golden_fields`**:
    - `id` (PK, String), `subject_type` (String), `subject_id` (String), `field_name` (String), `selected_claim_id` (FK -> `field_claims.id`), `selected_by` (`auto` | `officer`), `locked` (Boolean), `reason_code` (String), `updated_at` (DateTime).
    - *Constraint:* `UNIQUE(subject_type, subject_id, field_name)`.
18. **`merge_conflicts`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `subject_type` (String), `subject_id` (String), `field_name` (String), `claim_ids_json` (Text), `status` (`open` | `resolved` | `dismissed`), `resolution_claim_id` (String), `resolved_by` (String), `resolved_at` (DateTime), `reason_code` (String), `created_at` (DateTime).
19. **`ingest_runs`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (FK -> `evidence_files.id`), `job_id` (String), `mode` (`preview` | `apply` | `rollback`), `counts_json` (Text), `status` (String), `extractor_version` (String), `started_at` (DateTime), `finished_at` (DateTime).
20. **`schema_registry`**:
    - `id` (PK, String), `record_type` (String), `field_name` (String), `seen_count` (Integer), `first_seen_at` (DateTime), `promoted` (Boolean).

### 1.5 Forensic Records & Staging Tables
21. **`call_records`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (FK -> `evidence_files.id`), `caller_number` (String), `receiver_number` (String), `call_time` (DateTime), `duration_seconds` (Integer), `call_type` (String), `imei` (String), `cell_tower_id` (String).
22. **`transactions`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (FK -> `evidence_files.id`), `txn_id` (String), `account_number` (String), `counterparty_account` (String), `amount_paise` (Integer, no floats), `txn_date` (DateTime), `direction` (`IN` | `OUT`), `narration` (Text), `balance_after_paise` (Integer).
23. **`ip_events`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `ip_address` (String), `event_time` (DateTime), `user_identifier` (String), `event_type` (String).
24. **`entities`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `canonical_type` (`phone` | `bank_account` | `person` | `vehicle` | `device`), `canonical_id` (String), `display_name` (String), `risk_score` (Float), `is_master` (Boolean).
25. **`entity_links`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `source_entity_id` (FK -> `entities.id`), `target_entity_id` (FK -> `entities.id`), `relationship_type` (String), `confidence` (Float), `evidence_id` (String).
26. **`extracted_entities`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `evidence_id` (FK -> `evidence_files.id`), `entity_type` (String), `raw_value` (String), `normalized_value` (String), `confidence` (Float), `source_span` (Text), `page_no` (Integer), `bbox_json` (Text), `method` (String).
27. **`match_suggestions`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `entity_id_a` (String), `entity_id_b` (String), `similarity_score` (Float), `reasons_json` (Text), `status` (`pending` | `approved` | `rejected`).
28. **`profile_members`**:
    - `id` (PK, String), `master_entity_id` (String), `member_entity_id` (String), `merged_by` (String), `merged_at` (DateTime).
29. **`alerts`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `pattern_type` (String), `entity_id` (String), `severity` (`HIGH` | `MEDIUM` | `LOW`), `details_json` (Text), `created_at` (DateTime).
30. **`lead_decisions`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `entity_id` (String), `decision` (String), `officer_notes` (Text), `updated_at` (DateTime).
31. **`reports`**:
    - `id` (PK, String), `case_id` (FK -> `cases.id`), `title` (String), `file_path` (String), `sha256` (String), `generated_by` (String), `created_at` (DateTime).

---

## 2. Disposable Graph Projection (Neo4j / NetworkX)

- **Source of Truth:** SQLite relational tables.
- **Node Labels:**
  - `(:Person {id, name, case_id})`
  - `(:Phone {id, number, valid_mobile, carrier_hint, case_id})`
  - `(:BankAccount {id, account_number, ifsc, bank_name, case_id})`
  - `(:IPAddress {id, ip, case_id})`
  - `(:Vehicle {id, reg_no, state_code, case_id})`
- **Relationship Types:**
  - `[:CALLED {count, total_duration, nocturnal_ratio, last_seen}]`
  - `[:TRANSFERRED {total_amount_paise, txn_count, last_txn_date}]`
  - `[:ACCESSED {last_seen, event_count}]`
  - `[:IDENTIFIED_AS {confidence, source_evidence_id}]`
  - `[:ASSOCIATED_WITH {source_relation, status}]`
- **Rebuild Operation:** `POST /cases/{id}/graph/rebuild` queries all active `extraction_records` and staged links from SQLite and projects them onto Neo4j/NetworkX.

