# Product Requirements Document (PRD) — Case Connect AI

**Product Name:** Case Connect AI — Criminal Network Analysis System  
**Document Version:** 1.0.0  
**Status:** Approved Source of Truth  
**Target Platform:** Web (Desktop/Laptop forensic workstations & projector control rooms)  
**Legal Benchmark:** Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023) & DPDP Act 2023  
**Problem Statement Reference:** SIH26189 | Team UNITx  

---

## 1. Executive Summary & Value Proposition

### 1.1 Problem Statement
Indian Law Enforcement Agencies (State Police Cyber Cells, Crime Branches, and Central Special Cells) face significant operational bottlenecks when investigating complex criminal syndicates and financial fraud:
1. **Evidence Fragmentation:** Investigators receive heterogeneous evidence streams from varied telecom circles (CDRs), dozens of commercial banks (varying statement formats, NEFT/RTGS/UPI narrations), identity databases (SDR/KYC), and regional police First Information Reports (FIRs in free-text Hindi/English).
2. **Manual Reconciliation Bottlenecks:** Correlating phone numbers with bank account transfers across multiple suspects takes weeks of manual spreadsheet cross-referencing.
3. **Black-Box AI Skepticism:** Traditional predictive AI tools lack explainability, hallucinate connections, and fail judicial admissibility standards in court.
4. **Evidentiary Integrity Vulnerabilities:** Digital evidence without cryptographic chain-of-custody tracking fails Section 63 BSA 2023 scrutiny during trial proceedings.

### 1.2 Value Proposition
**Case Connect AI** is an enterprise-grade forensic investigation platform that aggregates unstructured and tabular evidence into a high-integrity, explainable investigation graph. It automates entity extraction, detects financial layering trails, calculates suspect centrality hierarchies, and generates court-admissible dossiers stamped with cryptographic SHA-256 audit chains—all running fully air-gapped without cloud exfiltration.

### 1.3 Target Users & Personas
* **Lead Investigator (Cyber Cell / Crime Branch):** Needs to ingest messy CDRs and bank exports, discover hidden coordinators/money mules, record decisions, and generate court-ready charge-sheet annexures.
* **Supervisory Admin (SP / DCP / Cyber Crime Head):** Needs case-level governance, role provisioning, and cryptographically verified audit trails to attest compliance under BSA Section 63.
* **Intelligence Analyst / Viewer:** Needs read-only access to visual graph projections, transaction timelines, and anomaly heatmaps for strategic briefing.

---

## 2. Core User Journeys & User Stories

### Journey 1: Evidence Ingestion & Universal Mapping
* **As an Investigator**, I want to upload unstandardized CDR spreadsheets or bank statement exports, so that the system automatically detects column layouts, cleans canonical data, and saves mapping templates for recurring bank branches.
* **Flow:**
  1. Officer opens `/cases/:id/evidence` and uploads files (`.csv`, `.xlsx`, `.json`, `.pdf`, `.txt`).
  2. Backend performs magic byte validation, computes SHA-256 hash, and strips header preambles.
  3. Dynamic column mapper presents suggested field alignments with confidence scores.
  4. Officer confirms or adjusts alignments; mapping template is saved for future uploads.
  5. Asynchronous ingestion job cleans, normalizes (paise, ISO dates, 10-digit mobile), and stages records into SQLite and Neo4j.

### Journey 2: Investigative Graph Exploration & Node Inspection
* **As an Investigator**, I want to search an entity (phone, person, account) and visualize multi-hop relationship connections, so that I can reveal hidden associates and device-sharing rings.
* **Flow:**
  1. Officer enters phone number or name in the OmniSearch bar at `/cases/:id/graph`.
  2. Graph renders nodes color-coded by entity type with dynamic Cytoscape layout.
  3. Officer selects hop radius (1 to 4) and filters by relationship type.
  4. Clicking any node/edge opens the Node Inspector showing verified provenance (source file, row number, detection method, and confidence).

### Journey 3: Money Trail & Layering Analysis
* **As a Financial Crime Analyst**, I want to trace fund flows from victim accounts across layered mule networks, so that I can identify pass-through accounts and cash-out points.
* **Flow:**
  1. Officer navigates to `/cases/:id/money-trail` and selects a focal bank account.
  2. Directed graph highlights fan-in consolidation, rapid pass-through (<24h turnaround), and high-velocity fund dissipation.
  3. Quantile filter chips (`p50`, `p75`, `p90`, `p99`) filter transaction sizes.
  4. Officer exports transaction sub-ledgers directly to CSV.

### Journey 4: AI Lead Advisor & Review Decisions
* **As an Investigator**, I want prioritized investigative leads backed by mathematical signal breakdowns, so that I can act on anomalies without bias.
* **Flow:**
  1. System scores entities using NetworkX centrality, call spike anomalies (MAD), money velocity, and document NER.
  2. Officer reviews leads sorted by Priority (`HIGH`, `MEDIUM`, `LOW`) at `/cases/:id/leads`.
  3. Officer views the "Why this lead?" breakdown showing exact formula weights and evidence links.
  4. Officer logs a formal decision (`Accept`, `Reject`, `Need More Data`) with investigator notes.

### Journey 5: Entity Deduplication & Master Profile Resolution
* **As an Investigator**, I want phonetic and fuzzy deduplication suggestions to merge duplicate identity records, with full human signoff and instant undo capability.
* **Flow:**
  1. System compares entities using Soundex, Jaro-Winkler, and shared phone/device links.
  2. Candidate match pairs appear in the review queue with similarity confidence (0.0 to 1.0).
  3. Officer approves or rejects the merge.
  4. If approved, a unified Master Profile is synthesized; if later disputed, officer clicks `Undo Merge` to cleanly restore original graph nodes.

### Journey 6: Cryptographic Audit & Court-Ready Dossier Export
* **As a Supervisory Officer**, I want to verify chain-of-custody integrity and export Section 63 BSA 2023 certified PDF reports for court submission.
* **Flow:**
  1. Officer visits `/audit` and triggers "Verify Chain Integrity" to validate every SHA-256 hash block from genesis.
  2. Officer navigates to `/cases/:id/reports`, selects dossier sections (Executive Summary, Graph Canvas, Suspect Rankings, Financial Trails, Hash Audit).
  3. ReportLab engine compiles the PDF with cryptographic watermarks, officer badge attestations, and source evidence hashes.

---

## 3. Features & Functional Requirements

| Module | Feature ID | Functional Requirement |
| :--- | :--- | :--- |
| **Auth & Governance** | FR-01 | Role-Based Access Control (`admin`, `investigator`, `viewer`) with bcrypt password hashing (12 rounds) and JWT sessions. |
| **Case Management** | FR-02 | Multi-tenant case isolation; all queries, graphs, and evidence strictly scoped by `case_id`. Cross-case access strictly prohibited unless explicit cross-docket alert is raised. |
| **Evidence Ingestion** | FR-03 | Universal tabular parser supporting CSV, XLSX, JSON, TXT, PDF. Header signature extraction and template persistence. |
| **Data Quality** | FR-04 | Rejection queue for malformed rows with exact failure reasons and original payloads preserved for audit. |
| **Canonical Staging** | FR-05 | Monotonic paise integer storage (`amount_paise`), ISO-8601 timestamps, 10-digit normalized phone numbers with validation flags. |
| **Graph Projection** | FR-06 | Dual-store architecture: SQLite authoritative source of truth, Neo4j rebuildable projection engine (`rebuild_graph(case_id)`). |
| **Network Analytics** | FR-07 | NetworkX centrality calculations (Degree, Betweenness, PageRank) producing Tier 1/2/3 suspect hierarchies. |
| **Financial Forensics** | FR-08 | BFS layering detection, rapid pass-through window identification, fan-in/fan-out ratio computation. |
| **Entity Resolution** | FR-09 | Soundex phonetic matching and Jaro-Winkler string similarity with strict human-in-the-loop approval and reversible undo logs. |
| **Document NLP** | FR-10 | spaCy entity recognizer combined with deterministic regex for FIR parsing (names, IPC/BNS sections, dates, locations). |
| **Audit Log** | FR-11 | Immutable blockchain-style SHA-256 ledger recording actor, timestamp, action, object, and previous row hash. |
| **Statutory Dossier** | FR-12 | Dynamic Section 63 BSA 2023 compliant PDF compilation with cryptographic verification certificates and forensic exhibits. |

---

## 4. Non-Functional Requirements

### 4.1 Security & Compliance
* **Zero Hardcoding Policy:** Zero synthetic names, numbers, or constants in production source files (enforced by `audit_hardcode.py`).
* **Zero Mock Data Policy:** All production API routes return genuine database state or clean empty collections.
* **BOLA / IDOR Defense:** Server-side case membership check on every endpoint invocation.
* **Statutory Compliance:** Full adherence to Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023) and Digital Personal Data Protection Act, 2023 (DPDP 2023).

### 4.2 Performance & Scale
* **Ingestion Throughput:** Ingestion of 50,000 CDR rows in < 15 seconds.
* **Graph Query Latency:** Sub-200ms response for 2-hop graph expansions up to 10,000 nodes.
* **PDF Compilation:** High-resolution multi-page forensic dossier generated in < 5 seconds.

### 4.3 Reliability & Air-Gapped Operation
* **Offline First:** System operates 100% locally with zero external internet dependencies; local fonts (`@fontsource/inter`) and SVGs (`lucide-react`).
* **Graph Recovery:** Complete graph projection index rebuildable from SQLite staging tables at any time.

---

## 5. Screen Inventory & Application Pages

1. **`/login` — Authentication Portal:** Credential entry, department SSO selector, security notice.
2. **`/select-role` — Role Wizard:** Profile confirmation and active workstation permission view.
3. **`/dashboard` — Command Overview:** Active cases KPI cards, activity feed, system status banner.
4. **`/cases` — Case Docket Management:** Case directory, search/filter, new investigation creator modal.
5. **`/cases/:id/evidence` — Evidence Ingestion Hub:** Drag-and-drop uploader, dynamic column mapper, job progress monitor.
6. **`/cases/:id/graph` — Investigation Graph Canvas:** Interactive Cytoscape network explorer, hop radius filters, node inspector.
7. **`/cases/:id/money-trail` — Financial Flow Explorer:** Directed account transaction trails, quantile volume filters, ledger export.
8. **`/cases/:id/leads` — AI Lead Advisor:** Prioritized lead cards, mathematical signal breakdowns, formal decision recorder.
9. **`/cases/:id/profiles/:profileId` — Cross-FIR Master Profile:** Unified identity dossier, linked phones/accounts, chronological timeline.
10. **`/audit` — Cryptographic Audit Trail:** Tamper-evident hash chain viewer, genesis recalculation tool.
11. **`/cases/:id/reports` — Court Dossier Generator:** ReportLab PDF builder with Section 63 BSA 2023 compliance selector.
12. **`/404` — Tactical Error Screen:** Styled custom page with breadcrumbs returning to active docket.

---

## 6. Roles & Permissions Matrix

| Permission / Capability | Supervisory Admin (`admin`) | Lead Investigator (`investigator`) | Intelligence Analyst (`viewer`) |
| :--- | :---: | :---: | :---: |
| Authenticate & Access Workspace | Yes | Yes | Yes |
| Create Cases & Assign Members | Yes | Yes | No |
| Manage System Users & Roles | Yes | No | No |
| Upload Evidence & Map Columns | Yes | Yes | No |
| Approve / Undo Entity Merges | Yes | Yes | No |
| Submit Formal Lead Decisions | Yes | Yes | No |
| View Graph, Trails, & Heatmaps | Yes | Yes | Yes |
| Export Court-Ready PDF Dossier | Yes | Yes | Yes |
| Verify Hash Chain Integrity | Yes | Yes | Yes |

---

## 7. Data Requirements

* **Call Detail Records (CDR):** A-Party (caller), B-Party (receiver), Date, Time, Duration (seconds), Call Type, IMEI, IMSI, Cell ID.
* **Bank Statements & Ledger Exports:** Transaction ID, Remitter Account, Beneficiary Account, Remitter/Beneficiary Names, Amount (canonical paise), Date, Reference/Narration, Direction.
* **Identity Master / SDR / KYC:** Subscriber Name, Mobile Number, Bank Account, National ID / PAN, Address, Vehicle Registration.
* **Police FIRs & Seizure Memos:** FIR Number, Police Station, Date/Time, Acts & Sections (e.g. IPC 420 / BNS 318), Named Suspects, Complainants, Narratives.
* **IP Event Logs:** Identifier (phone/account/user), IP Address, Timestamp.

---

## 8. Integrations & Technology Dependencies

* **Backend Engine:** FastAPI (Python 3.11+) with asynchronous execution and Pydantic validation.
* **Primary Database:** SQLite 3 with SQLAlchemy ORM (WAL mode enabled).
* **Graph Projection Engine:** Neo4j Community Server 5.x / NetworkX local graph library fallback.
* **Natural Language Processing:** spaCy (`en_core_web_sm`) + deterministic regex patterns + optional Google Gemini 3.5 Flash Copilot.
* **Frontend Web Application:** React 18 with Vite, Tailwind CSS, Lucide icons, and @fontsource/inter.
* **Visualization Libraries:** Cytoscape.js with fcose layout, Recharts for timeline and transaction distributions.
* **Document Compilation:** ReportLab PDF toolkit for Section 63 BSA 2023 certified court reports.

---

## 9. Loading, Empty & Error States

* **Loading States:** Pulse skeleton blocks for KPI cards, tables, and inspector sidebars; spinner with textual status for asynchronous ingestion jobs (`"Parsing rows...", "Staging entities...", "Syncing graph..."`).
* **Empty States:** Clean, actionable instructions on every view (e.g., `"No evidence files staged. Upload CDR CSV or Bank Excel to begin"` with primary upload button).
* **Error States:** Actionable inline messages with error codes (e.g., `"MAPPING_ERROR: Mandatory date column not aligned"`), avoiding raw stack trace leaks.

---

## 10. Scope Boundaries & Success Criteria

### 10.1 In-Scope (MVP & Core Platform)
* Universal tabular parsing with header caching and fuzzy mapping suggestions.
* Canonical data staging into 22 SQLite relational tables.
* Dual-engine graph projection with NetworkX centrality and Cytoscape.js rendering.
* BFS money layering detection and pass-through account flagging.
* Reversible entity merging with human signoff.
* Blockchain-style cryptographic SHA-256 audit ledger.
* Section 63 BSA 2023 certified PDF dossier generation.

### 10.2 Out-of-Scope (Explicit Non-Goals)
* **No Autonomous Black-Box Merging:** Merging records requires explicit recorded human approval.
* **No Facial Recognition / Biometrics:** Strictly focused on telecom, financial, and relational records.
* **No Automated Judicial Determinations:** Produces prioritized leads for human review, never automated verdicts of guilt.
* **No Cloud Exfiltration:** All investigative files remain strictly on local premises.

### 10.3 Success Criteria
* 100% test pass rate across the full integration and multi-dataset test suite (86+ tests).
* Zero hardcoded sample names, dates, or credentials in production code paths.
* Zero mock data in production APIs.
* Full judicial compliance under Section 63 BSA 2023 attested by valid SHA-256 chain verification.
