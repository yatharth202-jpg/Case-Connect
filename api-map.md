# API Map & Interface Inventory (api-map.md) — Case Connect AI

This document provides a detailed API specification for all backend endpoints, documenting HTTP methods, paths, request payloads, response bodies, dependencies, and consuming frontend components.

---

## 1. Authentication & Session APIs

### `POST /auth/login`
- **Purpose:** Authenticate officer via username and salted bcrypt password, issuing an HS256 JWT bearer token.
- **Used By:** `frontend/src/pages/Login.jsx`, `frontend/src/context/AuthContext.jsx`.
- **Input Payload:**
  ```json
  {
    "username": "investigator1",
    "password": "OfficerPass1234!"
  }
  ```
- **Output Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "role": "investigator",
    "user_id": "usr_94f83b2a"
  }
  ```
- **Database Access:** `users` table.

### `GET /auth/me`
- **Purpose:** Fetch current active session profile, permissions, and active case assignments.
- **Used By:** `frontend/src/context/AuthContext.jsx`, `frontend/src/components/shell/Header.jsx`.
- **Input:** Bearer Token in `Authorization` header.
- **Output Response (200 OK):**
  ```json
  {
    "id": "usr_94f83b2a",
    "username": "investigator1",
    "role": "investigator",
    "is_active": true
  }
  ```

---

## 2. Case Management & Dossier APIs

### `GET /cases`
- **Purpose:** Retrieve all case dockets accessible to the officer.
- **Used By:** `frontend/src/pages/Cases.jsx`, `frontend/src/components/cases/SavedCasesModal.jsx`.
- **Output Response:** Array of case summary objects including ID, title, status, evidence counts, and created date.

### `POST /cases`
- **Purpose:** Initialize a new criminal investigation case docket.
- **Input Payload:**
  ```json
  {
    "title": "FIR 142/2026 Cyber Cell Mumbai",
    "description": "Multi-tier SIM syndicate financial layering investigation",
    "assigned_officer": "investigator1"
  }
  ```
- **Database Access:** `cases`, `case_members`, `audit_log`.

### `POST /cases/{id}/reveal`
- **Purpose:** Reveal unmasked PII (full Aadhaar, PAN, phone, account) for an entity or record under strict statutory justification.
- **Used By:** Unmask / Reveal Modal (`frontend/src/components/case/MainCaseDossier.jsx`).
- **Input Payload:**
  ```json
  {
    "entity_id": "ent_33b8a10",
    "statutory_justification": "Section 63 BSA production order under Hon'ble Special Court",
    "field_names": ["phone", "bank_account"]
  }
  ```
- **Output Response:** Unmasked data dictionary + SHA-256 audit log identifier.
- **Audit Requirement:** Appends tamper-evident entry to `audit_log` with officer username, case ID, justification, and timestamp.

---

## 3. Evidence Ingestion & Mapping APIs

### `POST /cases/{id}/evidence/upload`
- **Purpose:** Multi-file evidence staging with magic-byte validation, ZIP bomb checks, and path traversal sanitization.
- **Used By:** `frontend/src/components/upload/UploadScreen.jsx`.
- **Input:** `multipart/form-data` with `files` list.
- **Output Response:** List of staged `evidence_files` records with SHA-256 hashes, file sizes, and detected mime types.

### `POST /cases/{id}/evidence/detect`
- **Purpose:** Content-based column profiling, encoding detection, and header vocab matching.
- **Input:** `{ "evidence_id": "evi_837b29a" }`
- **Output Response:** Top candidate record types (CDR, Bank Statement, SDR, FIR) and suggested column mappings with confidence scores.

### `POST /cases/{id}/evidence/ingest`
- **Purpose:** Dispatch asynchronous chunked parsing and staging job.
- **Output Response:** `{ "job_id": "job_119a02d", "status": "processing" }`

---

## 4. Extraction & OCR APIs

### `POST /cases/{id}/evidence/{eid}/extract`
- **Purpose:** Extract named entities, dates, legal sections, and phone numbers via spaCy and regex rules.
- **Database Access:** `evidence_files`, `extracted_entities`, `document_facts`.

### `GET /cases/{id}/evidence/{eid}/pages/{page}/ocr`
- **Purpose:** Fetch OCR per-word bounding box coordinates and confidence levels for image/scanned PDF review.
- **Used By:** Document Text & OCR Review Drawer.

### `POST /cases/{id}/evidence/{eid}/pages/{page}/corrections`
- **Purpose:** Submit officer text corrections to OCR output, creating locked claims with highest trust rank.
- **Database Access:** `evidence_pages`, `field_claims`, `golden_fields`, `audit_log`.

---

## 5. Unified Record Store & Merge APIs

### `POST /cases/{id}/evidence/{eid}/merge/preview`
- **Purpose:** Dry-run comparison of new evidence against existing case records; returns counts of new records, identical records, new fields, and conflicts.
- **Output Response:**
  ```json
  {
    "counts": {
      "new_records": 142,
      "same_records": 89,
      "new_fields": 12,
      "conflicts": 3,
      "rejected": 0
    },
    "sample_changes": []
  }
  ```

### `POST /cases/{id}/evidence/{eid}/merge/apply`
- **Purpose:** Commit merged records and claims, resolve golden values, rebuild graph projection, and append to audit log.
- **Database Access:** `extraction_records`, `field_claims`, `golden_fields`, `merge_conflicts`, `ingest_runs`, `audit_log`.

### `POST /cases/{id}/evidence/{eid}/rollback`
- **Purpose:** Retract all claims and records originating from specified evidence file, restoring previous golden fields.

### `GET /cases/{id}/master-sheet`
- **Purpose:** Export consolidated tabular master sheet (JSON, CSV, XLSX) covering all entities and records with dynamic extra fields.
- **Output Headers:** Returns `X-Export-SHA256` checksum header for evidentiary verification.

---

## 6. Graph, Money & Analytics APIs

### `GET /cases/{id}/graph`
- **Purpose:** Deliver Cytoscape-formatted JSON elements (`nodes`, `edges`) with centrality metadata and suspiciousness scores.
- **Used By:** `frontend/src/components/network/NetworkCanvas.jsx`.

### `GET /cases/{id}/money-trail`
- **Purpose:** Compute BFS layered money flow DAG and detect pass-through layering mule accounts.
- **Used By:** `frontend/src/components/money/MoneyTrailFlow.jsx`.

### `GET /cases/{id}/analytics/comm-patterns`
- **Purpose:** Analyze nocturnal curfew calls (IST 00:00-05:00), frequency bursts, and duration anomalies.
- **Used By:** `frontend/src/components/analytics/CommPatternsView.jsx`.

---

## 7. Court Dossier & Audit APIs

### `POST /cases/{id}/reports/generate`
- **Purpose:** Compile Section 63 BSA 2023 certified forensic court dossier with ReportLab.
- **Output:** `{ "report_id": "rep_9371bca", "sha256": "8f3e...", "download_url": "/api/cases/.../download" }`

### `GET /audit/verify`
- **Purpose:** Re-hash the complete sequential SHA-256 genesis audit chain and mathematically prove zero database tampering.
- **Output Response:** `{ "verified": true, "total_events": 1420, "broken_links": 0 }`

