# CaseConnect AI — Baseline Verification Flows

**Document Version:** 1.0.0  
**Baseline Date:** 12 November 2026  
**Status:** Verified Operational Baseline for System Upgrade  
**Statutory Framework:** Section 63, Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)  

---

## 1. Executive Summary

This document specifies the ten (10) operational flows that constitute the baseline functionality of CaseConnect AI prior to the v2 full upgrade. Every listed flow has been validated through automated tests (`backend/tests`), anti-hardcoding audits, and end-to-end frontend builds. Under the non-negotiable **DO-NOT-BREAK PROTOCOL**, all existing flows must remain fully functional and backward-compatible after every upgrade phase.

---

## 2. Inventory of Baseline Flows

### Flow 1: Authentication, RBAC & Case Membership (BOLA / IDOR Defense)
- **Description:** Officers authenticate via `/auth/login` receiving salted bcrypt (12 rounds) verified HS256 JWT bearer tokens. Roles (`admin`, `lead`, `investigator`, `viewer`) dictate read/write permissions. Every case-scoped endpoint enforces `get_case_for_user` to block Broken Object Level Authorization (BOLA/IDOR).
- **Verification Method:**
  - Automated tests: `backend/tests/test_auth.py`, `backend/tests/test_phase8_security_hardening.py`
  - Validated 401 on missing tokens, 403 on viewer write attempts, and 404/403 on non-member case access.

### Flow 2: Case Docket Creation & Management
- **Description:** Sworn officers create cases with FIR numbers, police station names, and crime descriptions. Cases establish cryptographic genesis anchors for audit logging.
- **Verification Method:**
  - Automated tests: `backend/tests/test_cases.py`
  - Validated case lifecycle transitions (`active`, `closed`, `archived`) and case member assignments.

### Flow 3: Evidence File Ingestion & Multi-MIME Safety Gate
- **Description:** Secure ingestion endpoint (`POST /cases/{case_id}/evidence/upload`) accepts CSV, XLSX, PDF, DOCX, ZIP, Audio, and Video files. Files undergo magic-byte header inspection (preventing extension spoofing), ZIP-bomb compression ratio verification (<= 100:1), and defused XML inspection on DOCX files.
- **Verification Method:**
  - Automated tests: `backend/tests/test_evidence.py`, `backend/tests/test_phase1_readers.py`, `backend/tests/test_phase8_security_hardening.py`
  - Validated rejection of disguised executable files, oversized archive members, and corrupted headers.

### Flow 4: Dynamic Tabular Reading, Preamble Stripping & Column Mapping
- **Description:** `readers.py` discovers multi-sheet Excel files, detects preambles (skipping bank statement headers up to 30 rows), sniffs CSV delimiters/encodings, and matches column headers against canonical forensic schemas. The frontend `MappingPreviewModal.jsx` displays raw-to-canonical alignment for officer confirmation before staging.
- **Verification Method:**
  - Automated tests: `backend/tests/test_phase1_readers.py`, `backend/tests/test_phase2_ingestion.py`
  - Validated automatic detection of Airtel, Jio, VI, BSNL CDRs and SBI, HDFC, ICICI, Axis bank statement layouts.

### Flow 5: Asynchronous Ingestion & Normalization to Integer Paise
- **Description:** Cooperative background worker (`Job`) stages rows in 5,000-row batches. Phone numbers are normalized to 10-digit MSISDNs (`valid_mobile` flag). All financial amounts are converted to 64-bit integer paise (`amount_paise`). Invalid rows are recorded in `rejected_rows` with precise statutory rejection reasons.
- **Verification Method:**
  - Automated tests: `backend/tests/test_phase2_ingestion.py`, `scripts/audit_hardcode.py`
  - Validated zero floating-point currency drift across all staged financial tables.

### Flow 6: Extraction V2 Pipeline (Rules, NLP, OCR & Media)
- **Description:**
  - Deterministic rules: Indian Mobile, Aadhaar Verhoeff check-digit, IMEI Luhn check-digit, 170+ RBI bank IFSC codes, PAN, UPI VPAs, and Indian vehicle registration numbers.
  - NLP: Local spaCy (`en_core_web_sm`) entity extraction from FIRs; bidirectional IPC to BNS section mapping.
  - OCR: OpenCV preprocessing (deskew, binarization) + Tesseract dual-language (`hin+eng`) OCR.
  - Media: Local faster-whisper ASR audio transcription + FFmpeg keyframe extraction.
- **Verification Method:**
  - Automated tests: `backend/tests/test_phase3_rules.py`, `backend/tests/test_phase4_ner.py`, `backend/tests/test_phase5_ocr.py`, `backend/tests/test_phase10_media.py`, `scripts/eval_extraction.py` (100% Precision & Recall).

### Flow 7: Competing Claims Ledger & Conflict Adjudication
- **Description:** Evidence ingestion never overwrites cells. Extracted fields are stored as `RecordFieldClaim` entries. Active values are determined by the 8-tier `source_trust_order` (`officer_confirmed` > `court_order` > `sdr_official` > `bank_official` > `telecom_cdr` > `ocr_printed` > `ocr_handwritten` > `asr_audio`). Disputed claims within a 0.15 confidence margin are queued in `ConflictQueue.jsx` for officer review.
- **Verification Method:**
  - Automated tests: `backend/tests/test_phase6_claims.py`
  - Validated clean file rollback: retracting an evidence file removes its claims without affecting other sources.

### Flow 8: Identity Deduplication & Reversible Merging
- **Description:** Probabilistic and deterministic matching via Jaro-Winkler, Levenshtein, and Soundex. Candidate pairs are proposed to officers via `MergePreviewModal.jsx`. Identity merges require explicit officer confirmation and support instantaneous 1-click rollback (`POST /cases/{case_id}/merge/undo`).
- **Verification Method:**
  - Automated tests: `backend/tests/test_phase7_merge.py`
  - Validated zero automated guilt assertions and full reversibility of merged profiles.

### Flow 9: Graph Visualization & Advanced Forensic Analytics
- **Description:** Authoritative SQLite records are projected into Cytoscape.js canvas (`fcose` layout) and Neo4j/NetworkX. Analytics modules execute:
  - Rapid Pass-Through BFS / Hawala mule detection.
  - Median Absolute Deviation (MAD) financial surge detection.
  - Topological centrality metrics (Degree, Betweenness, PageRank).
- **Verification Method:**
  - Automated tests: `backend/tests/test_graph.py`, `backend/tests/test_analytics.py`
  - Validated responsive rendering of multi-hop network graphs (`*1..4` hops) with zero external cloud dependencies.

### Flow 10: Section 63 BSA 2023 Certification & Master Evidence Export
- **Description:** Every state change appends to an immutable SHA-256 rolling hash chain in `audit_log`. The system automatically compiles legally admissible Section 63 BSA 2023 digital evidence certificates with cryptographic watermarks via ReportLab. `MasterSheetTab.jsx` provides virtualized tabular inspection with SHA-256 export verification.
- **Verification Method:**
  - Automated tests: `backend/tests/test_audit.py`, `backend/tests/test_reports.py`
  - Validated cryptographic chain linkage: `Hash_n = SHA256(Hash_{n-1} + Timestamp + UserID + Action + ObjectID + Details)`.
