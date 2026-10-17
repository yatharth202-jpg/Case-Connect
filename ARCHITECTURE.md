# System Architecture Specification (ARCHITECTURE.md) — Case Connect AI

**Product:** Case Connect AI — Criminal Network Analysis System  
**Document Version:** 1.0.0  
**Status:** Approved Source of Truth  
**Target Environment:** Air-Gapped Police Workstations & On-Premise Cyber Cells  
**Foundational References:** PRD.md & DESIGN.md  

---

## 1. Executive Architecture Summary & Technology Stack

Case Connect AI implements a clean, modular, monolith-first architecture engineered for high forensic throughput, zero cloud exfiltration, and verifiable legal admissibility under Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023).

```
                      +---------------------------------------+
                      |       React 18 + Vite Frontend        |
                      |  (Cytoscape.js, Recharts, Lucide)     |
                      +-------------------+-------------------+
                                          | REST API (JWT Bearer)
                                          v
                      +---------------------------------------+
                      |         FastAPI Backend Engine        |
                      |    (Python 3.11+, Pydantic, Async)    |
                      +---------+-------------------+---------+
                                |                   |
                 +--------------+                   +--------------+
                 v                                                 v
  +-------------------------------+             +----------------------------------+
  |    Authoritative Storage      |             |     Disposable Graph Index       |
  |  SQLite 3 (WAL Mode + ORM)    |             |  Neo4j Community / NetworkX      |
  |  - 22 Relational Tables       |             |  - Cypher Traversal              |
  |  - Paise amounts, ISO dates   |             |  - Degree/Betweenness Centrality |
  |  - Cryptographic Hash Chain   |             |  - Rebuildable on demand         |
  +-------------------------------+             +----------------------------------+
```

### 1.1 Technology Stack Selection & Reasoning
| Component | Technology | Architectural Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | **FastAPI (Python 3.11+)** | High-performance asynchronous REST endpoints, automatic OpenAPI documentation, native Pydantic schema validation. |
| **Primary Database** | **SQLite 3 (WAL Mode)** | Zero-configuration, serverless, single-file portability, strictly ACID compliant, and easily verifiable in judicial proceedings. |
| **ORM / Data Access** | **SQLAlchemy 2.0** | Robust relational mapping, query parameterisation preventing SQL injection, thread-safe connection pooling. |
| **Graph Database** | **Neo4j 5.x / NetworkX** | Disposable index for multi-hop relationship discovery (`*1..4`), path finding, and centrality algorithms. Rebuildable from SQLite source. |
| **NLP & Entity Extraction** | **spaCy (`en_core_web_sm`)** | Deterministic local tokenization, regex extraction, and named entity recognition for FIR texts without cloud dependencies. |
| **Frontend Framework** | **React 18 + Vite** | Fast compilation, modular component architecture, and lightweight client-side state management. |
| **Graph Visualization** | **Cytoscape.js (fcose)** | Production-grade canvas rendering supporting thousands of nodes/edges with smooth pan/zoom and dynamic layout physics. |
| **Analytics Charts** | **Recharts** | Declarative charting for transaction distributions, 24-hour CDR heatmaps, and fund flow histograms. |
| **Court Dossier Engine** | **ReportLab 4.x** | Low-level deterministic PDF layout generator producing cryptographic watermarks and Section 63 BSA 2023 compliance pages. |
| **Authentication** | **Bcrypt & PyJWT** | Direct salted bcrypt hashing (12 rounds) and HS256 signed JSON Web Tokens. Passlib avoided due to security deprecations. |

---

## 2. System Architecture & Component Structure

### 2.1 Backend Architecture
The backend is structured as a layered modular monolith:
1. **API Routers (`backend/app/*/router.py`):** Handle HTTP serialization, parameter validation, role enforcement, and response envelope formatting.
2. **Business Services (`backend/app/services/`):** Pure domain logic isolated from HTTP concerns:
   - `ingestion/`: Universal tabular parser, magic byte header verification, and dynamic column alignment.
   - `analytics/`: Median Absolute Deviation (MAD) spike detection, pass-through BFS money trails, NetworkX centrality ranking.
   - `matching/`: Phonetic (Soundex) and string similarity (Jaro-Winkler) candidate deduplication.
   - `extraction/`: spaCy NLP and regex parsers for unstructured FIR complaints.
   - `reports/`: ReportLab statutory PDF builder.
3. **Data Access Layer (`backend/app/db/`):** SQLAlchemy ORM models, session lifecycle, and Neo4j driver connections.
4. **Audit Service (`backend/app/audit/`):** Genesis-anchored SHA-256 hash chaining on all data modification operations.

### 2.2 Frontend Architecture
The frontend is a single-page React application built with functional components and hooks:
- **`components/`:** Atomic UI components (`Button`, `Card`, `StatCard`, `Modal`, `Dropzone`).
- **`features/`:** Domain workspaces (`GraphExplorer`, `MoneyTrailCanvas`, `LeadAdvisor`, `EvidenceQueue`, `AuditTable`).
- **`context/`:** Authentication state, active case selection, and toast notifications.
- **`services/`:** Axios client instances with automatic Bearer token injection and global error interceptors.

---

## 3. End-to-End Data Flow

```
[Evidence File (CSV/XLSX/PDF)]
       |
       v
1. SHA-256 Computation & Magic Byte Validation
       |
       v
2. Universal Tabular Parser & Preamble Stripping
       |
       v
3. Header Signature Match / Fuzzy Column Mapper
       |
       v
4. Officer Column Confirmation (Mapping Saved)
       |
       v
5. Asynchronous Ingestion Job:
   ├── Normalize Currency -> Paise (Integer)
   ├── Normalize Phone    -> 10-Digit Mobile + Validation Flag
   ├── Normalize Date     -> ISO-8601 UTC String
   └── Reject Invalid Rows -> `rejected_rows` Table
       |
       v
6. SQLite Canonical Staging (`call_records`, `transactions`, `entities`, `entity_links`)
       |
       v
7. Graph Synchronization (`rebuild_graph(case_id)` -> Neo4j / NetworkX)
       |
       v
8. Forensic Analysis Pipeline:
   ├── NetworkX Suspect Hierarchy (Degree / Betweenness / PageRank)
   ├── MAD Call Spike Detection (IQR / Anomaly Thresholds)
   └── BFS Money Trail Layering (Pass-Through Accounts < 24h)
       |
       v
9. UI Presentation & Court Dossier Export (Section 63 BSA 2023 PDF)
```

---

## 4. Complete Folder & File Structure

```
c:\Users\Anshuman Singh\AI-Crime-Analyser-(v1.0)\
├── backend/
│   ├── app/
│   │   ├── audit/                  # Cryptographic hash chain service & models
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   ├── auth/                   # Authentication, JWT tokens, bcrypt security
│   │   │   ├── router.py
│   │   │   └── security.py
│   │   ├── cases/                  # Case dockets, membership & settings
│   │   │   └── router.py
│   │   ├── db/                     # Data access & database definitions
│   │   │   ├── neo4j.py            # Rebuildable graph driver & health checks
│   │   │   └── sql.py              # 22 SQLAlchemy tables & session maker
│   │   ├── evidence/               # Evidence file uploads & column mapping
│   │   │   └── router.py
│   │   ├── services/               # Core forensic domain engines
│   │   │   ├── analytics/          # MAD spike detection, money trails, leads
│   │   │   ├── extraction/         # spaCy NLP & FIR text parsing
│   │   │   ├── ingestion/          # Tabular parser, cleansers, normalizers
│   │   │   ├── matching/           # Soundex, Jaro-Winkler entity resolution
│   │   │   └── reports/            # ReportLab court dossier generator
│   │   ├── config.py               # Pydantic environment configuration
│   │   └── main.py                 # FastAPI application factory & middleware
│   ├── config/
│   │   └── defaults.yaml           # Mathematical thresholds & scoring weights
│   ├── tests/                      # 86+ pytest integration and unit tests
│   └── requirements.txt            # Pinned backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/             # Reusable UI cards, tables, inputs
│   │   ├── context/                # AuthContext, CaseContext
│   │   ├── pages/                  # Page routes (Dashboard, Graph, Leads, etc.)
│   │   ├── services/               # API clients
│   │   ├── App.jsx                 # Route definitions & protected routes
│   │   └── index.css               # Design tokens, Tailwind directives
│   ├── package.json
│   └── vite.config.js
├── docs/                           # System specifications, playbooks & sample cases
├── scripts/                        # Operational scripts (seed, preflight, audit)
├── PRD.md                          # Product Requirements Document
├── DESIGN.md                       # Design System & UX Specification
├── ARCHITECTURE.md                 # System Architecture (This file)
├── DATABASE.md                     # Complete Data Model & Schemas
├── API.md                          # API Contract & Specifications
├── AGENTS.md                       # Coding Rules & Agent Discipline
└── docker-compose.yml              # Multi-container orchestration
```

---

## 5. Database Interaction & Dual-Store Strategy

### 5.1 SQLite as Authoritative Transaction Store
* **Role:** Single source of truth for all uploaded evidence, raw rows, confirmed mappings, officer decisions, user permissions, and audit logs.
* **Integrity:** Foreign keys enabled (`PRAGMA foreign_keys = ON`), Write-Ahead Logging (`PRAGMA journal_mode = WAL`), and synchronous normal mode for high write performance with crash protection.

### 5.2 Neo4j as Rebuildable Disposable Projection
* **Role:** Read-optimized graph traversal engine.
* **Sync Principle:** If Neo4j becomes corrupt, unindexed, or out of sync, the application invokes `rebuild_graph(case_id)`. This wipes the case projection in Neo4j and completely reconstructs all nodes and relationships directly from the SQLite `entities` and `entity_links` tables.
* **Cypher Security:** All Cypher queries use parameterized inputs (`$case_id`, `$node_id`). Variable length range queries (`*1..N`) strictly validate `N in {1, 2, 3, 4}` before execution.

---

## 6. Authentication, Authorization & Security Boundaries

### 6.1 Authentication Mechanism
* **Credentials:** Username and password. Passwords verified via salted bcrypt (12 rounds).
* **Tokens:** Signed JSON Web Tokens (`HS256`) containing `sub` (User ID), `role`, and expiration timestamp.
* **Expiration:** Standard 8-hour access token lifecycle suitable for operational police shifts.

### 6.2 Authorization & BOLA / IDOR Defense
* **Role Enforcement:** Three strictly enforced server-side roles:
  - `admin`: System administration, user provisioning, global audit verification.
  - `investigator`: Full case lifecycle (evidence upload, mapping, lead approval, report generation).
  - `viewer`: Read-only access to visual projections, timelines, and dashboards.
* **Case Scoping (BOLA Defense):** Every route requiring a `{case_id}` invokes a shared dependency `get_case_access(case_id, current_user)`. If the user is neither an `admin` nor an assigned `case_member`, the request is immediately rejected with HTTP `403 Forbidden`.

### 6.3 Cryptographic Chain-of-Custody (BSA 2023 Section 63)
* Every database write triggers an entry in `audit_log`.
* `hash = SHA256(prev_hash + ts + user_id + action + case_id + object_id + details_json)`.
* Genesis block anchored at system initialization. Any tampering or retroactive record deletion invalidates the subsequent chain and is immediately flagged upon audit verification.

---

## 7. AI Architecture & Forensic Lead Scoring

Case Connect AI uses an explainable, deterministic AI architecture:
1. **No Probabilistic Hallucination:** Entity linkage and anomaly detection are governed by mathematical algorithms, not generative hallucinations.
2. **Anomaly Scoring Engines:**
   - **MAD Call Spike Detector:** Uses Median Absolute Deviation ($MAD = \text{median}(|X - \tilde{X}|)$) to identify communication bursts without assuming normal distribution.
   - **BFS Layering Engine:** Breadth-first graph traversal identifying accounts where $>80\%$ of funds received are dispersed to downstream beneficiaries within 24 hours.
   - **Centrality Hierarchy:** NetworkX calculation of Degree, Betweenness, and Eigenvector centrality to score suspect coordination hierarchy (Tier 1, Tier 2, Tier 3).
3. **Optional Copilot (Gemini 3.5 Flash):** An air-gapped, optional assistant that summarizes factual timelines and drafts charge-sheet narratives solely from confirmed SQLite entities.

---

## 8. Environment Configuration & Secrets Management

Configuration is managed via Pydantic `BaseSettings` reading exclusively from `.env`:
* `DATABASE_URL`: SQLite connection URI (`sqlite:///./app.db`).
* `JWT_SECRET`: 64-character random cryptographic secret for token signing.
* `ACCESS_TOKEN_EXPIRE_HOURS`: Token validity period (default: `8`).
* `NEO4J_URI`: Connection string for Neo4j instance (`bolt://localhost:7687`).
* `NEO4J_USER`: Neo4j database user (`neo4j`).
* `NEO4J_PASSWORD`: Neo4j database password.
* `GEMINI_API_KEY`: Optional API key for AI copilot narrative drafting.

*Rule: Zero hardcoded secrets or default passwords in source files.*

---

## 9. Error Handling & Resilience Conventions

* **Unified Error Envelope:** All backend errors return a structured payload:
  ```json
  {
    "error": {
      "code": "ERROR_CODE_ENUM",
      "message": "Clear explanation of failure without exposing internal stack traces."
    }
  }
  ```
* **Database Transactions:** All multi-row ingestion operations run inside explicit database transactions. If any error occurs, the entire batch rolls back, and the row is logged to `rejected_rows`.
* **Graceful Degradation:** If the Neo4j graph database is offline or unreachable, the system automatically falls back to in-memory NetworkX graph processing for network analysis.

---

## 10. Testing, Quality Assurance & Deployment Approach

### 10.1 Automated Test Suite
* **Unit & Integration Tests:** 86+ pytest tests covering authentication, case permissions, ingestion parsers, matching algorithms, money trails, and audit hash chains.
* **Multi-Dataset Invariance Testing:** Matrix tests running permutations across multiple synthetic seeds to verify parsers do not overfit to specific file layouts.
* **Security & Anti-Hardcoding Audit:** Automated scanning via `python scripts/audit_hardcode.py` to ensure zero synthetic names or hardcoded secrets enter version control.

### 10.2 Deployment Models
* **Docker Compose (Recommended):** Multi-container deployment running `backend`, `frontend`, and `neo4j` in an isolated bridge network with persistent local volumes.
* **Air-Gapped Standalone:** Single-executable or virtualenv deployment on isolated forensic laptops without internet connectivity.
* **Production Web Service:** Deployable on standard Linux servers or Render/AWS with preflight validation scripts (`scripts/preflight.py`).
