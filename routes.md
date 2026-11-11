# Routes Map (routes.md) — Case Connect AI

This document catalogs every client-side and server-side route in the Case Connect AI platform.

---

## 1. Frontend Client Routes (`frontend/src/App.jsx`)

| Route | Component / View | Purpose | Auth Required |
| :--- | :--- | :--- | :--- |
| `/` | `UploadScreen` / `MainCaseDossier` | Root landing page; defaults to dynamic evidence upload screen or active case dossier | Yes (Officer fallback) |
| `/login` | `Login` | Officer credential authentication portal | No (Public) |
| `/cases` | `Cases` | Comprehensive case docket management table | Yes (Officer) |
| `/cases/:id` | `CaseDetail` | Dedicated single-case investigation workstation | Yes (Case Member) |
| `/audit` | `AuditLog` | Cryptographic SHA-256 chain-of-custody audit log ledger | Yes (Admin/Investigator) |
| `/quick-analyser` | `QuickCrimeAnalyser` | Fast single-file CDR / Bank statement exploratory analyser | Yes (Officer) |

---

## 2. Backend API Inventory (`backend/app/main.py`)

All routes are mounted under `/api` and at the root prefix.

### 2.1 Authentication & System Health
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | SQLite and Neo4j connectivity and cluster status | No | Any |
| `POST` | `/auth/login` | Issue HS256 JWT access token from credentials | No | Any |
| `GET` | `/auth/me` | Return authenticated officer identity and permissions | Yes | Any valid token |

### 2.2 Case Docket Management (`backend/app/cases/router.py`)
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/cases` | List cases accessible to the authenticated officer | Yes | All roles |
| `POST` | `/cases` | Create a new criminal case docket | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}` | Retrieve case metadata and summary stats | Yes | Case Member |
| `PUT` | `/cases/{id}` | Update case title, status, or description | Yes | `admin`, `investigator` |
| `DELETE` | `/cases/{id}` | Archive or soft-delete a case | Yes | `admin` |
| `POST` | `/cases/{id}/members` | Assign an officer to a case | Yes | `admin` |
| `POST` | `/cases/{id}/reveal` | Unmask PII with statutory justification (creates audit log) | Yes | `admin`, `investigator` |

### 2.3 Evidence Ingestion & Mapping (`backend/app/services/ingestion/router.py`)
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/cases/{id}/evidence/upload` | Upload evidence file (CSV, XLSX, PDF, JPG, PNG, ZIP) | Yes | `admin`, `investigator` |
| `POST` | `/cases/{id}/evidence/detect` | Sniff encoding, detect file type, and extract candidate columns | Yes | `admin`, `investigator` |
| `POST` | `/cases/{id}/evidence/map` | Save confirmed column mapping and schema definition | Yes | `admin`, `investigator` |
| `POST` | `/cases/{id}/evidence/ingest` | Launch asynchronous chunked ingestion job | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/jobs/{job_id}` | Poll progress steps and status of an ingestion or OCR job | Yes | Case Member |
| `POST` | `/cases/{id}/jobs/{job_id}/cancel` | Cooperatively cancel an in-flight background job | Yes | `admin`, `investigator` |
| `POST` | `/cases/{id}/jobs/{job_id}/retry` | Reset and retry a failed background job | Yes | `admin`, `investigator` |

### 2.4 Document Extraction & OCR (`backend/app/services/extraction/router.py`)
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/cases/{id}/evidence/{eid}/extract` | Run spaCy NER + regex extraction on raw document | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/evidence/{eid}/entities` | List extracted entities with confidence and bbox spans | Yes | Case Member |
| `GET` | `/cases/{id}/evidence/{eid}/pages` | List page quality scores and OCR processing statuses | Yes | Case Member |
| `GET` | `/cases/{id}/evidence/{eid}/pages/{page}/ocr` | Fetch per-word bounding boxes and confidence scores | Yes | Case Member |
| `POST` | `/cases/{id}/evidence/{eid}/pages/{page}/corrections` | Submit officer OCR correction (creates locked claim) | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/completeness` | Case-wide data completeness score and missing field report | Yes | Case Member |

### 2.5 Unified Record Store & Merge Engine (`backend/app/services/merge/router.py`)
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/cases/{id}/evidence/{eid}/merge/preview` | Preview would-be changes without committing | Yes | Case Member |
| `POST` | `/cases/{id}/evidence/{eid}/merge/apply` | Apply claims, resolve golden fields, update graph | Yes | `admin`, `investigator` |
| `POST` | `/cases/{id}/evidence/{eid}/rollback` | Retract evidence claims and recompute golden fields | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/records` | Paginated search across active extraction records | Yes | Case Member |
| `GET` | `/cases/{id}/conflicts` | List open merge conflicts requiring officer decision | Yes | Case Member |
| `POST` | `/conflicts/{cid}/resolve` | Confirm selected claim value for a conflicting field | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/entities/{eid}/history` | Historical claims audit trail for an entity | Yes | Case Member |
| `GET` | `/cases/{id}/master-sheet` | Consolidated export (JSON, CSV, XLSX) with SHA-256 | Yes | Case Member |
| `POST` | `/cases/{id}/annotations` | Add officer forensic note or tag to an entity | Yes | `admin`, `investigator` |

### 2.6 Graph, Money Trail & Forensic Analytics
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/cases/{id}/graph` | Cytoscape graph nodes and edges projection | Yes | Case Member |
| `POST` | `/cases/{id}/graph/rebuild` | Trigger full Neo4j projection rebuild from SQLite | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/money-trail` | BFS money path layering and pass-through mule accounts | Yes | Case Member |
| `GET` | `/cases/{id}/analytics/comm-patterns` | Nocturnal curfew (IST 00:00-05:00) and frequency spikes | Yes | Case Member |
| `GET` | `/cases/{id}/analytics/lead-advisor` | Rule-based lead prioritization and risk scoring | Yes | Case Member |

### 2.7 Court Dossier & Audit Logs
| Method | Route | Purpose | Auth Required | Roles |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/cases/{id}/reports/generate` | Generate Section 63 BSA ReportLab court PDF | Yes | `admin`, `investigator` |
| `GET` | `/cases/{id}/reports/{rid}/download` | Download sealed, watermarked court PDF dossier | Yes | Case Member |
| `GET` | `/audit/logs` | Query tamper-evident SHA-256 genesis hash chain | Yes | `admin`, `investigator` |
| `GET` | `/audit/verify` | Verify mathematical integrity of the cryptographic chain | Yes | `admin` |

