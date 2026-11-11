# REST API Specification (API.md) — Case Connect AI

**Product:** Case Connect AI — Criminal Network Analysis System  
**Document Version:** 1.0.0  
**Status:** Approved Source of Truth  
**API Protocol:** REST over HTTP/HTTPS with JSON payloads  
**Authentication Scheme:** HTTP Bearer JSON Web Tokens (JWT HS256)  
**Foundational References:** PRD.md, ARCHITECTURE.md, DATABASE.md  

---

## 1. Global Conventions & Protocol Standards

### 1.1 Base URL & Content Types
* **Development URL:** `http://localhost:8000`
* **Production Base Path:** `/` or `/api/v1`
* **Content Type:** `application/json` for all standard endpoints, `multipart/form-data` for file uploads, `application/pdf` for court dossiers.

### 1.2 Authentication & Authorization Headers
Protected endpoints require an `Authorization` header containing a valid Bearer token:
```http
Authorization: Bearer <jwt_access_token>
```
Server-side authorization verifies:
1. Token signature and validity against `JWT_SECRET`.
2. User active status (`is_active = True`).
3. System role permissions (`admin`, `investigator`, `viewer`).
4. Case docket membership for case-scoped paths (`/cases/{case_id}/...`).

### 1.3 Standard Response Envelopes
* **Standard Success:** Returns the requested resource entity or JSON collection directly.
* **Error Envelope:**
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested case could not be found or access is denied."
    }
  }
  ```
* **Asynchronous Job Envelope:**
  ```json
  {
    "id": "job_94a73e8f-7c12-4211-8be4-7a31b6e680a1",
    "case_id": "case_101",
    "job_type": "ingest",
    "status": "queued | running | done | failed",
    "progress": 65,
    "steps": [
      {"name": "read_file", "status": "done"},
      {"name": "detect_and_map", "status": "done"},
      {"name": "clean_and_stage", "status": "running"},
      {"name": "sync_graph", "status": "queued"}
    ],
    "error": null
  }
  ```

---

## 2. Authentication & User Management Endpoints

### 2.1 Authenticate Officer
* **`POST /auth/login`**
  - **Description:** Verifies officer credentials and issues a signed JWT access token.
  - **Request Body:**
    ```json
    {
      "username": "investigator1",
      "password": "OfficerPass1234!"
    }
    ```
  - **Response `200 OK`:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "token_type": "bearer",
      "user": {
        "id": "usr_99812",
        "username": "investigator1",
        "role": "investigator"
      }
    }
    ```
  - **Errors:** `401 Unauthorized` ("Invalid username or password").

### 2.2 Current User Profile
* **`GET /auth/me`**
  - **Description:** Returns profile and active permissions for the authenticated officer.
  - **Response `200 OK`:**
    ```json
    {
      "id": "usr_99812",
      "username": "investigator1",
      "role": "investigator",
      "is_active": true
    }
    ```

### 2.3 User Directory Management *(Admin Only)*
* **`GET /users`** — List system users (`admin` only).
* **`POST /users`** — Provision new officer account.
  - **Request Body:** `{"username": "officer2", "password": "...", "role": "investigator"}`
* **`PATCH /users/{id}`** — Modify user active status or role assignment.

---

## 3. Case Docket Management Endpoints

### 3.1 Create Investigation Docket
* **`POST /cases`**
  - **Description:** Initializes a new investigation case docket.
  - **Request Body:**
    ```json
    {
      "title": "FIR No. 402/2026 Cyber Cell Cyberabad",
      "description": "Multi-tier phishing syndicate targeting banking victims.",
      "priority": "high"
    }
    ```
  - **Response `201 Created`:** Created case record including creator and creation timestamp.

### 3.2 List Accessible Cases
* **`GET /cases`**
  - **Description:** Returns all dockets the authenticated user is authorized to inspect.
  - **Response `200 OK`:**
    ```json
    [
      {
        "id": "case_101",
        "title": "FIR No. 402/2026 Cyber Cell Cyberabad",
        "priority": "high",
        "status": "active",
        "evidence_count": 4,
        "created_at": "2026-08-10T10:30:00Z"
      }
    ]
    ```

### 3.3 Get Case Docket Details
* **`GET /cases/{id}`**
  - **Description:** Returns full docket details, assigned officers, and evidence summary.
  - **Errors:** `403 Forbidden` if user is not assigned, `404 Not Found`.

### 3.4 Manage Case Members
* **`GET /cases/{id}/members`** — List officers assigned to this case.
* **`POST /cases/{id}/members`** — Assign officer to case (`{"user_id": "...", "role": "..."}`).
* **`DELETE /cases/{id}/members/{user_id}`** — Remove officer from case docket.

### 3.5 Configure Case Settings
* **`GET /cases/{id}/settings`** — Retrieve case-specific anomaly and scoring thresholds.
* **`PUT /cases/{id}/settings`** — Update thresholds (e.g., minimum call spike MAD factor).

---

## 4. Evidence Ingestion & Column Mapping Endpoints

### 4.1 Upload Evidence File
* **`POST /cases/{id}/evidence`**
  - **Format:** `multipart/form-data`
  - **Fields:** `file` (Binary payload), `description` (Optional notes).
  - **Behavior:** Validates magic bytes, computes SHA-256 hash, stores raw file on disk, strips preambles, and computes header signature.
  - **Response `201 Created`:**
    ```json
    {
      "id": "evi_8820",
      "case_id": "case_101",
      "original_name": "Airtel_CDR_North_Zone.csv",
      "file_size": 491203,
      "sha256": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
      "detected_type": "cdr",
      "suggested_mapping": {
        "Caller_Number": "caller",
        "Receiver_Number": "receiver",
        "Date_Time": "datetime_iso",
        "Call_Duration": "duration_seconds"
      },
      "header_signature": "sig_49f8a3..."
    }
    ```

### 4.2 Confirm Column Mapping
* **`POST /evidence/{id}/mapping`**
  - **Description:** Submits confirmed column alignments; saves mapping template for recurring bank branches or telecom circle formats.
  - **Request Body:**
    ```json
    {
      "mapping": {
        "Caller_Number": "caller",
        "Receiver_Number": "receiver",
        "Date_Time": "datetime_iso",
        "Call_Duration": "duration_seconds",
        "IMEI_No": "imei"
      }
    }
    ```

### 4.3 Trigger Asynchronous Ingestion Job
* **`POST /evidence/{id}/ingest`**
  - **Description:** Queues background ingestion job that cleans, validates, stages rows in paise/ISO format, and triggers graph synchronization.
  - **Response `202 Accepted`:** Job response envelope containing Job ID.

### 4.4 Check Job Status
* **`GET /jobs/{id}`**
  - **Description:** Returns real-time execution progress (0% to 100%) and granular step status.

---

## 5. Investigation Graph Endpoints

### 5.1 Search Graph Network
* **`GET /cases/{id}/graph/search`**
  - **Query Parameters:** `q` (Search query string: phone, account, or person name), `hops` (Integer: 1, 2, 3, or 4).
  - **Response `200 OK` (Standard Graph Shape):**
    ```json
    {
      "nodes": [
        {
          "id": "case1|Person|rahul_sharma",
          "type": "Person",
          "label": "Rahul Sharma",
          "props": {
            "degree": 5,
            "shared": false,
            "first_seen": "2026-08-01T10:00:00Z"
          }
        },
        {
          "id": "case1|Phone|9876543210",
          "type": "Phone",
          "label": "9876543210",
          "props": {
            "valid_mobile": true
          }
        }
      ],
      "edges": [
        {
          "id": "edge_123",
          "source": "case1|Person|rahul_sharma",
          "target": "case1|Phone|9876543210",
          "type": "USES",
          "props": {
            "confidence": 0.95,
            "method": "structured"
          }
        }
      ],
      "truncated": false,
      "meta": {
        "hops": 2,
        "count_nodes": 2,
        "count_edges": 1
      }
    }
    ```

### 5.2 Shortest Path Finder
* **`GET /cases/{id}/graph/path`**
  - **Query Parameters:** `source_id`, `target_id`.
  - **Returns:** Sequence of nodes and relationships bridging two entities.

### 5.3 Manual Link Association
* **`POST /cases/{id}/links`** — Investigator-added relationship link.
* **`DELETE /cases/{id}/links/{id}`** — Remove manual relationship link.

---

## 6. Financial Forensics & Money Trail Endpoints

### 6.1 Money Trail Graph Projection
* **`GET /cases/{id}/money-trail`**
  - **Query Parameters:** `account_id` (Focal bank account), `hops` (1..4), `quantile` (`p50`, `p75`, `p90`, `p99`), `direction` (`in`, `out`, `both`).
  - **Response `200 OK`:**
    ```json
    {
      "nodes": [ ... ],
      "edges": [ ... ],
      "totals": {
        "inflow_paise": 150000000,
        "outflow_paise": 149000000,
        "throughput_paise": 299000000
      },
      "flags": {
        "is_pass_through": true,
        "pass_through_ratio": 0.993,
        "fan_in_count": 8,
        "fan_out_count": 2
      }
    }
    ```

### 6.2 Transaction Volume Analytics
* **`GET /cases/{id}/analytics/txn-volume`**
  - **Returns:** Time-binned transaction totals and frequency histograms for charting.

---

## 7. AI Lead Advisor & Entity Deduplication Endpoints

### 7.1 Prioritized Leads
* **`GET /cases/{id}/leads`**
  - **Description:** Returns ranked entities scored by Centrality, MAD call spikes, and layering.
  - **Response `200 OK`:** Array of lead objects with `priority` (`HIGH`, `MEDIUM`, `LOW`), `score`, `signals` breakdown, and `matched_pattern`.

### 7.2 Lead Explainability Inspector
* **`GET /cases/{id}/entities/{entity_id}/why`**
  - **Returns:** Detailed mathematical explanation, configuration thresholds used, and linked evidence rows justifying the lead score.

### 7.3 Submit Lead Decision
* **`POST /cases/{id}/leads/{lead_id}/decision`**
  - **Request Body:**
    ```json
    {
      "decision": "accept",
      "notes": "Verified suspect device usage in cell tower sector."
    }
    ```

### 7.4 Entity Deduplication & Reversible Merging
* **`GET /cases/{id}/matches`** — List pending entity deduplication candidates.
* **`POST /cases/{id}/matches/{match_id}/approve`** — Merge entities into Master Profile.
* **`POST /cases/{id}/matches/{match_id}/undo`** — Revert merge and cleanly restore original graph nodes.

---

## 8. Cryptographic Audit & Court Dossier Endpoints

### 8.1 View Audit Trail
* **`GET /audit`**
  - **Query Parameters:** `case_id` (Optional), `limit` (Default: 50), `offset`.
  - **Returns:** Immutable chronological ledger entries with previous hash and block hash.

### 8.2 Verify Chain of Custody Integrity
* **`GET /audit/verify`**
  - **Description:** Recalculates SHA-256 chain from Genesis block.
  - **Response `200 OK`:**
    ```json
    {
      "verified": true,
      "total_blocks": 1420,
      "tampered_block_id": null
    }
    ```

### 8.3 Compile Court Dossier PDF
* **`POST /cases/{id}/report`**
  - **Request Body:** `{"title": "Forensic Exhibit A", "sections": ["summary", "graph", "money_trail", "audit_chain"]}`
  - **Response `201 Created`:** Generated report record with SHA-256 fingerprint.

### 8.4 Download Court Dossier
* **`GET /reports/{id}/download`**
  - **Returns:** Certified Section 63 BSA 2023 compliant PDF file stream.

---

## 9. Extraction V2 — Merge Engine, Master Sheet & Conflict Resolution Endpoints

### 9.1 Merge Preview & Apply
* **`POST /cases/{id}/evidence/{eid}/merge/preview`**
  - **Description:** Computes deterministic dry-run merge counts (`new`, `same`, `updated`, `new_fields`, `conflicts`, `rejected`) and sample diffs for an evidence file without writing to the database.
* **`POST /cases/{id}/evidence/{eid}/merge/apply`**
  - **Description:** Creates an `ingestion` job, merges evidence records into the unified store (`extraction_records`, `field_claims`, `golden_fields`, `merge_conflicts`), rebuilds the case graph (`rebuild_graph(case_id)`), and appends `INGEST_APPLY` to `audit_log`.
* **`POST /cases/{id}/evidence/{eid}/rollback`**
  - **Description:** Creates an `ingestion` job, soft-retracts all claims from `eid`, re-runs field resolution on affected records, marks records with zero active claims as `retracted` (`is_active=False`), rebuilds the case graph, and appends `INGEST_ROLLBACK` to `audit_log`.

### 9.2 Unified Record Browser & Claim History
* **`GET /cases/{id}/records`**
  - **Query Parameters:** `type` (Record type filter), `status` (Default: `active`), `q` (Search across `data_json` and `extra_json`), `page` (Default: `1`), `page_size` (Default: `50`).
  - **Returns:** Paginated unified records with resolved known fields, dynamic `extra_json` fields, and confirming source evidence IDs.
* **`GET /cases/{id}/entities/{eid}/history`** & **`GET /cases/{id}/records/{rid}/history`**
  - **Returns:** Full append-only `field_claims` history and current `golden_fields` selection per field (including locked status and reason code).

### 9.3 Field Conflict Queue & Officer Resolution
* **`GET /cases/{id}/conflicts`**
  - **Query Parameters:** `status` (Default: `open`).
  - **Returns:** List of field-level merge conflicts with full competing `field_claims` metadata.
* **`POST /conflicts/{cid}/resolve`** (and **`POST /cases/{id}/conflicts/{cid}/resolve`**)
  - **Request Body:** `{"selected_claim_id": "...", "custom_value": null, "reason": "Verified against primary statement"}`
  - **Description:** Locks `golden_fields` (`selected_by='officer'`, `locked=True`), marks conflict `resolved`, updates `extraction_records` and linked staging rows, calls `rebuild_graph(case_id)`, and logs `CONFLICT_RESOLVE` to `audit_log`.

### 9.4 Dynamic Master Sheet Export & Ingest Runs
* **`GET /cases/{id}/master-sheet`**
  - **Query Parameters:** `format` (`json`, `csv`, `xlsx`), `view` (`wide`, `per_type`).
  - **Headers:** `X-Export-SHA256` (SHA-256 hex digest of exported bytes).
  - **Description:** Exports all active unified records for the case with the full union of known schema columns and dynamically discovered `extra_json` columns, plus provenance (`_sources`, `_confidence`, `_status`), and logs `EXPORT` to `audit_log`.
* **`GET /cases/{id}/ingest-runs`**
  - **Returns:** Chronological changelog of merge `apply` and `rollback` runs with counts and timestamps.

### 9.5 Investigator Annotations (Soft-Delete Only)
* **`POST /cases/{id}/annotations`** — Create an investigator annotation on a `record` or `entity` (logs `create_annotation` to `audit_log`).
* **`GET /cases/{id}/annotations`** — List annotations for a case (`subject_id`, `include_deleted`).
* **`DELETE /cases/{id}/annotations/{aid}`** — Soft-delete an annotation (`is_deleted=True`, logs `soft_delete_annotation` to `audit_log`).

### 9.6 Scanned PDF, Image & Handwritten OCR Review Endpoints (Phase 5)
* **`GET /evidence/{id}/pages`**
  - **Description:** Lists all pages/frames of an evidence document or image with `source_kind` (`text_layer_pdf`, `ocr_printed`, `ocr_handwritten`), `status` (`ready`, `needs_better_image`, `pending_review`, `ocr_unavailable`), OpenCV `quality_metrics`, `mean_confidence`, `perceptual_hash`, `duplicate_of_evidence_id`, and `exif` metadata (`"disclaimer": "as reported by file"`).
* **`GET /evidence/{id}/pages/{n}/ocr`**
  - **Description:** Returns per-word OCR bounding boxes (`bbox: [x0, y0, x1, y1]`), word confidences, script guesses, `raw_text` (immutable), `corrected_text`, and extracted entities with their page bounding boxes.
* **`POST /evidence/{id}/pages/{n}/corrections`**
  - **Request Body:** `{"word_id": "p1_w5", "span": null, "corrected_text": "9876543210", "note": "Verified on physical FIR"}`
  - **Description:** Applies an officer word or span correction without overwriting `raw_text`, re-extracts affected entities, stores them as locked officer claims (`source_kind='officer'`, `locked=True`) via the Merge Engine, and logs `OCR_CORRECTION` to `audit_log`.
* **`PATCH /evidence/{id}/handwritten`**
  - **Request Body:** `{"is_handwritten": true}`
  - **Description:** Marks or unmarks an evidence file as handwritten and re-runs extraction with `source_kind='ocr_handwritten'`, confidence capped by `extraction.ocr.handwritten_conf_cap`, and mandatory `pending_review` status.

### 9.7 FIR Understanding, IPC ↔ BNS Mapping & Completeness (Phase 6)
* **`GET /evidence/{id}/fir-analysis`**
  - **Description:** Returns structured FIR `facts` (`fir_no`, `police_station`, `incident_date`, `incident_time`, `incident_place`, `complainant`, `sections`) with character spans, `sections` with `IPC ↔ BNS` / `CrPC ↔ BNSS` / `IT Act` reference mappings (`"disclaimer": "reference — verify against the official gazette"` or `"mapping unavailable"`), chronological incident `timeline`, `relationship_proposals` (`status='pending_review'`), and per-FIR `completeness` report.

### 9.8 Phone Intelligence, Potential Anomaly Flags & Completeness (Phase 7)
* **`GET /cases/{id}/completeness`**
  - **Description:** Returns case-level completeness (`case_completeness_score` in `0.0..1.0`, documented `score_formula`), per-file completeness reports (`files`), `missing_fields_summary`, `date_range_gaps`, `disabled_detectors`, `cross_file_consistency` (`balance_discrepancies`, `overlapping_period_conflicts`, `same_identifier_different_names`, `statement_owner_mismatches`), and `potential_anomalies`.
* **`GET /evidence/{id}/completeness`**
  - **Description:** Returns per-evidence completeness (`completeness_score`, `missing_fields`, `date_range_gaps`, `disabled_detectors`, `score_formula`) and persists it in `EvidenceFile.quality_json`.
* **`GET /cases/{id}/anomalies`** & **`POST /cases/{id}/anomalies/evaluate`**
  - **Description:** Evaluates and returns Potential Anomaly flags (`label: "Potential Anomaly"`, `rule_code`, `triggered_threshold`, `evidence_refs`, `explanation`) across pattern checks, international/VoIP numbers in domestic context, cross-case shared identifiers (strictly scoped by `CaseMember`), multi-name identifiers, and CDR behavioral rules (`NIGHT_CALL_RATIO_ANOMALY`, `HIGH_SHORT_DURATION_COUNTERPARTIES`, `IMEI_MULTIPLE_MSISDN`, `MSISDN_MULTIPLE_IMEI`, `SHORT_ACTIVITY_WINDOW`), persisting them to `alerts`.
* **`GET /cases/{id}/numbers/{number}/intelligence`**
  - **Description:** Returns honest phone number intelligence (`format_valid`, `number_type`, `region`, `carrier_hint` + `carrier_disclaimer: "original allocation — may be ported"`, `line_status: "unverified"`, `status_label: "Format valid — ownership unverified"`, digit-pattern anomaly check, and cross-case presence scoped by case membership).

---

## 10. Error Conventions & HTTP Status Codes

| Code | Meaning | Typical Trigger |
| :--- | :--- | :--- |
| **`200 OK`** | Success | Query returned data successfully |
| **`201 Created`** | Created | Resource successfully created (Case, Evidence, Report) |
| **`202 Accepted`**| Accepted | Ingestion / recomputation job queued in background |
| **`400 Bad Request`**| Invalid Input | Missing mandatory fields, corrupted file format |
| **`401 Unauthorized`**| Unauthenticated | Missing or expired JWT token |
| **`403 Forbidden`**| Access Denied | Officer lacks role permission or is not a case member |
| **`404 Not Found`**| Not Found | Requested case, entity, or evidence ID does not exist |
| **`422 Unprocessable`**| Validation Error | Pydantic schema validation failure |
| **`500 Internal Error`**| Server Error | Unexpected error; logged to secure error repository |
