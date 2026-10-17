# AI Coding Agent Rules & Governance (AGENTS.md) — Case Connect AI

**Product:** Case Connect AI — Criminal Network Analysis System  
**Document Version:** 1.0.0  
**Status:** Mandatory Source of Truth for all AI Coding Agents  
**Scope:** All changes to `backend/`, `frontend/`, `docs/`, `scripts/`, and root files  
**Foundational References:** PRD.md, DESIGN.md, ARCHITECTURE.md, DATABASE.md, API.md  

---

## 1. Prime Directive & Core Working Disciplines

All AI coding assistants (including Antigravity, Claude, Codex, or subagents) working in this repository MUST strictly follow these rules. The codebase is an enterprise-grade forensic investigation platform with strict legal and statutory requirements under Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023).

### 1.1 The Golden Rules
1. **INSPECT BEFORE EDITING:** Always read existing implementations, models, and tests before modifying or proposing code. Never guess existing signatures or invent redundant modules.
2. **ZERO HARDCODING:** Neither `backend/app/` nor `frontend/src/` may contain synthetic names, phone numbers, account constants, or fixed dates. Test fixtures belong exclusively in `backend/tests/` and `scripts/generate_data.py`. Every PR or task must pass `python scripts/audit_hardcode.py`.
3. **ZERO MOCK DATA IN PRODUCTION PATHS:** If no evidence has been staged for a case, production endpoints MUST return clean empty collections (`[]` or `{}`), and frontend views MUST render actionable empty states. Never hardcode mock items to fill UI widgets.
4. **SQLITE IS THE AUTHORITATIVE SOURCE OF TRUTH:** Neo4j is a rebuildable, disposable index. All merges, decisions, staged records, and audit events MUST be stored in SQLite first and synced to Neo4j via `rebuild_graph(case_id)`.
5. **AI SUGGESTS, HUMAN DECIDES:** Never automatically merge records or declare guilt. All identity merges require explicit officer confirmation and MUST support instant reversibility (`Undo Merge`).
6. **NO PREJUDICIAL TERMINOLOGY:** Never output words like `criminal`, `suspect`, `guilty`, or `mastermind` in UI copy, API messages, or reports. Use neutral, objective forensic terminology: `lead for review`, `high-priority entity`, or `potential anomaly`.

---

## 2. Code Quality & Naming Standards

### 2.1 Python (Backend)
* **Code Style:** Adhere strictly to PEP 8, Type Hints on all public functions, and descriptive function naming (`detect_rapid_pass_through`, `normalize_paise`).
* **Framework:** FastAPI with Pydantic v2 schemas. Avoid raw dictionary returns from API endpoints; use typed response models.
* **Exceptions:** Raise standard FastAPI `HTTPException` with structured JSON error details. Never swallow exceptions silently or return generic string errors.
* **Datetime Handling:** Store datetimes as ISO-8601 strings in UTC or timezone-aware objects (`datetime.now(timezone.utc)`). Never use deprecated bare `datetime.utcnow()`.

### 2.2 JavaScript / React (Frontend)
* **Components:** Functional React components with hooks. One component per file with PascalCase naming (`DropzoneUploader.jsx`).
* **Icons:** Use `lucide-react` exclusively. Do not import external CDN fonts, FontAwesome, or unvetted icon libraries.
* **Styling:** Adhere strictly to the tactical tokens in `DESIGN.md` and `index.css`. Never introduce arbitrary inline color hexes or harsh saturated rainbow gradients.
* **Zero Emojis:** Strictly prohibited in law-enforcement UI copy. Statuses are indicated via text badges (`HIGH`, `MEDIUM`, `LOW`) and SVG icons.

---

## 3. Project Structure & File Boundaries

```
backend/
├── app/
│   ├── audit/        # Cryptographic SHA-256 chain of custody
│   ├── auth/         # Bcrypt (12 rounds) & JWT token handling
│   ├── cases/        # Case dockets, permissions, & settings
│   ├── db/           # 22 SQLAlchemy models (sql.py) & Neo4j driver (neo4j.py)
│   ├── evidence/     # Ingestion, magic byte checks, & column mapping
│   ├── services/     # Pure forensic algorithms (analytics, matching, extraction, reports)
│   ├── config.py     # Pydantic BaseSettings
│   └── main.py       # FastAPI application setup & middleware
frontend/
├── src/
│   ├── components/   # Atomic reusable UI components
│   ├── pages/        # Route pages
│   ├── services/     # Axios API clients
│   └── index.css     # Design system tokens
```

*Rule: Place new backend business logic in `backend/app/services/<domain>/`, not directly inside route handlers.*

---

## 4. Component Reuse & Dependency Management

* **No Premature Dependencies:** Before introducing a new `npm` or `pip` package, evaluate whether the feature can be implemented using native standard libraries (`dataclasses`, `sqlite3`, `re`, `hashlib`) or existing installed dependencies (`networkx`, `spacy`, `reportlab`, `lucide-react`).
* **Pinned Versions:** Always record exact package versions in `requirements.txt` and `package.json`.
* **Prohibited Packages:**
  - `passlib`: Deprecated and insecure; use `bcrypt` directly.
  - Generative UI component libraries that inject unvetted external fonts or arbitrary global CSS styles.

---

## 5. Type Safety & Validation Rules

* **Pydantic Schemas:** All request and response bodies MUST have explicit Pydantic schemas under `backend/app/*/schemas.py` or within their respective router.
* **Input Validation:**
  - Upload file size caps: `<= 200 MB` for tabular files, `<= 20 MB` for document files.
  - Magic byte header checks: Verify raw file bytes before accepting file types (prevent disguised executable files).
  - Parametric Hop Limits: Graph hop query parameters MUST be constrained to `{1, 2, 3, 4}` to prevent exponential memory consumption.

---

## 6. Security, Secrets & Privacy Mandates

1. **Secrets Isolation:** All credentials (`JWT_SECRET`, `NEO4J_PASSWORD`, `GEMINI_API_KEY`) MUST be read strictly from environment variables via `backend/app/config.py`. Never hardcode fallback secret strings in code.
2. **BOLA / IDOR Defense:** Every case-scoped endpoint MUST verify that the requesting authenticated officer is assigned to that case or holds the `admin` role.
3. **Parametrised Queries Only:**
   - 100% SQLAlchemy ORM or parameterized queries (`:param`). Never concatenate user inputs into SQL strings.
   - 100% parameterized Cypher queries (`$param`).
4. **Privacy & Data Protection:**
   - Never open, print, or commit files located in `data/private/` or user-uploaded evidence.
   - Personal identifiable information (PII) must be masked in general server logs.
   - Passwords must be hashed with 12 salt rounds of bcrypt before entering the database.

---

## 7. Canonical Data & Units Conventions

* **Monetary Values:** All financial transactions MUST be converted and stored as integer **PAISE** (`amount_paise`). Never use floating-point numbers for currency arithmetic.
* **Dates & Timestamps:** All dates must be normalized to standard **ISO-8601** strings (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`).
* **Phone Numbers:** Phone numbers must be normalized to clean 10-digit mobile strings where valid, with an explicit boolean flag `valid_mobile=True`. Unrecognized or foreign numbers are retained as raw strings with `valid_mobile=False`.
* **Account Numbers:** Trimmed and normalized uppercase alphanumeric strings.

---

## 8. Testing & Self-Check Protocol

Before declaring any feature complete, the agent MUST execute the **Self-Check Protocol**:

### Step 1: Run Verification Tests
```bash
# Run full backend test suite
.venv\Scripts\pytest backend/tests -q

# Run strict anti-hardcoding and security audit
python scripts/audit_hardcode.py

# Verify frontend production build
cd frontend && npm run build && cd ..
```

### Step 2: Review Against Guidelines
* Verify that no mock data or hardcoded names were introduced.
* Ensure all database writes log to the cryptographic `audit_log` with valid previous hash linkage.
* Verify that responsive behavior functions without horizontal page overflow.

### Step 3: Evidence Before Assertions
* Always report real test execution results, passed test counts, and files modified. Never assume code works without running it.

---

## 9. Git & Change Discipline

* **Atomic Commits & Edits:** Focus code changes strictly on the requested task. Do not reformat or refactor unrelated files.
* **Preserve Integrity:** Preserve all existing docstrings, legal compliance notices, and architecture invariants.
* **No Broken States:** The codebase must remain runnable, test-passing, and clean after every completed task.
