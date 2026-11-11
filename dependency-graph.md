# Dependency Graph & Critical Files (dependency-graph.md) — Case Connect AI

This document maps module interdependencies, identifies critical core files, and outlines change-impact blast radiuses across the platform.

---

## 1. Critical Core System Files (DO NOT MODIFY LIGHTLY)

The following files represent the structural foundation of the system. Unvetted edits to these files can invalidate Section 63 BSA legal compliance or cause cascade database corruption:

| Critical File | Invariants Protected | Blast Radius |
| :--- | :--- | :--- |
| `backend/app/db/sql.py` | 31 SQLAlchemy relational models, primary keys, foreign key constraints, integer paise precision. | **CRITICAL:** Affects all database queries, migrations, and ORM serialization across the backend. |
| `backend/app/audit/logging_sanitizer.py` | Cryptographic SHA-256 hash chaining, PII regex redaction filter in Python logging streams. | **HIGH:** Any regression leaks PII into server logs or breaks statutory audit admissibility. |
| `backend/app/config.py` & `backend/config/defaults.yaml` | Zero-hardcoding contract, extractor version computation, security limits, regex validators. | **HIGH:** Controls all system tunables. Removing keys causes startup crashes. |
| `backend/app/services/merge/engine.py` | Deterministic natural key generation, field claim trust ordering, golden field selection. | **CRITICAL:** Core data layer for Extraction Module V2. Dictates active vs retracted records. |
| `backend/app/cases/deps.py` | BOLA / IDOR defense verifying authenticated officer membership on every case docket. | **CRITICAL:** Access control boundary. Regressions expose cases across tenants. |
| `scripts/audit_hardcode.py` | Mandatory pre-commit gate verifying zero mock data, synthetic names, or hardcoded values. | **HIGH:** Automated compliance check required on all PRs. |

---

## 2. High-Impact Service Dependencies

```
[backend/app/main.py]
   │
   ├── [backend/app/config.py] <── [backend/config/defaults.yaml]
   │
   ├── [backend/app/db/sql.py] ──> [backend/app/db/neo4j.py]
   │
   ├── [backend/app/cases/deps.py] <── [backend/app/auth/router.py]
   │
   ├── [backend/app/services/ingestion/]
   │      ├── [safety.py] (ZIP bomb, XML defuser, path sanitization)
   │      ├── [readers.py] (Universal CSV, multi-sheet XLSX, PDF tables)
   │      ├── [validators.py] (Verhoeff, Luhn, IFSC, IST dates)
   │      └── [jobs.py] (Per-case locks, cooperative cancel, progress)
   │
   ├── [backend/app/services/extraction/]
   │      ├── [text.py] (PyMuPDF text-layer router & OCR preprocessing)
   │      ├── [pipeline.py] (spaCy NER, legal entities, FIR patterns)
   │      └── [masking.py] (Response-layer PII masking serializer)
   │
   ├── [backend/app/services/merge/]
   │      ├── [match.py] (Natural key hashing & occurrence indexing)
   │      ├── [resolve.py] (Deterministic trust ranking & conflict creation)
   │      └── [engine.py] (Transaction orchestration & rollback)
   │
   └── [backend/app/services/reports/router.py] ──> [backend/app/services/reports/pdf.py] (ReportLab Section 63 BSA)
```

---

## 3. Frontend Component & State Flow

```
[frontend/src/App.jsx]
   │
   ├── [context/AuthContext.jsx] (Bcrypt/JWT session state)
   │
   ├── [context/CaseFlowContext.jsx] (Active case, view transitions)
   │
   ├── [components/shell/Header.jsx] & [components/shell/IndiaMapBackground.jsx]
   │
   ├── [components/upload/UploadScreen.jsx]
   │      └── Calls: POST /cases/{id}/evidence/upload
   │
   ├── [components/case/MainCaseDossier.jsx]
   │      ├── [components/network/NetworkCanvas.jsx] (Cytoscape Graph)
   │      ├── [components/money/MoneyTrailFlow.jsx] (BFS Money DAG)
   │      ├── [components/analytics/CommPatternsView.jsx] (CDR Curfew Spikes)
   │      ├── [components/cases/SavedCasesModal.jsx] (Dossier Ledger)
   │      └── [components/chat/CopilotDrawer.jsx] (AI Copilot)
   │
   └── [services/api.js] (Axios client with Bearer token interceptor)
```

---

## 4. Third-Party Binary & Environment Dependencies

| External Tool / CLI | Installation Method | Fallback Behavior |
| :--- | :--- | :--- |
| **Tesseract OCR** | UB-Mannheim Windows binary (`hin` + `eng` traineddata) | Graceful error: *"Tesseract OCR binary not found at configured path. Install UB-Mannheim Tesseract with hin+eng."* (Zero stack traces). |
| **Neo4j 5.x** | Docker container (`bolt://localhost:7687`) | Automatic graceful fallback to NetworkX in-memory graph traversal. System status reports `sqlite_online_neo4j_offline`. |
| **OpenRouter / Gemini** | Windows Environment Registry (`OPENROUTER_API_KEY`) | Air-gapped local mode: cloud AI disabled by default. Enabled strictly with officer consent per case. |
| **Serena Agent** | `uv tool install -p 3.13 serena-agent` | MCP lazy loaded server. |
| **Context7** | `npm install -g ctx7` | Global CLI and MCP documentation search. |

