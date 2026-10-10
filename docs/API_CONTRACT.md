# Case Connect AI — REST API Contract

All endpoints follow REST principles with standard JSON responses.
Production code paths contain **zero mock data**. If no data has been uploaded for a case, endpoints return clean empty arrays / structures, and UI displays empty states.

---

## 1. Standard Response Shapes

### 1.1 Error Shape
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested case could not be found or access is denied."
  }
}
```

### 1.2 Job Response Shape
```json
{
  "id": "job_94a73e8f-7c12-4211-8be4-7a31b6e680a1",
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

### 1.3 Standard Graph Response Shape
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
    }
  ],
  "edges": [
    {
      "id": "edge_123",
      "source": "case1|Person|rahul_sharma",
      "target": "case1|Phone|9876543210",
      "type": "USES",
      "props": {
        "calls": 14,
        "confidence": 0.95,
        "method": "structured"
      }
    }
  ],
  "truncated": false,
  "meta": {
    "hops": 3,
    "count_nodes": 1,
    "count_edges": 1
  }
}
```

---

## 2. Authentication & User Management

* **`POST /auth/login`**
  - **Body**: `{"username": "...", "password": "..."}`
  - **Returns**: `{"access_token": "...", "token_type": "bearer", "user": {"id": "...", "username": "...", "role": "admin | investigator | viewer"}}`
* **`GET /auth/me`**
  - **Header**: `Authorization: Bearer <token>`
  - **Returns**: Current user profile and assigned cases.
* **`GET /users`** *(Admin only)*
  - **Returns**: `[{"id": "...", "username": "...", "role": "...", "is_active": true}]`
* **`POST /users`** *(Admin only)*
  - **Body**: `{"username": "...", "password": "...", "role": "..."}`
* **`PATCH /users/{id}`** *(Admin only)*
  - **Body**: `{"role": "...", "is_active": "..."}`

---

## 3. Case Management & Settings

* **`POST /cases`**
  - **Body**: `{"title": "...", "description": "...", "priority": "high | medium | low"}`
  - **Returns**: Created case details.
* **`GET /cases`**
  - **Returns**: List of cases accessible to the authenticated officer.
* **`GET /cases/{id}`**
  - **Returns**: Case details, evidence file summary, status, assigned members.
* **`GET /cases/{id}/settings`**
  - **Returns**: Active case threshold and weight configuration (merged from defaults and overrides).
* **`PUT /cases/{id}/settings`** *(Investigator / Admin)*
  - **Body**: Updated thresholds/weights dictionary. Audited.

---

## 4. Evidence Upload & Ingestion Engine

* **`POST /cases/{id}/evidence`** *(Multipart upload)*
  - Computes SHA-256 fingerprint, validates file integrity.
  - Runs format sniffing and column synonym matching.
  - **Returns**: `{"evidence_id": "...", "filename": "...", "sha256": "...", "detected_type": "cdr | bank_transactions | bank_statement | identity_table | ip_log | text_document", "suggested_mapping": {...}, "preview": [...first 20 rows...], "issues": [...]}`
* **`GET /cases/{id}/evidence`**
  - **Returns**: List of evidence files with SHA-256 hashes, status, row counts.
* **`GET /evidence/{id}`**
  - **Returns**: Details, column mapping, verification status, file preview.
* **`POST /evidence/{id}/mapping`**
  - **Body**: Confirmed column mapping overrides and format options. Audited.
* **`POST /evidence/{id}/ingest`**
  - Initiates asynchronous cleaning, staging, deduplication and graph indexing job.
  - **Returns**: Job object.
* **`POST /evidence/{id}/verify`**
  - Re-computes SHA-256 hash against disk file to verify chain of custody integrity.
  - **Returns**: `{"verified": true | false, "stored_hash": "...", "computed_hash": "..."}`
* **`GET /evidence/{id}/rejected-rows`**
  - **Returns**: Rejected rows with row numbers, raw values, and rejection reasons.
* **`GET /mapping-templates`**
  - **Returns**: Saved column mapping templates keyed by header signature hash.
* **`GET /jobs/{id}`**
  - **Returns**: Current progress percentage and step states of background jobs.

---

## 5. Knowledge Graph & Multi-Hop Exploration

* **`GET /cases/{id}/graph/search`**
  - **Query Params**: `q` (name, phone, account), `hops` (1..4), `view` (`entity` | `detail`), `types` (comma-separated), `limit` (default 200).
  - **Returns**: Standard Graph Response with candidate picker if multiple matches exist.
* **`GET /cases/{id}/graph/path`**
  - **Query Params**: `from` (node ID), `to` (node ID), max length 6.
  - **Returns**: Shortest path between two entities with highlighted intermediate edges.
* **`POST /cases/{id}/links`** *(Investigator)*
  - Officer-created manual link (e.g. assigning phone to person). `method='officer'`, audited.
* **`DELETE /cases/{id}/links/{link_id}`** *(Investigator)*
  - Undo officer link. Audited, re-syncs projection.

---

## 6. Money Trail Explorer

* **`GET /cases/{id}/money-trail`**
  - **Query Params**: `account` (account ID), `min_amount` (paise), `hops` (1..4), `direction` (`in` | `out` | `both`).
  - **Returns**: Graph response with directed transfer edges, account aggregate totals (inflow, outflow, throughput), ordered paths, and `hidden_edges` (edges below threshold for grey-dashed drawing).

---

## 7. Extraction, Review & Master Profiles

* **`GET /evidence/{id}/text`**
  - **Returns**: Per-page extracted text paragraphs and recognized entity spans.
* **`GET /cases/{id}/extracted`**
  - **Query Params**: `status` (`pending_review` | `approved` | `rejected`), `type`, `min_conf`, `evidence_id`.
* **`PATCH /extracted/{id}`**
  - Edit or change status of extracted entity span. Audited.
* **`POST /cases/{id}/extracted`**
  - Manually insert an entity observed in text. `method='officer'`.
* **`POST /cases/{id}/extracted/approve-all`**
  - Bulk approve pending extractions above given confidence threshold. Audited.
* **`GET /cases/{id}/matches`**
  - **Query Params**: `level` (`HIGH` | `MEDIUM` | `SHARED_DEVICE` | `LOW`), `status` (`pending` | `approved` | `rejected` | `undone`).
* **`POST /matches/{id}/approve`** | **`POST /matches/{id}/reject`** | **`POST /matches/{id}/undo`**
  - Human-in-the-loop entity merge decisions. Resolves to MasterProfile without deleting original nodes.
* **`GET /cases/{id}/profiles`**
  - List of resolved Master Profiles.
* **`GET /cases/{id}/profiles/{profile_id}`**
  - Master profile detail: known aliases, linked phones, bank accounts, vehicles, linked FIRs, timeline, and source provenance.

---

## 8. Analytics & Anomaly Detection

* **`GET /cases/{id}/analytics/overview`**: Core case stats (files, rows, nodes, edges, money volume).
* **`GET /cases/{id}/analytics/calls-per-day`**: Daily communication time series with detected spike flags.
* **`GET /cases/{id}/analytics/txn-volume`**: Daily transaction volumes with percentile quantiles (p50, p75, p90, p99).
* **`GET /cases/{id}/analytics/top-entities`**: Top entities ranked by degree, call count, or financial throughput.
* **`GET /cases/{id}/analytics/communities`**: NetworkX Louvain community clusters.
* **`GET /cases/{id}/analytics/degree-distribution`**: Node degree distribution histogram.
* **`GET /cases/{id}/analytics/call-heatmap`**: Weekday x Hour call frequency matrix.
* **`POST /cases/{id}/analytics/recompute`**: Background job to recompute network metrics upon threshold changes.

---

## 9. Lead Advisor & Provenance

* **`GET /cases/{id}/leads`**
  - Suggested leads ranked by explainable priority score (0..100) and confidence.
  - Signals: `money_flow`, `bridge`, `unusual_communication`, `timing`, `multi_document`.
  - Signal explanations with real numbers and thresholds.
* **`GET /cases/{id}/entities/{entity_id}/why`**
  - Detailed breakdown of why an entity was flagged, matched patterns, missing data checklist, and recommended legal next steps.
* **`POST /cases/{id}/leads/{lead_id}/decision`**
  - Officer decision: `accept` | `reject` | `need_more_data` with investigator notes. Audited.
* **`GET /cases/{id}/provenance`**
  - **Query Params**: `edge_id` or `node_id`.
  - Returns source evidence file name, row/page number, extraction method, confidence, and approving officer.

---

## 10. Timeline, Audit Log & Reports

* **`GET /cases/{id}/timeline`**
  - **Query Params**: `entity`, `type`, `from`, `to`.
  - Chronological sequenced events (FIR dates, peak call spikes, high-value transfers, alerts).
* **`GET /cases/{id}/alerts`**
  - Detected communication and financial anomalies (spikes, bridge positions, fan-in, pass-through).
* **`GET /cases/{id}/saved-views`** | **`POST /cases/{id}/saved-views`** | **`DELETE /cases/{id}/saved-views/{view_id}`**
  - Save and reopen graph canvas exploration state.
* **`GET /audit`**
  - **Query Params**: `case_id`. Paginated immutable audit trail.
* **`GET /audit/verify`** *(Admin)*
  - Validates cryptographic SHA-256 hash chain of the audit log. Returns `{ok: true, checked: N}` or broken entry ID.
* **`POST /cases/{id}/report`**
  - Generates court-ready PDF investigation report with file fingerprints, graph visual, timeline, and audit extract.
* **`GET /cases/{id}/reports`**
  - List of generated reports.
* **`GET /reports/{id}/download`**
  - Stream PDF download.
