# CaseConnect AI — Extraction Module V1 Baseline Audit (`EXTRACTION_AUDIT.md`)

**Date:** 2026-11-09  
**Starting Tag:** `pre-extraction-v2`  
**Target Branch:** `feature/extraction-v2`  
**Baseline Test Result:** `84 passed, 2 skipped` (`pytest backend/tests -q`), `[PASS] 0 violations` (`python scripts/audit_hardcode.py`), `frontend build passed in 5.85s`.

---

## Detailed Audit Findings (Questions a–n)

### a. Date Parsing, Timezones & Curfew Logic
- **Dayfirst Handling:** `normalize_datetime()` in `backend/app/services/ingestion/normalize.py:145-218` accepts a static parameter `dayfirst: bool = True` (`line 145`) and first tries a hardcoded list of `strptime` formats (`lines 162-177`) before falling back to `dateutil.parser.parse(s, dayfirst=dayfirst)` (`line 188`). It does **not** infer `dayfirst` per column by scanning whether the first or second component exceeds `12`. Furthermore, if parsing fails completely, it silently falls back to a hardcoded date `datetime(2026, 1, 1, 0, 0, 0)` (`line 194`) instead of flagging or rejecting the date.
- **Naive Timestamps (IST vs UTC):** Naive timestamps are formatted directly as `f"{d_str}T{t_str}Z"` (`normalize.py:217`), which falsely labels local Indian Standard Time (`Asia/Kolkata`, UTC+05:30) timestamps from CDRs and bank statements as UTC (`Z`) without converting them or recording `tz_source`.
- **Curfew / Nocturnal Logic:** `backend/app/services/analytics/comm_patterns.py:11-23` (`parse_date_str`) strips `Z` and parses only the date (`str(d_str)[:10]`, `line 16`) without timezone conversion; there is no dedicated IST timezone conversion helper for 00:00–05:00 curfew checks in `comm_patterns.py`.

### b. Phone, Account, Aadhaar, PAN & Identifier Regexes
- **Checksums & Validation:**
  - Tabular phone normalization (`backend/app/services/ingestion/normalize.py:9-52`) strips non-digits, removes leading `91` (if 12 digits) or `0` (if 11 digits), and checks `len(digits) == 10 and digits[0] in "6789"` (`line 46`). It does not use `phonenumbers` for carrier/region/type metadata or masked number (`XXXXXX1234`) flags.
  - Document regex extraction (`backend/app/services/extraction/rules.py:9-46`) defines `PHONE_REGEX` (`line 9`), `VEHICLE_REGEX` (`line 10`), `EMAIL_REGEX` (`line 11`), `IP_REGEX` (`line 12`), `UPI_REGEX` (`line 13`), `FIR_REGEX` (`line 14`), and `ACCOUNT_TRIGGER_REGEX` (`line 27`).
  - **Missing Validators:** Neither `normalize.py` nor `rules.py` implements Aadhaar 12-digit Verhoeff checksum validation, PAN format + entity-type letter validation, IMEI 15-digit Luhn checksum validation, or IFSC `^[A-Z]{4}0[A-Z0-9]{6}$` + bank code lookup.
- **10-Digit Account vs Phone Collision:**
  - In `backend/app/services/ingestion/detect.py:38-40`, `MOBILE_REGEX` runs before `ACCOUNT_REGEX` (`elif ACCOUNT_REGEX.match(clean_digits)`), so any 10-digit account number starting with 6–9 is counted as a mobile number during type sniffing.
  - In `backend/app/services/extraction/rules.py:91-108`, a 10-digit number starting with 6–9 is treated as `BANK_ACCOUNT` only if preceded within 40 characters by `account|a/c|acct|beneficiary`; otherwise it is unconditionally labeled as `PHONE` (`lines 110-120`), even in banking contexts or tables without those exact trigger words.

### c. Header Row / Preamble Detection & Messy File Edge Cases
- **Header Row & Preamble Detection:** `detect_header_row()` in `backend/app/services/ingestion/readers.py:46-81` scans the first 40 non-empty rows and picks the single row with the highest token match against `column_synonyms.yaml`. Rows above `best_idx` are returned as `banner_rows` (`lines 75-78`).
- **Repeated Headers:** Not handled (`readers.py:148-155`, `178-186`). Repeated header rows in multi-page exports are ingested as data rows (and either rejected or corruptly staged).
- **Footer Totals / Opening & Closing Balances:** `is_trailing_total_row()` (`readers.py:83-90`) only checks if the first two cells contain `TOTAL`, `SUMMARY`, or `GRAND TOTAL`. It does not detect `Opening Balance`, `Closing Balance`, or `Brought Forward` rows, nor does it capture opening/closing balances into file metadata.
- **Merged Cells & Multi-Sheet Excel:** `read_xlsx_file()` (`readers.py:159-187`) reads **only one sheet** (`sheet_names[0]` unless `target_sheet` is passed, `line 164`), uses `values_only=True` without unmerging/filling merged header cells, and ignores secondary sheets (`Tower_Metadata`, etc.).
- **Non-UTF8 CSV:** `read_csv_file()` (`readers.py:108-123`) loops through a fixed list `["utf-8-sig", "utf-8", "cp1252", "latin-1"]` instead of using `charset-normalizer` confidence detection.
- **Multi-Page PDF Tables:** `read_tabular_file()` (`readers.py:92-106`) only supports `.csv`, `.xlsx`, `.json`, `.jsonl` — it raises `ValueError("Unsupported tabular extension: .pdf")` (`line 106`). PDF bank statements cannot be ingested as tabular transactions at all.

### d. File Type Detection & Mixed Files
- **Detection Mechanism:** `detect_file_type()` in `backend/app/services/ingestion/detect.py:87-159` combines header synonym scores (`score_header_matches`), cell regex ratios (`sniff_value_types`), and filename substring bonuses (`"cdr"`, `"bank"`, `"statement"`, `"sdr"`). Any `.pdf`, `.docx`, or `.txt` is hardcoded by filename extension to return `"text_document"` (`lines 93-99`).
- **Mixed Files:** Not supported. A single `detected_type` string is assigned per file (`detect.py:146-158`). Workbooks with multiple sheets of different types or CSVs with mixed sections are forced into a single type.

### e. Bank Statement Account Owner Determination
- In `backend/app/services/ingestion/stage.py:45-51`, if `statement_account` is not passed in the request, it scans `banners` for `"account no"` or `"a/c no"` and grabs the first digit token of length $\ge 8$.
- **Silent Fallback Bug:** If no account number is found in the banner or column, `stage.py:207` falls back to a hardcoded string literal `"PRIMARY_ACCOUNT"` (`stmt_acct = normalize_account(statement_account or get_val("statement_account") or "PRIMARY_ACCOUNT")`) and counterparty falls back to `"COUNTERPARTY_UNKNOWN"` (`line 237`), creating synthetic graph nodes for `"PRIMARY_ACCOUNT"` and `"COUNTERPARTY_UNKNOWN"` instead of pausing for `needs_owner_confirmation`.

### f. Row Fingerprint & Legitimate Duplicate Rows
- `compute_row_fingerprint()` in `backend/app/services/ingestion/stage.py:20-23` hashes:
  - CDR (`lines 103-109`): `{t: "cdr", c: caller, r: receiver, dt: iso_str, d: duration}`.
  - Bank Transactions (`lines 165-172`): `{t: "txn", fa: from_account, ta: to_account, amt: amt_paise, dt: iso_str, ref: ref}`.
  - Bank Statements (`lines 245-252`): `{t: "stmt", fa: from_acc, ta: to_acc, amt: amt_paise, d: d_str, ref: ref}`.
- **Legitimate Identical Rows Dropped:** Because `occurrence_idx` within the same file is not tracked and `d_str` (date without time) is used for statements (`line 250`), two legitimate identical transfers on the same day (e.g., two ₹5,000 IMPS transfers with the same narration/empty ref in the same file) produce the exact same `fingerprint`, causing the second legitimate transaction to be silently skipped (`duplicates_skipped += 1`, `lines 254-257`).

### g. Re-Ingest Behavior After Mapping Changes
- In `backend/app/services/ingestion/stage.py:70-386`, re-ingesting an evidence file after changing its column mapping **does not clean up or retract** rows previously staged from that `evidence_id`. Old rows remain in `call_records`, `transactions`, `ip_events`, and `entities` (since `source_file` stores `ev.original_name` rather than `evidence_id`, and old fingerprints differ when mapping changes), resulting in duplicate/ghost rows mixed with the new rows.

### h. Mapping Templates Application
- In `backend/app/services/ingestion/router.py:95-100`, when `preview_evidence_mapping` finds a matching `header_signature` in `mapping_templates`, it returns `suggested = {h: {"canonical": saved_tpl.get(h, "ignore"), "confidence": 1.0} for h in headers}` without checking content drift (whether column data types changed) and without returning normalized preview rows or top-3 candidate alternatives.

### i. Synchronous vs Job Ingestion & Large File Behavior
- `POST /evidence/{evidence_id}/ingest` (`backend/app/services/ingestion/router.py:167-222`) creates a `Job` row and schedules `run_ingestion_job` via FastAPI `BackgroundTasks`.
- However:
  1. `GET /evidence/{evidence_id}/preview` (`router.py:91`), `POST /evidence/{evidence_id}/mapping` (`router.py:147`), and `POST /evidence/{evidence_id}/ingest` (`router.py:192`) all call `read_tabular_file(file_path)` **synchronously inside the HTTP request**, loading the **entire file into memory** (`records` list of dicts) before returning!
  2. `stage_evidence_file()` (`stage.py:42`) reads all rows into memory at once and commits once at the very end (`line 386`) without chunked streaming or per-chunk progress updates.
  3. `POST /evidence/{evidence_id}/extract` (`backend/app/services/extraction/router.py:149-174`) runs OCR, spaCy NER, and Gemini synchronously inside the HTTP request without creating a background `Job`.

### j. Person Entity Keying & FIR Relationship Extraction
- **Person Entity Keying:** In `stage.py:293-304` (identity tables) and `extraction/router.py:77-88` (approved FIR entities), `Person` entities are keyed in the `entities` table with `canonical_id = canon_name` (lowercase name string, e.g., `"rahul sharma"`). Furthermore, `graph/builder.py:201-213` auto-creates `Person` nodes directly from transaction `from_name`/`to_name` lowercase strings (`f"{case_id}|Person|{norm_name}"`). This means two different people with the same name share a node, while name variations split until `matching/service.py` runs.
- **FIR Relationships:** `backend/app/services/extraction/ner.py:465-611` (`extract_cooccurrence_relationships`) extracts co-occurrence candidate relationships (`ALIAS_OF`, `DRIVES`, `USES`, `OWNS`, `OPERATES`, `COURIER_FOR`, `MENTIONED_IN`, `TRANSFERRED_TO`, `ACCOMPLICE_OF`, `COMMUNICATED_WITH`) as `ExtractedEntity` rows with `entity_type="RELATIONSHIP"` and `status="pending_review"`, plus `extraction/router.py:91-147` auto-creates `MENTIONED_IN` links when `PERSON` and `FIR` entities are approved. However, relationship patterns in `ner.py` are hardcoded in Python rather than loaded from `backend/config/reference/fir_patterns.yaml`, and there is no IPC↔BNS section mapper or incident timeline fact extractor.

### k. OCR Support & Outbound Network Calls (Air-Gap Safety)
- **OCR:** `backend/app/services/extraction/text.py:9-43` attempts to import `rapidocr_onnxruntime` (which is not listed in `backend/requirements.txt`!) and `pypdfium2` (`line 100`). It returns only a flat string (`\n`.join(lines)) with **zero word-level confidence scores, zero bounding boxes, zero image quality checks (blur/skew/DPI), zero preprocessing, and zero handwriting classification**. Devanagari text triggers a warning `"partially supported: Devanagari text ignored"` (`lines 220-221`).
- **Outbound Network Calls Violation:** `backend/app/services/extraction/pipeline.py:56-64` automatically calls `extract_entities_with_gemini(p_text, p_name)` whenever `GEMINI_API_KEY` is non-empty in `.env` (`backend/app/services/ai/gemini_service.py:135`), sending up to 5,000 characters of raw FIR evidence text (`gemini_service.py:183`) to `https://generativelanguage.googleapis.com/...` **without a config enablement flag, without per-case officer consent, and without writing an `audit_log` entry!**

### l. File Safety (Size Limits, ZIP, Filenames, XML)
- **Size Limits:** Hardcoded in `backend/app/evidence/router.py:20-38` (`MAX_TABULAR_SIZE = 200 MB`, `MAX_DOC_SIZE = 20 MB`, `MAX_IMAGE_SIZE = 30 MB`) instead of reading from `defaults.yaml`.
- **Filename Handling:** `original_name = Path(file.filename).name` (`evidence/router.py:138`) is appended directly to the disk filename (`f"{file_uuid}_{original_name}"`, `line 149`) without sanitizing special characters or length.
- **ZIP Handling:** `.zip` bulk evidence uploads are not supported at all (`ALLOWED_EXTENSIONS` in `evidence/router.py:24-38`), and there is no zip-bomb protection (compression ratio, max files, max uncompressed size, nesting depth).
- **XML Parsing:** `.xlsx` and `.docx` are parsed directly by `openpyxl` and `python-docx` without `defusedxml` protection against XML entity expansion / billion-laughs attacks.

### m. Existing Tests & Synthetic Data Usage
- `backend/tests/` contains 16 test modules (`test_analytics.py`, `test_audit.py`, `test_audit_chain.py`, `test_auth.py`, `test_cases.py`, `test_evidence.py`, `test_extraction.py`, `test_generator.py`, `test_graph.py`, `test_health.py`, `test_ingestion.py`, `test_matching.py`, `test_money_trail.py`, `test_multi_dataset.py`, `test_phase9.py`, `test_reports.py`) plus `conftest.py`.
- `backend/tests/test_generator.py:8-142` and `backend/tests/test_multi_dataset.py:33-199` invoke `SyntheticDataGenerator` from `scripts/generate_data.py` with deterministic seeds (`42`, `101`, `102`) and topologies (`ring`, `two_rings`, `chain`, `hub_spoke`, `benign_heavy`, `cdr_only`, `bank_only`, `sparse_tiny`) to test ingestion, graph building, analytics, and extraction without committing static mock files.
- `backend/tests/test_ingestion.py:35-190` generates runtime CSV/XLSX buffers in `tmp_path` to test column mapping, statement direction parsing, and staging deduplication.
- `backend/tests/test_extraction.py:40-450` uses programmatic text strings, runtime `.txt`/`.docx`/`.pdf`/`.png` files, and monkeypatched OCR/Gemini handlers to test regex rules, spaCy NER, relationship extraction, and approval routes.

### n. Master Defect-to-Phase Resolution Matrix

| Problem / Gap | Exists Today? | Where (`file:line`) | Fixed In Phase |
| :--- | :---: | :--- | :---: |
| Naive timestamps labeled as UTC (`Z`) without IST conversion; fallback to `2026-01-01` | **Yes** | `services/ingestion/normalize.py:145-218`, `services/analytics/comm_patterns.py:11-23` | **Phase 1** |
| No per-column `dayfirst` inference across date values | **Yes** | `services/ingestion/normalize.py:145-190` | **Phase 1** |
| Missing Verhoeff (Aadhaar), Luhn (IMEI), PAN, IFSC bank lookup & Devanagari digit conversion | **Yes** | `services/ingestion/normalize.py:9-66`, `services/extraction/rules.py:9-121` | **Phase 1** |
| 10-digit account numbers misclassified as phone numbers when trigger words absent | **Partly** | `services/ingestion/detect.py:38-40`, `services/extraction/rules.py:91-120` | **Phase 1 & 2** |
| Single-sheet Excel reading, merged header cells not unmerged, no `charset-normalizer` usage | **Yes** | `services/ingestion/readers.py:108-187` | **Phase 2** |
| Repeated headers & opening/closing balance rows not captured as metadata | **Yes** | `services/ingestion/readers.py:46-90` | **Phase 2** |
| PDF bank statements rejected by tabular reader (`Unsupported tabular extension: .pdf`) | **Yes** | `services/ingestion/readers.py:92-106` | **Phase 2** |
| Bank statement with unknown owner silently defaults to `"PRIMARY_ACCOUNT"` | **Yes** | `services/ingestion/stage.py:207, 237` | **Phase 2** |
| Mapping templates applied with `confidence: 1.0` without content profiling or drift check | **Yes** | `services/ingestion/router.py:95-102`, `services/ingestion/mapping.py:48-114` | **Phase 2** |
| Synchronous full-file memory load during preview/mapping/ingest | **Yes** | `services/ingestion/router.py:91, 147, 192`, `services/ingestion/stage.py:42` | **Phase 2 & 8** |
| Legitimate identical rows dropped due to missing `occurrence_idx` in fingerprint | **Yes** | `services/ingestion/stage.py:20-23, 103-115, 165-177, 245-257` | **Phase 3** |
| Re-ingest after mapping change leaves orphan/duplicate rows; no field-level claims or conflict tracking | **Yes** | `services/ingestion/stage.py:70-386` | **Phase 3** |
| Unknown/extra columns silently dropped during staging | **Yes** | `services/ingestion/stage.py:70-382` | **Phase 3** |
| No merge preview, rollback per evidence file, conflict resolution API, or wide Master Sheet export | **Yes** | `services/ingestion/router.py` (missing endpoints) | **Phase 4** |
| Scanned PDFs & images lack quality gate, deskew/denoise, word bbox/confidence, and handwriting review queue | **Yes** | `services/extraction/text.py:9-43, 97-120, 194-210` | **Phase 5** |
| Unconsented outbound Gemini API call during document extraction | **Yes** | `services/extraction/pipeline.py:56-64`, `services/ai/gemini_service.py:161-226` | **Phase 5 & 8** |
| Hardcoded FIR regexes/roles in `ner.py`, no IPC↔BNS reference map, no FIR completeness check | **Partly** | `services/extraction/ner.py:6-288, 465-611` | **Phase 6** |
| Missing phone status metadata, cross-case anomaly checks, date-gap & detector completeness engine | **Yes** | `services/analytics/comm_patterns.py`, `services/ingestion/router.py:266-291` | **Phase 7** |
| Hardcoded upload size limits, no safe ZIP bulk upload, no `defusedxml`, no PII masking/reveal audit | **Yes** | `evidence/router.py:20-38, 137-198` | **Phase 8** |
| Frontend lacks OCR word-box review, Merge Preview modal, Conflict Queue, Master Sheet, Completeness UI | **Yes** | `frontend/src/components/` | **Phase 9** |
| Local audio/video transcription & frame OCR (`faster-whisper` + `FFmpeg` + `imagehash`) | **Yes** | Not implemented | **Phase 10** |
| Quantitative precision/recall/F1 evaluation report (`EXTRACTION_EVAL.md`) & V2 architecture docs | **Partly** | `scripts/eval_extraction.py` | **Phase 11** |
