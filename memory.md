# Codebase Memory (memory.md) — Case Connect AI

**Product Name:** Case Connect AI — Criminal Network Analysis System  
**Document Type:** Permanent Codebase Memory & Master Brain  
**Authoritative Standard:** Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)  
**Security Classification:** Law Enforcement Sensitive / Restricted  
**Last Updated:** Phase 8 Completed / Ready for Phase 9  

---

## 1. Project Overview & Business Purpose

### 1.1 Business Problem
Indian Law Enforcement Agencies (State Police Cyber Cells, CID, Crime Branches, Central Special Units) deal with fragmented, heterogeneous digital evidence in complex criminal syndicates and financial cyber-fraud:
- **Telecom circle Call Detail Records (CDRs)** in multi-column unstructured CSV/Excel files.
- **Commercial bank account statements** (dozens of differing layouts, merged headers, running balance footers, NEFT/RTGS/IMPS/UPI narrations).
- **Subscriber Detail Records (SDR / KYC)** with unstructured Hindi/English address strings.
- **First Information Reports (FIRs)** in free-text police registers or mobile photos of handwritten dockets.
- **Evidentiary Chain-of-Custody Requirements:** Under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023), digital evidence is only judicially admissible if a cryptographic chain of custody (SHA-256 genesis linkage) proves it has not been tampered with or modified since seizure.

### 1.2 Target Users & Operational Workflows
- **Supervising Officers / SP / ACP:** Reviewing executive crime syndicate summaries, Section 63 BSA statutory dossiers, and officer audit logs.
- **Investigating Officers (IO) & Cyber Analysts:** Ingesting multi-source evidence, linking phone numbers to bank accounts, tracing money trails through rapid pass-through layering accounts, inspecting call frequency heatmaps, and identifying syndicates.
- **Court Prosecutors:** Presenting admissible, cryptographically signed forensic PDF reports.

---

## 2. Technology Stack & Key Libraries

| Layer | Primary Technology | Key Libraries & Specifications |
| :--- | :--- | :--- |
| **Backend Engine** | Python 3.11+ (FastAPI) | `fastapi`, `pydantic` v2, `uvicorn`, `httpx` |
| **Database (Authoritative)** | SQLite 3 (WAL Mode) | `sqlalchemy` 2.0 (Strictly parameterized queries, 31 models) |
| **Graph Index (Disposable)** | Neo4j 5.x / NetworkX | `neo4j` Python driver, `networkx` for in-memory graph fallback |
| **Forensic NLP & NER** | spaCy (`en_core_web_sm`) | Deterministic regex rule matchers, Indian legal entity extractors |
| **Tabular & Document Extraction** | PyMuPDF (`fitz`), `pdfplumber` | `pytesseract` (OCR), `openpyxl`, `charset-normalizer`, `defusedxml` |
| **Statutory Dossier Engine** | ReportLab 4.x | Cryptographic SHA-256 page watermarking, Section 63 BSA certificates |
| **Authentication & Crypto** | Bcrypt (12 rounds) & PyJWT | HS256 JWT tokens, SHA-256 hash chains |
| **Frontend Framework** | React 18 + Vite | `cytoscape` (fcose layout), `recharts`, `lucide-react`, Tailwind CSS |
| **API Gateway / Proxy** | Express / Node.js 18+ | `server/index.js` (Reverse proxy with CORS and streaming support) |

---

## 3. Repository Structure

```
Case-Connect/
├── backend/
│   ├── app/
│   │   ├── audit/            # Cryptographic SHA-256 chain of custody & logging sanitizer
│   │   ├── auth/             # Bcrypt salted hashing & JWT bearer token lifecycle
│   │   ├── cases/            # Case dockets, RBAC membership, settings, and reveal API
│   │   ├── db/               # 31 SQLAlchemy models (sql.py) & Neo4j graph connector (neo4j.py)
│   │   ├── evidence/         # Multi-format ingestion, magic-byte checks, column mapping
│   │   ├── services/         # Pure forensic domain logic
│   │   │   ├── ai/           # Local/Gemini copilot & forensic narrative generator
│   │   │   ├── analytics/    # CDR nocturnal analysis, MAD volume spikes, centrality
│   │   │   ├── extraction/   # PyMuPDF/OCR/spaCy pipeline, validators, PII masking
│   │   │   ├── graph/        # NetworkX / Neo4j projection and multi-hop traversal
│   │   │   ├── ingestion/    # Resilient readers, jobs, concurrency locks, safety defense
│   │   │   ├── matching/     # Phonetic Soundex & string similarity identity matching
│   │   │   ├── merge/        # Unified extraction record store, field claims, conflict resolution
│   │   │   ├── money/        # Multi-layer BFS money trail & pass-through mule detection
│   │   │   └── reports/      # Section 63 BSA ReportLab court dossier generator
│   │   ├── config.py         # Pydantic BaseSettings & centralized provenance version
│   │   └── main.py           # FastAPI entrypoint, HTTP security headers, CORS, router mounting
│   ├── config/
│   │   ├── defaults.yaml     # Zero hardcoding: all system tunables and thresholds
│   │   └── reference/        # IFSC bank codes, FIR patterns, IPC-BNS legal mappings
│   └── tests/                # 148+ pytest unit and integration tests
├── frontend/
│   ├── src/
│   │   ├── components/       # Atomic UI components, case dossiers, modals, Cytoscape canvas
│   │   ├── context/          # AuthContext, CaseFlowContext
│   │   ├── pages/            # Cases, CaseDetail, AuditLog, Login, QuickCrimeAnalyser
│   │   ├── services/         # Axios API clients
│   │   ├── styles/           # Tailwind CSS & design tokens
│   │   └── App.jsx           # Client-side router and state orchestrator
│   └── package.json
├── docs/                     # Architectural specifications, audits, API contracts, guides
├── scripts/                  # Init DB, seed users, generate synthetic data, hardcode auditor
└── server/index.js           # Node gateway reverse proxy
```

---

## 4. System Architecture & Core Invariants

### 4.1 Invariant Rules (AGENTS.md)
1. **INSPECT BEFORE EDITING:** Inspect existing implementations and tests before touching code.
2. **ZERO HARDCODING:** Neither backend nor frontend may contain synthetic names, phone numbers, account constants, or fixed dates. All tunables reside in `backend/config/defaults.yaml`.
3. **ZERO MOCK DATA IN PRODUCTION PATHS:** Unstaged cases return clean `[]` or `{}`. UIs display actionable empty states.
4. **SQLITE IS AUTHORITATIVE:** Neo4j is a disposable index. SQLite writes happen first, followed by `rebuild_graph(case_id)`, then cryptographic append to `audit_log`.
5. **AI SUGGESTS, HUMAN DECIDES:** No automated identity merges. Identity resolution requires explicit officer action with full reversibility.
6. **OBJECTIVE FORENSIC TERMINOLOGY:** Strictly prohibited: "criminal", "suspect", "guilty", "mastermind", "fake". Mandatory neutral phrasing: "Lead for review", "High-priority entity", "Potential Anomaly", "Unverified".
7. **MONETARY PRECISION:** All currency is stored as integer **PAISE** (`amount_paise`). Floating point math for currency is strictly prohibited.

---

## 5. End-to-End Data Flow

```
[Evidence File (CSV/XLSX/PDF/IMG)]
       │
       ▼
1. Safety Checks: Magic-byte inspection, ZIP bomb defense, XML defusing, path sanitization
       │
       ▼
2. Reader Ingestion: Encoding detection, multi-page table stitching, preamble/footer cleanup
       │
       ▼
3. Column Mapping & Content Profiling: Match headers + data distributions; officer confirmation
       │
       ▼
4. Normalization & Validation: Verhoeff Aadhaar, Luhn IMEI, IFSC check, Dayfirst IST->UTC dates
       │
       ▼
5. Unified Merge Engine: Natural key hashing, field claims, deterministic trust ordering, conflict detection
       │
       ▼
6. Authoritative Persistence: SQLite (31 models) -> rebuild_graph(case_id) -> SHA-256 Audit Log
       │
       ▼
7. Graph Analytics & Forensics: NetworkX/Neo4j traversal, BFS money layering, CDR nocturnal spikes
       │
       ▼
8. Court Admissibility: Section 63 BSA ReportLab PDF dossier generation with cryptographic hashes
```

---

## 6. Authentication, RBAC & Privacy Protection

- **Password Storage:** Salted Bcrypt with 12 rounds (`scripts/seed_users.py`).
- **Token Format:** HS256 JWT tokens containing `sub` (username), `role`, and expiration.
- **RBAC Roles:**
  - `admin`: Full system privileges, user management, unrestricted audit log access, PII reveal.
  - `investigator`: Case creation, evidence upload, merge resolution, report generation, PII reveal.
  - `viewer`: Read-only access to assigned cases, masked PII, cannot mutate state or reveal PII.
- **BOLA / IDOR Defense:** Every case-scoped endpoint validates case membership via `backend/app/cases/deps.py`.
- **Response-Layer PII Masking:** Aadhaar (`XXXX-XXXX-1234`), PAN (`XXXXXX1234`), phone (`XXXXXX4321`), bank account (`XXXXXXXX1234`) are masked by default. Revealing unmasked data requires officer role, justification logging, and generates a tamper-evident audit record.

---

## 7. Current Extraction Module V2 Status (Phases 0–11)

- **Phase 0 (Audit & Safety Net):** Completed (`docs/EXTRACTION_AUDIT.md`, commit `41b3797`).
- **Phase 1 (Normalization & Validators):** Completed (Verhoeff, Luhn, IFSC, IST dates, commit `c210678`).
- **Phase 2 (Robust Readers & Column Profiling):** Completed (Multi-page PDF, cp1252, commit `9d4eb06`).
- **Phase 3 (Unified Record Store & Merge Engine):** Completed (Natural keys, claims, conflicts, commit `d4969cf`).
- **Phase 4 (Merge APIs & Master Sheet Export):** Completed (Job-based apply/rollback, commit `4aa3b8f`).
- **Phase 5 (Scanned PDFs, Images & OCR):** Completed (PyMuPDF routing, Tesseract, commit `de12e2d`).
- **Phase 6 (FIR Understanding & IPC-BNS):** Completed (Role-aware rules, IPC-BNS mapping, commit `d559f94`).
- **Phase 7 (Phone Intelligence & Anomalies):** Completed (Format validation, completeness, commit `871cff4`).
- **Phase 8 (Security Hardening & Hostile Defense):** Fully implemented & verified (18/18 tests passing).
- **Phase 9 (Frontend Extraction UI):** Ready to implement upon user approval.
- **Phase 10 (Media/Audio Transcription):** Optional feature-flagged module.
- **Phase 11 (Final Evaluation & Main Merge):** Final documentation and clean merge.

