# Extraction Module V2 — Architectural Specification & Operations Manual

**Document Version:** 2.0.0  
**Legal Standard:** Bharatiya Sakshya Adhiniyam, 2023 (BSA Section 63)  
**System Classification:** Local-First Forensic Intelligence & Natural Key Record Store  
**Authoritative References:** PRD.md, ARCHITECTURE.md, DATABASE.md, API.md, DESIGN.md  

---

## 1. Executive Summary & Core Engineering Philosophy

CaseConnect AI Extraction V2 transforms law-enforcement evidentiary processing from fragile heuristics into an immutable, verifiable, and reversible forensic ledger.

### 1.1 The Golden Principles
1. **SQLite is the Immutable Source of Truth:** Neo4j and NetworkX graphs are disposable projections that can be dropped and rebuilt at any time via `rebuild_graph(case_id)`.
2. **Competing Claims Model (No Blind Overwrites):** Evidence files never overwrite database cells. Every ingested field is stored as an independent, timestamped claim with source provenance, extraction method, and confidence score.
3. **Reversible Ingestion & Rollback:** Any ingested file can be retracted cleanly without affecting claims contributed by other evidence sources.
4. **Forensic Integrity & Zero Floating-Point Drift:** All monetary amounts are stored strictly as 64-bit integer paise (`amount_paise`). Currency math never uses floating-point numbers.
5. **Human-in-the-Loop Adjudication:** AI suggests probabilistic links; sworn officers make statutory determinations. All identity mergers and conflict resolutions require human confirmation.
6. **Statutory Neutral Terminology:** Under BSA 2023, prejudicial language (e.g., "criminal", "guilty", "mastermind", "fraud number") is strictly prohibited in system logs, API schemas, and user interfaces. Entities are designated as `Primary Attributed Lead`, `Potential Anomaly`, or `Format valid — ownership unverified`.

---

## 2. End-to-End Extraction & Ingestion Pipeline

```
Evidence Ingestion (Tabular, Documents, Images, Audio, Video)
  │
  ▼
[Content-Based MIME & Magic Byte Gate]
  │  ├── Reject corrupted / hostile headers
  │  └── Prevent file extension spoofing
  ▼
[Resilient Readers Layer]
  │  ├── Tabular: Multi-sheet Excel, CSV/JSONL, Header detection, Dialect sniffing
  │  ├── Documents: PyMuPDF text-layer extraction, OCR fallback
  │  ├── Scanned Images/PDFs: Preprocessing (deskew, contrast, blur), Tesseract OCR
  │  └── Media: Local faster-whisper (Audio) + FFmpeg keyframe OCR (Video)
  ▼
[Forensic Normalization & Checksum Validation]
  │  ├── Phones: E.164 + 10-digit Indian MSISDN normalization
  │  ├── Aadhaar: Verhoeff algorithm check digit validation
  │  ├── IMEI: Luhn algorithm check digit validation
  │  ├── Banking: IFSC prefix validation (170+ RBI bank codes) & Account normalization
  │  ├── Currency: Day-first date parsing (UTC) + integer paise conversion
  │  └── PAN / UPI / Vehicles: Strict regex & format validation
  ▼
[Unified Record Store & Claims Ledger]
  │  ├── ExtractionRecord: Natural key deduplication by tuple (case_id, record_type, natural_key, occurrence_idx)
  │  ├── RecordFieldClaim: Per-field provenance, confidence, extraction method, trust rank
  │  └── ExtractedEntity: Individual atomic forensic identifiers with char spans & bboxes
  ▼
[Merge Engine & Conflict Adjudication]
  │  ├── Pre-flight Dry-Run: MergePreviewModal (new, unchanged, updated, conflicts)
  │  ├── Automated Merge: Best-claim selection governed by source_trust_order
  │  ├── Conflict Queue: Competing claims within conflict_confidence_margin flagged for review
  │  └── Officer Decision Locking: Locked fields take precedence over automated claims
  ▼
[Graph Projection & Master Sheet Export]
  │  ├── Synchronized SQLite -> Neo4j / NetworkX graph sync
  │  ├── Section 63 BSA SHA-256 genesis-chained audit log entry
  │  └── Master Sheet Export: Virtualized tabular projection with SHA-256 certification
```

---

## 3. Merge Engine & Conflict Resolution Algorithm

### 3.1 Natural Keys
Records are mapped to deterministic natural keys based on their intrinsic forensic identity:
* **Call Records:** Deterministic hash of `(caller_phone, receiver_phone, timestamp_utc, duration_seconds)`.
* **Financial Transactions:** Deterministic hash of `(from_account, to_account, timestamp_utc, amount_paise)`.
* **IP Communication Events:** Deterministic hash of `(source_ip, destination_ip, timestamp_utc, port)`.
* **SDR Profile Records:** Deterministic hash of normalized phone number.

### 3.2 Source Trust Order
When multiple files contribute competing claims for the same natural key, the active value is resolved by the hierarchical trust order configured in `backend/config/defaults.yaml`:
```yaml
merge:
  source_trust_order:
    - "officer_confirmed"      # Officer manual adjudication or edit (locked)
    - "court_order"            # Judicial disclosures / legal notices
    - "sdr_official"           # Official telecom subscriber disclosure
    - "bank_official"          # Certified bank statement / RTGS receipt
    - "telecom_cdr"            # Raw telecom carrier switch log
    - "ocr_printed"            # Machine-printed OCR document
    - "ocr_handwritten"        # Handwritten diary / seizure memo (capped at 0.50)
    - "asr_audio"              # Speech-to-text transcript from surveillance
```

### 3.3 Conflict Generation Thresholds
A `MergeConflict` is generated when:
$$\Delta_{\text{conf}} = |\text{Confidence}_{\text{Claim A}} - \text{Confidence}_{\text{Claim B}}| \le \text{conflict\_confidence\_margin}$$
Where default `conflict_confidence_margin` is `0.15`.
* If $\Delta_{\text{conf}} > 0.15$, the higher-trust claim is accepted automatically.
* If $\Delta_{\text{conf}} \le 0.15$ or trust ranks are equal with conflicting values, the dispute is queued in the `ConflictQueue` for officer adjudication.

### 3.4 Reversible Provenance Rollback
When an evidence file is retracted:
1. All claims where `evidence_id == target_evidence_id` are purged.
2. The remaining claims for affected records are re-evaluated using the trust order.
3. If no claims remain for a record, the record is removed from the master sheet.
4. Downstream graph nodes and relationships are invalidated and projected afresh.
5. The rollback event is appended to the cryptographic SHA-256 audit log.

---

## 4. Configuration Parameter Reference (`backend/config/defaults.yaml`)

| Configuration Key | Default Value | Description / Operational Role |
| :--- | :--- | :--- |
| `extraction.default_region` | `"IN"` | Default ISO country code for telephone parsing |
| `extraction.timezone_display` | `"Asia/Kolkata"` | Display timezone for curfew and investigative reports |
| `extraction.date_parse.dayfirst_inference`| `true` | Enables automatic DD/MM/YYYY vs MM/DD/YYYY heuristic |
| `extraction.amount.indian_grouping` | `true` | Parses Lakhs/Crores grouping (e.g. `1,50,000.00`) |
| `extraction.validators.aadhaar_checksum`| `true` | Enforces Verhoeff check-digit algorithm for Aadhaar |
| `extraction.validators.imei_luhn` | `true` | Enforces Luhn mod-10 algorithm for IMEI numbers |
| `extraction.ocr.languages` | `["eng", "hin"]` | Tesseract language models loaded for document OCR |
| `extraction.ocr.handwritten_conf_cap` | `0.50` | Maximum confidence ceiling for handwritten OCR text |
| `extraction.ocr.review_below_conf` | `0.70` | Threshold below which OCR words enter officer review queue |
| `extraction.media.enabled` | `false` | Master toggle for local Audio/Video speech extraction |
| `extraction.media.whisper_model` | `"base"` | Model size for local faster-whisper transcription |
| `extraction.masking.fields` | `["aadhaar", "account", "pan", "phone"]` | Identifiers masked by default in response serializer |
| `extraction.masking.reveal_roles` | `["admin", "investigator"]` | Officer roles permitted to request statutory unmasking |
| `merge.conflict_confidence_margin` | `0.15` | Confidence delta generating a merge conflict dispute |
| `merge.min_confidence_auto_accept` | `0.85` | Minimum confidence score for un-reviewed merge acceptance |

---

## 5. Forensic Limitations & Statutory Disclaimers

1. **Carrier Metadata Disclaimer:** Telecommunication carrier CDR records indicate switch routing and cell tower connectivity. They do not constitute statutory proof of subscriber physical custody or individual device operation without corroborative surveillance or forensic seizure.
2. **Handwriting Probabilistic Ceiling:** OCR results on handwritten documents are probabilistic approximations and must not be used as sole evidentiary facts without officer verification.
3. **Statutory PII Protection (Section 63 BSA 2023):** Unmasking of Aadhaar, PAN, bank accounts, or telephone numbers requires sworn justification and creates an immutable cryptographic record in `audit_log`.
