# Case Connect AI — Criminal Network Analysis System

> **Statutory Evidence Aggregator & Explainable Investigation Engine**  
> *Compliant with Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)*

Case Connect AI is an enterprise-grade forensic investigation platform engineered for Indian Law Enforcement Agencies (State Police Cyber Cells, Crime Branches, and Central Special Cells). It unifies fragmented evidence streams—Call Detail Records (CDRs), multi-bank statement exports, mobile Subscriber Detail Records (SDR), IP event logs, and police First Information Reports (FIRs)—into a single high-integrity investigation graph with explainable lead recommendations and tamper-evident audit trails.

---

## 1. Quickstart — Run Locally in 6 Commands

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker Desktop (or Neo4j Community Server 5.x)
- Git

```bash
# 1. Clone repository
git clone https://github.com/unitx/case-connect-ai.git
cd case-connect-ai

# 2. Run system preflight validator
python scripts/preflight.py

# 3. Setup backend environment and install dependencies
python -m venv .venv
.venv\Scripts\activate  # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt

# 4. Setup frontend dependencies
cd frontend && npm install && cd ..

# 5. Initialize database, seed schema & test accounts
python scripts/reset_db.py --force
python scripts/seed_users.py

# 6. Launch platform servers (FastAPI backend + Vite frontend)
python scripts/start.py
```

Open browser to **`http://localhost:5173`**  
- **Admin**: `admin` / `AdminPass1234!`
- **Investigator**: `investigator1` / `OfficerPass1234!`
- **Viewer**: `viewer1` / `ViewerPass1234!`

---

## 2. System Architecture

```mermaid
graph TD
    subgraph Evidence Ingestion & Chain of Custody
        A[Evidence Upload: CDR / Bank / SDR / FIR / IP] --> B[SHA-256 Hasher & Magic Byte Validator]
        B --> C[Universal Tabular Parser & Dynamic Column Mapper]
        C --> D[SQLite Staging Repository: Canonical Paise, Mobile, ISO Dates]
    end

    subgraph Forensic Analytics Engine
        D --> E[Median Absolute Deviation MAD Call Spike Detector]
        D --> F[Rapid Pass-Through & Layering BFS Money Trail Engine]
        D --> G[Soundex & Jaro-Winkler Entity Deduplication]
        D --> H[5-Signal Explainable Lead Advisor Engine]
    end

    subgraph Presentation & Legal Export
        E --> I[Executive Recharts Dashboard & Heatmap]
        F --> J[Directed Cytoscape Money Trail Explorer]
        G --> K[Master Profile Resolution & Human Approval Portal]
        H --> L[Chronological Unified Timeline & Pre-FIR Anomaly Banner]
        I & J & K & L --> M[ReportLab Section 63 BSA 2023 Court-Ready PDF Dossier]
    end

    subgraph Statutory Integrity
        M -.-> N[SHA-256 Cryptographic Audit Trail with Chain Verification]
    end
```

---

## 3. How to Bring Your Own Data

Case Connect AI has **zero hardcoded schemas** and adapts dynamically to unseen formats from telecom operators, commercial banks, and regional police stations.

### Supported File Formats
1. **Call Detail Records (CDR)**: `.csv`, `.xlsx`, `.json`, `.jsonl` (A-Party, B-Party, Date, Time, Duration, Call Type, IMEI, Cell ID).
2. **Bank Transaction Statements**: `.csv`, `.xlsx`, `.json` (Remitter Account, Beneficiary Account, Amount, Date, Reference/Narration). Both multi-column exports and single-account debit/credit ledger sheets are parsed automatically.
3. **Identity Master / SDR / KYC**: `.csv`, `.xlsx` (Name, Phone, Account, Address, Vehicle Registration).
4. **Unstructured Police Documents**: `.txt`, `.pdf`, `.docx` (FIRs, Complaint Letters, Seizure Memos). Processed via deterministic regex and contextual NER.

### Dynamic Column Mapping Flow
1. Upload any file on the **Evidence Repository** tab.
2. System computes the cryptographic SHA-256 fingerprint, inspects headers, strips banner preambles, and computes a unique `header_signature`.
3. An interactive modal displays proposed canonical column alignments (`suggested_mapping`).
4. Officer confirms or modifies alignments.
5. Mapping templates are cached by `header_signature`; future uploads from the same bank branch or telecom circle are mapped automatically with 100% confidence.

### Known Ingestion Boundaries
- **Text PDFs Only**: Scanned image-only PDFs without OCR text streams are not automatically transcribed (OCR engine optional).
- **English & Transliterated Text**: Primary regex heuristics target English and Romanized Indian names.
- **Narrations**: Bank statement parsing currently targets NEFT, RTGS, IMPS, and UPI format strings.

---

## 4. Key Architectural Standards & Non-Negotiables

| Principle | Technical Implementation |
| :--- | :--- |
| **No Hardcoding** | Zero synthetic names, phone numbers, account constants, or dates exist in `backend/app/` or `frontend/src/`. Verified by `audit_hardcode.py`. |
| **No Mock Data** | Production API paths return clean empty arrays when no case evidence is staged; UI displays actionable empty states. |
| **Source of Truth** | SQLite is the authoritative transaction store; Neo4j is a rebuildable, disposable index (`rebuild_graph(case_id)`). |
| **AI Suggests, Officer Decides** | Entity merges and lead priorities are decision recommendations. Merges require explicit human signoff and support instant rollbacks (`Undo Merge`). |
| **Zero Prejudicial Terms** | Strictly bans words like `criminal`, `suspect`, `guilty`, or `mastermind`. Replaced with `lead for review`, `high-priority entity`, or `potential anomaly`. |
| **Section 63 BSA 2023** | Evidentiary hashes, machine fingerprints, extraction timestamps, and cryptographic audit chains ensure strict court admissibility. |

---

## 5. What We Did NOT Build (Explicit Non-Goals)

To preserve ethical rigor, investigative explainability, and legal admissibility:
1. **No Autonomous Black-Box Merging**: We do NOT silently fuse records with identical surnames or loose similarity without an investigator's recorded decision.
2. **No Facial Recognition / Biometric Scoring**: The platform does not perform probabilistic facial matches or demographic surveillance.
3. **No Automated Prosecution Deciders**: The platform produces analytical leads and anomaly indicators for review—not judicial determinations of guilt.
4. **No Cloud LLM Data Exfiltration**: Evidence is processed entirely within local air-gapped on-premise infrastructure; no sensitive police records are dispatched to external cloud APIs.

---

## 6. Project Verification & Test Suite

Run the full validation suite:

```bash
# 1. Run all 85+ backend integration and unit tests
pytest backend/tests

# 2. Run multi-dataset invariance proof matrix (27 permutations across 3 seeds)
pytest backend/tests/test_multi_dataset.py -s

# 3. Run strict security, offline, and anti-hardcoding auditor
python scripts/audit_hardcode.py

# 4. Run system scale & latency benchmarks
python scripts/perf_benchmark.py

# 5. Verify frontend production bundle
cd frontend && npm run build
```
