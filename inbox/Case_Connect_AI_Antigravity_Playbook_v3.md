# Case Connect AI — Antigravity Playbook v3 (Data-Driven · Stitch UI · Self-Checking)

**Kya badla (v2 → v3):**

- **Tumhara kaam kam:** tum sirf ek `inbox/` folder bharte ho (Stitch ZIP + PDFs + yeh file). Unzip, organise, UI inventory, design tokens, start script, sab agent karta hai. Har phase ke upar ek alag **"TUMHARA KAAM"** box hai: kab kya dena hai, kab ruk ke approve karna hai, kya bahar ka kaam hai.
- **Stitch UI:** ZIP ek hi baar, Phase 0 se pehle. Agent har screen ko waise hi React me banata hai (layout, colours, fonts, spacing). Image me dikhne wala placeholder data (naam, number, amount) wo kabhi copy nahi karta.
- **Koi bhi file / koi bhi doc:** nayi types: identity table (persons list, vehicle registry, SDR, KYC), IP log, JSON, DOCX, koi bhi narrative document (FIR zaroori nahi). Naya `probe_file.py` tool kisi bhi file ko app ke engine se chalake dikhata hai ki wo kya samjha.
- **Self-check x3:** har phase ke end me agent 3 pass karta hai (run, review, naye random data pe test) aur ek table dikhata hai. Pehle "done" nahi bol sakta.
- **Overfitting ke khilaf:** 9 scenarios (ring ke alawa chain, hub-spoke, two rings, tiny, random mix...), har run me random seeds, `audit_hardcode.py` Phase 1 se hi, aur rule "test fail ho to code badlo, test nahi".
- **v2 ki galtiyan fix:** API contract me missing endpoints (saved views, reports, recompute, users), IP/vehicle ke graph relations, money-trail me parallel-transaction path explosion, same-name Person ka honest note.

---

## A. Tumhara pura kaam ek nazar me

| Kab | Tum kya doge / karoge | Kitna time |
|---|---|---|
| **Phase 0 se pehle (ek baar)** | Docker Desktop, Node 20+, Python 3.11+, Git install. Project folder banao, uske andar `inbox/` me: Stitch ki saari ZIP files, PDFs (Master Guide, Architecture, Skills, Sample Demo Data), aur yeh playbook file. | 30-60 min |
| Phase 0 | Agent ka PLAN approve (ek baar). End me `UI_INVENTORY.md` dekho. | 15 min |
| Phase 1 | Kuch nahi bhejna. Generator ki messy Excel kholke dekho. | 5 min |
| Phase 2 | Admin password terminal me. Login test. | 5 min |
| Phase 3 | Optional: apni files `data/user_samples/` me. Ek file UI se upload karke mapping confirm. | 15 min |
| Phase 4 | Kuch nahi. (Cypher Fundamentals seekhna accha rahega.) | 0 |
| Phase 5 | Kuch nahi. Money trail try karo. | 5 min |
| Phase 6 | Optional: apni text FIR (txt/pdf/docx). Review screen try karo. | 10 min |
| Phase 7 | Kuch nahi. Approve/Undo try karo. | 5 min |
| Phase 8 | Kuch nahi. Settings me weight badal ke score badalta dekho. | 5 min |
| Phase 9 | Kuch nahi. PDF report dekho. | 5 min |
| Phase 10 | Ek bilkul nayi file ready rakho. Empty app se demo rehearse karo. | 1-2 ghante |

**Jo agent kar hi nahi sakta (bahar ka kaam):** software install, Antigravity login/quota, GitHub login aur push, demo video record, hackathon rulebook padhna, apna PPT final karna (agent Phase 10 me PPT ka text draft dega, par slides tum banate ho).

---

## B. Antigravity me kaise chalana hai

1. **Ek phase = ek naya conversation.** Prompt block (```text) pura copy karo. Phase 0 ke baad `inbox/` ki playbook copy `docs/PLAYBOOK.md` ban jaati hai.
2. **Chhota tareeqa (quota bachta hai):** Phase 1-10 ke liye block paste karne ki jagah bas ye likho:
   `Read docs/RULES.md, then execute ONLY "PHASE N" of docs/PLAYBOOK.md (the prompt block under that heading). Give a plan first and wait for my approval, then implement. Finish with the SELF-CHECK report.`
   Phase 0 ke liye: `Read inbox/<is file ka naam>.md and execute ONLY "PHASE 0".`
3. Pehle **plan** aata hai. Padho, approve karo. Terminal ko auto-run pe mat chhodo (review mode).
4. Phase ke end me agent ki **SELF-CHECK table** zaroor aani chahiye. Na aaye to bolo: `Run the SELF-CHECK PROTOCOL from docs/RULES.md and show the table.`
5. "DONE WHEN" **tum khud** chalake verify karo, phir `git commit` aur tag.
6. Agent rules tode to bolo: `Re-read docs/RULES.md, list which rules you broke, and fix.`
7. Neo4j Browser (http://localhost:7474) me agent ki Cypher khud chalake dekho.

---

## C. Hardcode-free design (poore project ke 12 usool)

1. **App me koi sample naam/number/date/amount nahi.** Sirf `tests/` aur `scripts/generate_data.py` me ho sakta hai. `scripts/audit_hardcode.py` Phase 1 se har phase me chalta hai.
2. **Koi mock JSON production path me nahi.** Data nahi hai to UI "Upload data to begin" dikhata hai.
3. **Source of truth = SQLite** (staging tables: calls, transactions, entities, links, decisions). **Neo4j ek rebuildable graph index hai.** `rebuild_graph(case_id)` kabhi bhi sab kuch SQL se dubara bana sakta hai. Isse bug-fix ke baad re-run aasan hai aur approvals/undo safe rehte hain.
4. **Thresholds hardcode nahi.** `config/defaults.yaml` me generic defaults, **per-case Settings screen** me editable, aur har flag ki explanation me asli threshold aur asli numbers likhe hon.
5. **Percentile/relative scoring.** Score data ke apne distribution se nikalta hai (kis account ka throughput case me kitna upar hai), kisi fixed rupees se nahi.
6. **Missing data graceful.** Sirf CDR upload hui to money signals "not available" dikhein aur priority sirf available signals pe rescale ho, confidence kam ho. Crash ya fake zero nahi.
7. **Owner unknown ho sakta hai.** CDR me sirf numbers hote hain. Jis phone/account ka owner pata nahi, wo khud graph me ek entity hai. Owner baad me SDR/KYC/FIR/officer se aata hai.
8. **Real files messy hoti hain.** Alag headers, title rows, Excel, `dd/mm/yyyy`, `+91`, Dr/Cr columns, single-account statements. Isliye column-mapping engine zaroori hai.
9. **Identity tables generic hain.** Persons list, vehicle registry, SDR, KYC, IP log: sab "naam <-> identifiers" tables hain. Ek hi engine (`identity_table`) sabko sambhalta hai; kisi ek file ke columns pe nirbhar nahi.
10. **Documents generic hain.** FIR ho ya complaint ya bank notice: text se entities nikalte hain. FIR number / police station optional hain.
11. **UI image = sirf layout spec.** Stitch ki image me jo naam/number/chart dikhta hai wo placeholder hai. Layout, colours, fonts copy hote hain, content kabhi nahi.
12. **Overfitting ki jaanch:** har phase me agent un seeds pe test karta hai jo usne development me kabhi use nahi kiye (random, print kiye hue), alag scenarios/formats ke saath. Aur tumhari `data/user_samples/` ki files pe bhi.

**Guide ki jo galtiyan fix ki hain (pehle jaisi):**
- Hop = **entity-level hops** (person/phone/account jo owner se collapse ho), raw graph ke nahi.
- "Only bridge" nahi, "**highest-betweenness bridge**".
- Neo4j me `*1..$n` parameter invalid hai: `n` validate karke string me format karo. Path pe condition `ALL(r IN relationships(path) WHERE ...)`.
- 10-digit phone aur account number regex me takrate hain: account sirf "a/c"-type context ke saath.
- Name-only match kabhi merge suggest nahi; relatives (same surname + shared phone) = "shared device" flag.
- Section 65B ki jagah **Section 63, BSA 2023**; admissibility court decide karti hai.
- Hindi doc ke "auto-link", "Mastermind", "Risk 96%", "Tornado Cash mixer" mat use karo.

---

## PHASE 0 — Inbox, UI pack, bootstrap, rules, API contract

> ### TUMHARA KAAM — PHASE 0
> **Pehle (paste karne se pehle):**
> - Install: Docker Desktop (chalu rakho), Node 20+, Python 3.11+, Git. Agent install nahi kar sakta; baad me `python scripts/preflight.py` batayega kya missing hai.
> - Project folder me `inbox/` banao aur usme daalo:
>   1. Stitch se nikali **saari ZIP files** (jitni bhi, unzip mat karo).
>   2. PDFs: `Case_Connect_AI_Master_Guide`, `SIH26189_Complete_Project_Architecture`, `SIH26189_Skills_Required`, `SIH26189_Sample_Demo_Data` (ye sirf format dekhne ke liye, data copy nahi hoga).
>   3. Yeh playbook file.
> - Hindi wali "Ultimate All-in-One" PDF **mat daalo** (usme "100% admissible", "auto-link", "Mastermind" jaise claims hain jo yahan banned hain). Daal bhi do to agent use SUPERSEDED mark karega.
> - Optional: `data/user_samples/` me koi bhi file jo agent ko dekhne deni hai (sirf synthetic / non-sensitive). Sensitive ho to `data/private/` me rakho, agent use kabhi nahi kholega.
>
> **Beech me:** agent PLAN dega (files + assumptions). Ek baar approve karo. Uske baad wo Task 0 se Task 6 tak khud chalta hai.
>
> **Baad me (verify):**
> - `docs/ui/UI_INVENTORY.md` kholo: har image sahi screen se map hui? "Missing screens" list me jo screen tumhe chahiye, Stitch se bana ke `inbox/` me daalo aur bolo `Re-run the UI inventory`. Ya agent ka proposed layout accept karo.
> - `python scripts/start.py` chalao, `/health` me neo4j aur sqlite dono ok.
> - Agent ki SELF-CHECK table dekho.
>
> **Bahar ka kaam:** GitHub repo banao aur `git remote add origin ...` (agent ke paas tumhara login nahi).

```text
ROLE
You are a senior full-stack engineer pair-programming with a student who is a beginner in backend development. Prefer boring, well-known solutions. Add short comments for non-obvious decisions. Never leave stubs that silently return fake data.

PROJECT
"Case Connect AI": an investigation-support web app for police investigators (Smart India Hackathon PS SIH26189, team UNITx). An officer creates a case and UPLOADS their own files (CDR, bank data, subscriber/KYC data, FIR text/PDFs). The system detects formats, maps columns, cleans the data, builds a knowledge graph, runs analytics and shows graphs, charts, money trails and explainable "leads for review". The app contains NO built-in case data: everything on screen is computed from what the user uploaded. The system assists; the officer decides.

TASK 0 — INBOX + REFERENCE DOCS + UI PACK (do this first)
 a) Look in ./inbox/ (create it if missing). Never modify its originals; work on copies.
 b) PDFs: copy to docs/reference/ and convert each to docs/reference/<name>.md with pdfplumber (keep page markers). Authority order: (1) my instructions in this chat and docs/RULES.md, (2) Master Guide, (3) Architecture, (4) Skills. SIH26189_Sample_Demo_Data is ONLY a format reference for test generators: its names, numbers and dates must never be copied into app code, UI text or seeded data. Any PDF whose content contradicts RULES.md (for example documents using words like 'mastermind', '100% admissible', 'auto-link') is marked SUPERSEDED in docs/reference/INDEX.md and is not used for decisions. Where my instructions conflict with the PDFs, MY INSTRUCTIONS WIN.
 c) UI PACK (exported from Stitch): unzip every *.zip in ./inbox/ into docs/ui/pack/<zip-name>/ (keep the structure). Inventory every image (png/jpg/webp/svg) and every html/css/js/json file. View each image. Then write:
   - docs/ui/UI_INVENTORY.md: a table (file, screen name you infer, route, confidence, notes); then the list of screens the product needs (Login, Dashboard, Cases list, Case workspace, Upload + mapping, Entity Review, Matches queue, Master Profile, Investigation with Graph / Money Trail / Timeline / Network Analysis, Lead Advisor panel, Alerts, Reports, Settings, Admin audit) that have NO image, with a one-paragraph proposal for each in the same visual language.
   - docs/ui/DESIGN_TOKENS.md: if html/css exist, extract colours, fonts, spacing, radius, shadows EXACTLY from the code (not by eye); otherwise sample from the images. Note the icon style. Fonts are bundled locally via npm @fontsource packages (no Google Fonts CDN; the app must work offline). Icons come from lucide-react (replace Material-Symbols-style font icons).
   - docs/ui/SCREEN_MAP.md: per screen: route, components, which endpoints from docs/API_CONTRACT.md and which data fields it needs, interactions, and its empty / loading / error states.
 d) UI IMAGES CONTAIN PLACEHOLDER DATA (names, numbers, amounts, dates, charts). They are a LAYOUT SPEC only. Copy structure, spacing, colours, typography and component shapes. NEVER copy displayed content into code. Static charts in images become real chart components fed by API data.
 e) If inbox/ is empty or has no zip: say so, continue every other task, and use a clean default layout (Master Guide Figure 3: sidebar + top search/filters + central canvas + right panel).
 f) PLAYBOOK: copy any playbook .md found in ./inbox/ (the file this prompt comes from) to docs/PLAYBOOK.md unchanged, so later phases can be started with a one-line instruction. Treat it as read-only.

TASK 1 — Monorepo skeleton
case-connect-ai/
  backend/ (FastAPI, Python 3.11+): app/main.py, config.py, db/{neo4j.py,sql.py}, routers/, services/, schemas/, jobs/, tests/, config/{defaults.yaml, column_synonyms.yaml, narration_patterns.yaml, patterns.yaml}
  frontend/ (React + Vite, JAVASCRIPT not TypeScript, Tailwind, react-router-dom, cytoscape, recharts, lucide-react)
  scripts/ (generate_data.py = DEV TOOL ONLY, init_db.py, reset_db.py, preflight.py, start.py, seed_users.py, probe_file.py, audit_hardcode.py)
  data/synthetic/ (generator output, git-ignored except small samples)
  data/private/ (git-ignored; where the user keeps real/external files; YOU MUST NEVER OPEN OR READ FILES HERE)
  data/user_samples/ (git-ignored; files I allow you to analyse; you MAY open them to harden ingestion, never copy their contents into code, tests or docs)
  inbox/ (git-ignored; Stitch ZIPs, PDFs and this playbook; see TASK 0)
  docs/{reference/, ui/, RULES.md, API_CONTRACT.md}
  docker-compose.yml (neo4j:5-community, ports 7474+7687, named volume, credentials from .env)
  .env.example (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, JWT_SECRET, DATABASE_URL=sqlite:///./app.db, UPLOAD_DIR)
  .gitignore (.env, app.db, uploads/, data/private/, data/user_samples/, inbox/, node_modules, __pycache__, .venv)

TASK 2 — Backend dependencies (pin after install)
fastapi, uvicorn[standard], neo4j (official v5 driver), pandas, openpyxl (xlsx), charset-normalizer, python-dateutil, pydantic, pydantic-settings, python-multipart, sqlalchemy, bcrypt (use bcrypt directly, NOT passlib), pyjwt, rapidfuzz, networkx, spacy, pdfplumber, reportlab, matplotlib, faker, pytest, httpx, pyyaml, python-docx (read .docx). No APOC, no Neo4j GDS: graph maths in NetworkX.

TASK 3 — scripts/init_db.py
Create SQLite tables (empty models now): users, cases, case_members, case_settings(case_id, json), evidence_files, column_mappings, mapping_templates, jobs, call_records, transactions, ip_events, rejected_rows, entities, entity_links, extracted_entities, match_suggestions, profile_members, lead_decisions, alerts, reports, audit_log, saved_views.
Create Neo4j uniqueness constraints on property `key` for labels Person, Phone, BankAccount, Organization, Vehicle, FIR, MasterProfile, Email, Device, VPA, IP; plus an index on case_id for each.

TASK 4 — GET /health -> {"neo4j","sqlite"}; frontend landing shows backend status (Vite proxy /api -> localhost:8000, CORS for localhost:5173).

TASK 4b — ONE-COMMAND DEV EXPERIENCE (so I do not run six commands by hand)
 scripts/preflight.py: checks that Docker is running, Node >= 20, Python >= 3.11, Git, ports 5173/8000/7474/7687 are free, and there is enough disk; prints a plain-language fix for each missing item; never installs anything silently.
 scripts/start.py: preflight -> docker compose up -d -> wait for Neo4j (retry with timeout) -> create the Python venv and install requirements if missing -> init_db -> npm install if missing -> start backend and frontend -> print the URLs. From Phase 2 on it also calls scripts/seed_users.py when no admin exists (password asked in the terminal). Pure Python, works on Windows, macOS and Linux.

TASK 5 — docs/RULES.md (copy verbatim; obey in every later task)
 1. NO HARDCODING. app/ and frontend/src/ must contain NO sample names, phone/account numbers, dates, amounts or case-specific constants. Test data lives only in tests/ and scripts/generate_data.py.
 2. NO MOCK DATA in production code paths. If nothing is uploaded, screens show an empty state with an "Upload data" call-to-action.
 3. Source of truth is SQLite. Neo4j is a rebuildable index: implement rebuild_graph(case_id). Approvals/undo/decisions are stored in SQLite and synced to Neo4j.
 4. All thresholds/weights come from backend/config/defaults.yaml, overridable per case via case_settings. Every flag/score explanation states the actual threshold and values used.
 5. AI suggests, the human decides. Never merge identities automatically; merges are suggestions with confidence and need officer approval; every merge is undoable. The ONLY exception is exact normalised-name equality inside one case (Phase 4): it is recorded as method='name_equality' and shown in the UI, never hidden.
 6. Never output the words "criminal", "suspect", "guilty", "mastermind" in UI text, API responses or reports. Use "lead for review", "high-priority entity", "potential anomaly".
 7. Provenance on every graph node/relationship and every staged row: case_id, source_file (evidence id), source_ref (row number or page), method ('structured'|'regex'|'ner'|'officer'|'derived'), confidence 0-1, approved_by when applicable.
 8. Cypher is always parametrised. ONLY exception: variable-length range (*1..N), where N is validated as int in {1,2,3,4} then formatted into the string. Conditions on every relationship of a variable-length path use ALL(r IN relationships(path) WHERE ...). Always LIMIT; use neo4j.Query(..., timeout=...) for path queries.
 9. Everything is case-scoped (case_id). Nothing crosses cases except the explicit cross-case alert.
10. Money is stored as integer PAISE (amount_paise). Dates as ISO-8601 strings. Phones normalised to 10-digit mobile where valid; other numbers kept as-is with valid_mobile=false. Account identifiers are normalised strings (uppercase, trimmed) and may be alphanumeric.
11. Passwords bcrypt, tokens JWT, secrets only from .env.
12. PRIVACY: never open, print, or send anything under data/private/ or any user-uploaded evidence unless I explicitly ask. Files in data/user_samples/ you MAY open (I put them there for you) to make sure ingestion handles them, but never copy their contents into code, tests or docs. Tests use generator output only.
13. SELF-CHECK PROTOCOL (mandatory at the end of every phase and every big task; do NOT say 'done' before it):
     PASS 1 - RUN: all tests of this phase and earlier phases, scripts/audit_hardcode.py (once it exists), and the frontend build/lint. Paste the real output.
     PASS 2 - REVIEW: re-read every file you changed against (a) this RULES.md and (b) the phase's DONE WHEN list. Write the violations or doubts you found (even 'none') and fix them.
     PASS 3 - HELD-OUT DATA: pick 2 random seeds you have never used (print them), generate fresh data in scenarios/formats different from the ones you developed with, run the phase's end-to-end check and compare with ground_truth.json. Also run the feature on every file in data/user_samples/ if any exist.
     Finish with a table: check | result | what you fixed. If anything failed, fix it and repeat from PASS 1. Anything you could not verify is written as NOT VERIFIED with the reason.
14. NO OVERFITTING: never write logic that only works for the generator's names, headers, column order, row counts, dates or amounts. Every parser, matcher and scorer works from detected structure and config. When a test fails, fix the code; never weaken or special-case the test.
15. UI FIDELITY: build screens from docs/ui/SCREEN_MAP.md and DESIGN_TOKENS.md. Layout, colours and typography must match the Stitch pack; displayed example content in the images is never copied.
16. HONEST REPORTING: list what is incomplete, approximate or fragile (low recall, bank-specific narrations, slow paths). Never hide a failing test or a skipped item.
17. SMALL STEPS: if a task is bigger than expected, split it, finish and verify the first part, then continue. Never leave half-wired features that silently return fake data.

TASK 6 — docs/API_CONTRACT.md (write BEFORE endpoint code). All case-scoped under /cases/{id}/ :
 AUTH: POST /auth/login, GET /auth/me
 CASES: POST/GET /cases, GET /cases/{id}, GET/PUT /cases/{id}/settings
 EVIDENCE: POST /cases/{id}/evidence (upload; returns detected_type + suggested_mapping + preview rows), GET /cases/{id}/evidence, GET /evidence/{id} (details + mapping + preview), POST /evidence/{id}/mapping (confirm/override), POST /evidence/{id}/ingest, POST /evidence/{id}/verify, GET /jobs/{id}
 DATA QUALITY: GET /evidence/{id}/rejected-rows
 GRAPH: GET /cases/{id}/graph/search?q=&hops=&view=entity|detail&types=&limit=, GET /cases/{id}/graph/path?from=&to=, POST /cases/{id}/links (officer link, e.g. assign phone->person), DELETE /cases/{id}/links/{link_id} (undo)
 MONEY: GET /cases/{id}/money-trail?account=&min_amount=&hops=&direction=in|out|both
 ENTITIES/MATCHES: GET /cases/{id}/entities, GET /cases/{id}/extracted?status=&type=&min_conf=&evidence_id=, PATCH /extracted/{id} (edit/approve/reject), POST /cases/{id}/extracted (manual add), POST /cases/{id}/extracted/approve-all?threshold=, GET /evidence/{id}/text (page texts + entity spans), GET /cases/{id}/matches?level=&status=, POST /matches/{id}/approve|reject|undo, GET /cases/{id}/profiles, GET /cases/{id}/profiles/{profile_id}
 ANALYTICS: GET /cases/{id}/analytics/{overview|calls-per-day|top-entities|txn-volume|communities|degree-distribution|call-heatmap}
 LEADS: GET /cases/{id}/leads, GET /cases/{id}/entities/{entity_id}/why, POST /cases/{id}/leads/{lead_id}/decision
 OTHER: GET /cases/{id}/alerts, GET /cases/{id}/timeline, GET /cases/{id}/provenance?edge_id=|node_id=, POST /cases/{id}/analytics/recompute (job), GET/POST/DELETE /cases/{id}/saved-views, POST /cases/{id}/report, GET /cases/{id}/reports, GET /reports/{id}/download, GET /audit/verify, GET /audit?case_id=, GET/POST/PATCH /users (admin), GET /mapping-templates
Standard graph response: {"nodes":[{"id","type","label","props"}],"edges":[{"id","source","target","type","props"}],"truncated":false,"meta":{"hops":3,"count_nodes":0,"count_edges":0}}
Job response: {"id","status":"queued|running|done|failed","progress":0-100,"steps":[{"name","status"}],"error":null}
Error shape: {"error":{"code","message"}}

First give me a PLAN listing every file you will create and every assumption. Wait for my approval ONCE. Then implement TASK 0 to TASK 6 in order (TASK 4b included) and finish with the SELF-CHECK report (rule 13).
```

**DONE WHEN:** `python scripts/start.py` se Docker + backend + frontend chalte hain; `/health` ok; `docs/reference/INDEX.md`, `docs/ui/UI_INVENTORY.md`, `docs/RULES.md`, `docs/API_CONTRACT.md` bane hain aur tumne padhe; agent ki SELF-CHECK table aayi.

---

## PHASE 1 — Test-data generator + hardcode audit (sirf dev tools, app se alag)

> ### TUMHARA KAAM — PHASE 1
> **Pehle:** kuch nahi. **Beech me:** plan approve. 
> **Baad me:** `python scripts/generate_data.py --scenario ring --seed 7 --format messy --size small --out data/synthetic/t1` chalao. Excel kholo: title rows, ajeeb headers, comma wale amounts dikhne chahiye. `python scripts/audit_hardcode.py` chalao (abhi pass hona chahiye).
> **Bahar ka kaam:** koi nahi.

Yeh tumhari "external data" ka stand-in hai jab tak tumhare paas apni files nahi hain. Yeh app ko test karne ke liye **alag-alag shape ki files** banata hai, taaki saabit ho ki app hardcoded nahi hai.

```text
Read docs/RULES.md. Write scripts/generate_data.py: a DEV-ONLY, deterministic (seeded) generator. The app and its tests/ may call it as a subprocess; app/ must NEVER import it.

CLI: python scripts/generate_data.py --scenario <name> --seed <int> --format <clean|messy|statement|paysim> --size <small|medium|large> --out <dir>

SCENARIOS (all names, numbers, dates, amounts come from the seed via Faker locale en_IN; nothing fixed):
 ring: a layered fraud network. Parameters drawn from the seed within ranges: 3-6 victims paying into one collection account; 2-4 mule accounts; 1 'organiser' entity who appears in NO FIR but links a recruiter group and a mule group through calls and receives pooled money; 1 shell organisation receiving the onward transfer; money moves in dated waves; the organiser's phone is a NEW SIM whose daily calls ramp up (baseline few calls/day for ~1 week, then a spike) before the first FIR date; 3-5 FIRs at different police stations where the same person appears under name variants and different identifiers; 
 benign_heavy: a different graph with no planted ring: one call-centre-like number with very high steady call volume, one shop-like account with many small inflows (both are decoys), plus random noise people. Tests that no false high-priority lead appears for pure volume.
 cdr_only: only a CDR file (no bank, no FIR, no SDR).
 bank_only: only bank data.
 chain: a plain linear layering A->B->C->D->E->F of transfers with only 1-2 calls between the owners (no recruiters, no shell): tests that the engine does not need the 'ring' shape.
 hub_spoke: one hub phone calling many spokes, no bank data: tests bridge/degree logic on a different topology.
 two_rings: two independent rings in one case (different victims, accounts, organisers): tests that nothing assumes exactly one organiser.
 sparse_tiny: 10-40 rows in total and 1-2 FIRs: tests graceful behaviour with almost no data ('insufficient data' labels, no crash, low confidence).
 random_mix: random counts of every element drawn from wide ranges (people 5-200, calls 50-5000, accounts 3-100) with a random topology; its ground_truth.json records only structural facts (row counts, totals, distinct counts), so tests on it check invariants (idempotence, no crash, totals, case isolation, no HIGH lead on pure volume decoys).
 NOISE for every scenario: 10-30 noise people/phones/accounts; random calls/transfers; relatives sharing one phone with the same surname but different first names; an FIR mentioning an initial-only name ("R. Surname") compatible with 2 people; ~3% dirty rows (typos, missing amount, invalid phone, exact duplicate rows, mixed date formats in a few rows).

FORMATS (same underlying scenario rendered in different shapes, so tests can check format-invariance):
 clean: cdr.csv(call_id,caller,receiver,date,time,duration_seconds), bank_transactions.csv(txn_id,date,time,from_account,from_name,to_account,to_name,amount,reference), sdr.csv(phone,subscriber_name,activation_date), account_master.csv(account_no,holder_name,registered_mobile,branch,opened_date), FIR .txt, text-PDF and .docx versions; identity files with DIFFERENT shapes: persons.csv (name + phone + account + vehicle + email in one row), vehicles.csv (registration + owner + location + date), ip_logs.csv (phone + ip + datetime); and JSON variants (cdr.json, bank_transactions.json as lists of records).
 messy: .xlsx and .csv with different headers (e.g. 'A-Party','B-Party','Call Date','Call Time','Dur(sec)','Call Type' with values like MOC/MTC; bank 'Txn Date','Value Date','Remitter A/c','Beneficiary A/c','Amount (INR)'), 2-5 title/banner rows before the header, dd/mm/yyyy dates, '+91 98xxx xxxxx' and '0'-prefixed phones, amounts like '5,00,000.00', trailing totals row, one file in cp1252 encoding, one Excel file with 2 sheets.
 statement: bank data as SINGLE-ACCOUNT statements: header lines with 'Account No: ...', then Date, Narration, Withdrawal/Debit, Deposit/Credit, Balance; narrations like 'UPI/<12-digit ref>/<name>@<bank>/payment', 'NEFT-<ref>-<NAME>-<acct>', 'IMPS/<ref>/<NAME>', 'ATM WDL', 'POS ...'. Each ring account has its own statement so the same transfer appears in both the payer and payee statements.
 paysim: PaySim-style rows (step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud) where 'step' = hours since an unknown start; account ids alphanumeric like 'C1234567890'.
 --size: small ~800 CDR/300 bank rows; medium ~20k/5k; large ~200k/50k.

OUTPUT: files + ground_truth.json that is TEST-ONLY and records for the seed: role of each planted entity (identified by the phone/account numbers actually generated), true identity clusters of name variants, expected totals (inflow to the collection account, total money volume, row counts after de-duplication, rejected-row counts per planted defect), the first date on which the planted new-SIM phone exceeds a reasonable spike (record onset date and peak date), decoy identifiers.
ALSO write tests/test_generator.py: same seed -> byte-identical output; different seeds -> different names/numbers; every format produces the same underlying counts in ground_truth.json; organiser appears in no FIR.

TASK — scripts/audit_hardcode.py (runs in every later phase; non-zero exit on findings)
 Scan backend app/ and frontend/src/ (exclude tests/, scripts/generate_data.py, config/*.yaml, docs/, *.md, node_modules, lock files) for: (1) any value taken from the generator output of 3 reference seeds (names, phones, accounts, vehicle numbers, emails, IPs, FIR numbers); build this set by running the generator into a temp dir at audit time; (2) any 10-digit mobile-like or 9-18 digit account-like literal; (3) any date literal 2015-2035 outside comments; (4) any hard-coded rupee amount used as a threshold; (5) JSON/CSV files under frontend/src or app/ that look like mock data; (6) the words criminal, suspect, guilty, mastermind in frontend/src, report templates, config yaml templates or API response messages; (7) fetch()/import URLs to external hosts (offline rule). Print file:line per finding. An allow-list file scripts/audit_allowlist.txt may exempt an entry only with a written reason. Add tests/test_audit.py proving the audit catches a planted literal in a temporary file and passes on clean code.
Show me a sample of each format and run the tests.
```

**DONE WHEN:** `--format messy` ki Excel file tum Excel me kholke dekho: title rows, ajeeb headers, comma amounts. Yahi tumhari asli files jaisi hogi. `python scripts/audit_hardcode.py` pass hota hai aur test me planted literal pakadta bhi hai.

---

## PHASE 2 — Auth, cases, evidence upload, SHA-256, audit log, UI shell (Stitch UI se)

> ### TUMHARA KAAM — PHASE 2
> **Pehle:** kuch nahi (UI ZIP tum Phase 0 me de chuke). Agar Phase 0 ke baad naye Stitch screens banaye hain to unki ZIP `inbox/` me daalo aur prompt ke saath likho: `New Stitch ZIP added to inbox/, re-run the UI inventory first.`
> **Beech me:** agent Part A me max 10 sawal ek saath puchega. Jawab do, ya na do (wo assumptions `docs/ui/ASSUMPTIONS.md` me likh ke aage badhega).
> **Baad me:** `python scripts/seed_users.py` (terminal me admin password tum daaloge, code me koi default password nahi). Login karo, case banao, file upload karo, SHA-256 dekho, "Verify log" chalao. Agent ki side-by-side screenshots (`docs/ui/compare/`) apni Stitch images se milao.
> **Bahar ka kaam:** koi nahi.


```text
Read docs/RULES.md, docs/API_CONTRACT.md, docs/ui/UI_INVENTORY.md, SCREEN_MAP.md and DESIGN_TOKENS.md. The Stitch pack in docs/ui/pack/ is the visual source of truth for LAYOUT (never for content).

PART A — READ THE UI PACK (no feature code yet)
 Phase 0 already produced docs/ui/UI_INVENTORY.md, SCREEN_MAP.md and DESIGN_TOKENS.md from the Stitch pack in docs/ui/pack/. Re-read them together with the real images/HTML. Then list AT MOST 10 concrete open questions (ambiguities, missing screens, charts that are only pictures) in ONE batch. For anything I do not answer, make the most consistent choice, record it in docs/ui/ASSUMPTIONS.md and continue. Stop for approval only if a question truly blocks the work.

PART B — BACKEND
 Auth: users(id, username, password_hash, role admin|investigator|viewer, is_active). bcrypt, JWT HS256 8h from .env secret. POST /auth/login, GET /auth/me; dependencies get_current_user, require_role. scripts/seed_users.py asks for passwords on the terminal (no default passwords in code).
 Permissions: viewer read-only; investigator + upload/approve/decide/report; admin + audit verify and users.
 Cases: cases(id, title, description, priority, status, created_by, created_at) + case_members. A user opens only cases they belong to (admin sees all). One dependency enforces membership on EVERY case-scoped endpoint, present and future. Endpoints addressed by their own id (/evidence/{id}/..., /matches/{id}/..., /extracted/{id}, /reports/{id}/...) first resolve the owning case and enforce the same check; every later phase adds a non-member test for each such endpoint family it introduces.
 Evidence upload: POST /cases/{id}/evidence (multipart, multiple files). Validate extension (csv, xlsx, json, jsonl, txt, pdf, docx), size (<= 200 MB for tabular/json, 20 MB for pdf/docx/txt), magic bytes for pdf/xlsx/docx (docx and xlsx are zip files). Stream-compute SHA-256 while saving to UPLOAD_DIR/<case_id>/<uuid>_<name>, read-only, never overwrite. Store original name, stored path, sha256, size, uploader, time, status 'uploaded' (later 'mapped' -> 'ingesting' -> 'ingested' | 'failed'). Type detection and mapping come in Phase 3; here just store + hash. POST /evidence/{id}/verify recomputes the hash.
 Audit log hash chain: audit_log(id, ts, user_id, action, case_id, object_type, object_id, details_json, prev_hash, hash), hash = sha256(prev_hash + canonical_json(entry fields)). Audited actions: login, case_create, evidence_upload, evidence_verify, mapping_confirm, ingest, match_approve/reject/undo, link_create, lead_decision, settings_change, report_generate, audit_verify. GET /audit/verify (admin) walks the chain -> {ok, checked, first_broken_id|null}. Add scripts/tamper_demo.py that edits one row in SQLite so verify fails.
 Case settings: GET/PUT /cases/{id}/settings stored as JSON; defaults come from config/defaults.yaml (create the file with empty sections now); PUT is audited.

PART C — FRONTEND SHELL (real pages, NO mock data)
 FIDELITY: build from DESIGN_TOKENS.md and SCREEN_MAP.md (Tailwind theme extended with the exact tokens; fonts via @fontsource; lucide-react icons). After building, screenshot every route at 1366x768 and 1440x900 (Playwright as a devDependency, or the IDE browser) with generator data loaded, save them as docs/ui/compare/<screen>-app.png next to the reference image, list the remaining differences (spacing, colours, missing components) and fix the biggest ones once. Report what still differs; do not claim a pixel-perfect match.
 Vite + React (JS) + Tailwind configured with the design tokens; desktop-first (works at 1366x768 for projectors). AppShell/Sidebar/TopBar, route guards, role-aware menus. Shared components: StatCard, DataTable, Badge (HIGH/MEDIUM/LOW), ConfidenceChip, EmptyState, LoadingSkeleton, Toast, Modal, ConfirmDialog, a shared lakh/crore money formatter (input paise).
 Pages that work now: Login, Cases list + create, Case workspace (details + evidence table with SHA-256 prefix, status, Verify button), Upload page (drag-drop, multi-file, progress), Admin audit page with 'Verify log'. All other pages exist as routes with an EmptyState "Upload data to begin" and disabled controls with tooltip 'wired in phase N'. Every control is wired to real API functions in src/api/client.js (one function per endpoint). No mock JSON anywhere.

TESTS: wrong password 401; viewer upload 403; non-member 403 on any case endpoint; same file twice = two rows, equal hash; altering a stored file -> verify mismatch; tamper script -> audit verify fails at the right id. Show output + screenshots of the pages next to my reference screenshots.
```

**DONE WHEN:** Login → case → file upload → hash dikhta hai; audit verify kaam karta hai; UI Stitch screens ke bahut kareeb hai (side-by-side compare images + bachi differences ki list).

---

## PHASE 3 — Ingestion engine: kisi bhi file ko samajhna (core of "no hardcoding")

> ### TUMHARA KAAM — PHASE 3
> **Pehle (optional par bahut kaam ka):** apni asli/external files (CDR, bank, SDR, KYC, JSON, Excel) `data/user_samples/` me daalo. Agent unpe `probe_file.py` chalake engine ko theek karega aur `docs/PROBE_REPORT.md` banayega. Agar file sensitive hai to `data/private/` me rakho aur khud chalao: `python scripts/probe_file.py data/private/<file>` (default me sirf headers aur masked values print hoti hain).
> **Beech me:** plan approve.
> **Baad me:** UI se ek messy Excel upload karo, mapping dropdowns se confirm karo, data-quality summary dekho. Apni file pe bhi yahi karo.
> **Bahar ka kaam:** agar tumhare bank ki narration alag format ki hai to `backend/config/narration_patterns.yaml` me ek pattern jodna padega (agent example dega). Yeh normal hai.

```text
Read docs/RULES.md. This phase is what lets the user bring ANY CDR/bank/subscriber/KYC file. Build services/ingestion/ and the Upload-flow UI.

A) READERS
 - CSV: try utf-8-sig, then cp1252/latin-1 (charset-normalizer to guess); sniff delimiter. XLSX via openpyxl: list sheets, let the user pick the sheet(s) (default: largest). .xls unsupported -> clear error.
 - JSON / JSONL: a list of flat records (or {"records":[...]} / one nested level flattened with dotted keys) goes through the same pipeline as CSV. .docx, .txt and .pdf narrative files are routed to text_document (Phase 6) after type detection.
 - Header-row detection: scan the first 40 rows, choose the row with the most cells matching config/column_synonyms.yaml (fuzzy, rapidfuzz) as the header; rows above are 'banner' lines (keep them: e.g. 'Account No: 123' is parsed for statement files); drop trailing total/summary rows and fully empty rows.
 - Chunked processing (pandas chunksize / row batches) so 200k+ rows do not blow memory.

B) TYPE DETECTION (scores, not if-else on exact headers)
 Types: cdr, bank_transactions (from/to per row), bank_statement (single-account: debit/credit/narration/balance), identity_table (any table linking an owner NAME to identifiers: SDR/subscriber, KYC/account master, a persons list, a vehicle registry; one row may carry several identifiers), ip_log (identifier + ip + datetime), text_document (txt/pdf/docx narrative such as an FIR -> Phase 6), unknown (user picks the type). For each type compute a score from (1) header synonym matches, (2) data sniffing of the first ~200 values (share that look like 10-digit mobiles, dates, amounts, account ids, UPI ids, Dr/Cr). Return the best type plus alternatives with scores. The user can override.

C) COLUMN MAPPING
 Canonical fields per type (e.g. cdr: caller, receiver, datetime|date+time, duration, call_type/direction, imei, imsi, cell_id, location; bank_transactions: txn_id, datetime|date+time, from_account, to_account, from_name, to_name, amount | debit+credit, reference, balance; bank_statement: date, narration, debit, credit, balance, + statement_account_number (from header banner OR asked from the user); identity_table: name + ANY of phone, account, vehicle, email, ip, imei, address, dob, activation_date, registered_mobile, location, date (a row may carry several identifiers; every identifier in a row is linked to that row's name); ip_log: identifier (phone or account or name), ip, datetime).
 Suggest mapping from synonyms + sniffing with a confidence per column; POST /cases/{id}/evidence returns {detected_type, alternatives, suggested_mapping, preview: first 20 raw rows, issues}. The UI shows the preview table with a dropdown on each column header (canonical field or 'ignore'), required-field warnings, date-format selector (dayfirst default true; detect ambiguity), direction mapping (map the user's call-type values to in/out/sms/other, e.g. MOC->out), amount mode (single amount + Dr/Cr, or separate debit/credit columns), a 'time offset' mode for datasets with only a relative hour/step column + user-given start date (PaySim-style). The user confirms with POST /evidence/{id}/mapping (audited). Save the mapping as a template keyed by the header-signature hash; the next file with the same headers is auto-mapped (still shown for confirmation).

D) NORMALISERS (services/ingestion/normalize.py, pure functions with unit tests)
 - phone: strip non-digits; drop leading 91 when length 12; drop leading 0 when length 11; valid_mobile = 10 digits starting 6-9; other numbers (landline, toll-free, short codes, international) are KEPT with valid_mobile=false; alphanumeric SMS sender ids kept as kind='sms_header'. Empty -> reject.
 - account id: trim, uppercase, remove spaces/dashes; keep alphanumerics.
 - amount: parse '5,00,000.00', '(1,200)', 'Rs 5 lakh' style when present; Dr/Cr; result integer PAISE (use Decimal, never float).
 - datetime: dayfirst, Excel serials, combined or separate date/time columns, timezone-naive local; keep raw string too.
 - duration: seconds, 'mm:ss', 'hh:mm:ss'.
 - name: normalised form (lowercase, collapse spaces, strip punctuation/titles) + keep original.
 - vehicle registration: uppercase, strip spaces/dashes. email: lowercase, trimmed. ip: validate IPv4/IPv6, keep invalid ones in the rejected-rows table.

E) BANK STATEMENT PARSING (single-account format)
 Each row is a transaction between statement_account and a counterparty. Direction from debit/credit. Counterparty extraction from the narration using config/narration_patterns.yaml (editable regex list): UPI (VPA like name@bank + 12-digit ref), NEFT/IMPS/RTGS (UTR/ref, name, optionally account/IFSC), and cash/ATM/POS rows with NO counterparty. Rows with a resolvable counterparty id (account or VPA) become transactions; rows without are kept in the table as 'unlinked' (counted in totals, not drawn as graph edges). Honest limitation: narration formats are bank-specific; unmatched narrations are listed in the data-quality report so the user can add a pattern.
 De-duplication when both sides' statements are uploaded: same UTR/reference, or same (account pair, amount, date +-1 day) -> ONE transaction, both source refs stored.

F) STAGING + DEDUPE + QUALITY
 Write cleaned rows to SQLite call_records / transactions / ip_events / entities (identity_table rows) with source_file + source_ref (row number). Row fingerprint = hash(normalised fields) (+ occurrence index within the file) so uploading the same file twice never doubles anything, but two genuinely identical-looking rows in one file are both kept. Rejected rows -> table with reason (missing phone, bad date, unparsable amount, ...). GET /evidence/{id}/rejected-rows (+CSV download). Data-quality summary per file: rows read, ingested, rejected by reason, duplicates skipped, date range, distinct phones/accounts, unmatched narrations, mapping confidence.
 If an optional imei column is mapped, store it (call_records.imei) for the shared-device analytics in Phase 8. Tower/location columns are stored but NO map features are built.

G) JOB RUNNER
 POST /evidence/{id}/ingest creates a job (FastAPI BackgroundTasks is fine) -> GET /jobs/{id} progress and steps (read, map, clean, stage, [later: graph build, analytics]). The frontend polls and shows a step-by-step progress card and then the data-quality summary. Failures show a readable error, never a stack trace.

H) scripts/probe_file.py <path> [--no-ingest] [--show-rows]
 Runs the SAME detection / mapping / cleaning code as the API on any file or folder (no server, temporary SQLite) and prints: detected type + alternatives with scores, header row found, suggested mapping with confidences, rows read / clean / rejected by reason, distinct phones/accounts/names, date range, unmatched narrations, and the first problems a human should fix. By default it prints column names and MASKED sample values only (e.g. 98xxxxxx10); raw rows only with --show-rows. This is how I check my own private files without sending them anywhere, and how we prove the engine is not tied to generator formats. Write docs/PROBE_REPORT.md covering every file in data/user_samples/ (if any): what worked, what needed manual mapping, what failed, honestly.

TESTS (pytest; run through the generator via subprocess):
 - Format invariance: generate the same scenario+seed in clean, messy, statement and paysim formats, ingest each through the UI-equivalent API (accepting the suggested mapping, fixing only what the test marks as needing override), and assert row counts, total money and distinct counterparties equal ground_truth.json (statement format: after de-duplication).
 - Type detection picks the right type for each generated file; header detection finds the header under 2-5 banner rows; the cp1252 file decodes; the 2-sheet workbook offers both sheets.
 - Normaliser unit tests for the tricky phone/amount/date forms; an amount never goes through float.
 - Uploading the same file twice leaves counts unchanged. Rejected rows match the planted defects.
 - A mapping template is re-used for a second file with the same headers.
 - Performance: 200k-row CDR ingests without memory blow-up (report time and peak memory).
 - Identity-table invariance: persons.csv / vehicles.csv / ip_logs.csv shapes are detected as identity_table / ip_log and every identifier is staged; the json variants give the same counts as the csv ones.
 - Unseen headers: take the messy format, shuffle column order and rename headers to spellings the synonym list does not contain (for example 'Originating No', 'Terminating No', 'Dt', 'Tm'); the engine must either map them by data sniffing or mark them 'needs mapping'; assert it NEVER maps a column wrongly with confidence above 0.8, and record which columns it could not map.
Show output.
```

**DONE WHEN:** Generator ki `messy` Excel file upload karo → app sahi type pehchaanta hai, mapping suggest karta hai, tum confirm karte ho, data-quality summary dikhti hai. Tumhari **apni** file bhi isi flow se jaati hai (pehle `python scripts/probe_file.py <file>` se dekh lo); jahan mapping galat ho wahan tum dropdown se sahi karte ho.

**Sachchai:** Har bank ka narration format alag hota hai. Agent kuch patterns dega, aur baaki tumhe `narration_patterns.yaml` me jodne honge. Yeh normal hai, chhupao mat.

---

## PHASE 4 — Graph builder + hop search + Graph Explorer (data se)

> ### TUMHARA KAAM — PHASE 4
> **Pehle:** (recommended) Neo4j GraphAcademy "Cypher Fundamentals" course.
> **Beech me:** plan approve.
> **Baad me:** koi bhi uploaded number/naam search karo, hops 1 se 4 badhao, Entity/Detail view toggle karo. Agent ki final Cypher ko Neo4j Browser me khud chalao.
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md. Build services/graph_builder.py, services/graph.py and the Graph Explorer screen. Everything derives from the SQLite staging tables.

GRAPH MODEL (every node: key, case_id; every relationship: case_id, source_file, source_ref, method, confidence)
 Node key = "<case_id>|<Label>|<normalised id>". Labels: Phone{number, valid_mobile, first_seen, last_seen, activation_date?}, BankAccount{id, holder_name?, registered_mobile?}, Person{name}, Organization{name}, Vehicle, FIR, Device{imei}, VPA{handle}, IP{address}.
 Detail relationships:
  (Person|Organization)-[:USES]->(Phone)       from identity tables (subscriber/SDR name + phone, KYC registered_mobile, persons lists), FIR extraction, officer links
  (Person|Organization)-[:OWNS]->(BankAccount) from identity tables (KYC holder, persons lists), bank from_name/to_name, FIR extraction, officer links
  (Phone)-[:CALLED {count,total_duration,first_call,last_call}]->(Phone)   aggregated per ordered pair, computed from call_records
  (BankAccount)-[:TRANSFERRED_TO {txn_key, amount_paise, date, datetime, reference, source_file, source_ref}]->(BankAccount)  ONE per transaction, MERGE on txn_key so re-runs are idempotent
  (Phone)-[:USED_ON]->(Device) when imei exists.
  (Person|Organization)-[:DRIVES]->(Vehicle) from identity tables, FIR extraction and officer links.
  (Phone)-[:SEEN_ON_IP {count, first_seen, last_seen}]->(IP) from ip_log; a shared IP is stored but NEVER creates an entity-view link by itself.
 Person key rule: exact normalised-name equality within a case = same node; it is recorded with method='name_equality' and shown in the details panel as 'identity by exact name (different people can share a name)'. Fuzzy variants stay separate (Phase 7 suggests merges). This is the ONE deliberate exception to 'no automatic merges' (otherwise every structured table would need thousands of approvals); document the common-name collision limitation in code comments, the README and the profile/lead pages. If one phone/account maps to several different owner names, keep ALL owner links, mark the entity shared=true, and do NOT collapse it into one owner.

ENTITY VIEW (what the hop buttons use) — derived, rebuilt by rebuild_projection(case_id)
 entity_of(x) = its single unambiguous owner (MasterProfile if resolved, else Person/Organization) if one exists, otherwise x itself (an unowned phone or account is its own entity). This is why the app works with a CDR-only upload.
 (Entity)-[:COMMUNICATES_WITH {calls, last_call, phones:[...]}]-(Entity)   from CALLED edges collapsed through entity_of
 (Entity)-[:PAID {total_paise, txn_count, first_date, last_date, txn_keys:[...]}]->(Entity)   from TRANSFERRED_TO collapsed through entity_of
 method='derived'; the underlying keys are stored so 'Why this link?' can show raw evidence. Hop counts are ENTITY hops.
 rebuild_graph(case_id): drop this case's nodes in Neo4j and recreate everything from SQLite (batched UNWIND, 5k rows per batch), then rebuild_projection. It runs automatically at the end of an ingest job and after any approval/undo/link change (incrementally if easy, full rebuild otherwise).

API
 GET /cases/{id}/graph/search?q=&hops=&view=entity|detail&types=&limit=200: q matches name, phone, account, vehicle, FIR number (case-insensitive, partial, ranked); returns candidates if several match (UI asks the user to pick). expand(): view=entity traverses only COMMUNICATES_WITH|PAID (undirected); view=detail traverses the detail relationships. hops validated {1,2,3,4}. Standard graph response, truncated flag at limit.
 GET /cases/{id}/graph/path?from=&to= shortest path (cap length 6, entity view default).
 POST /cases/{id}/links: officer-created owner link {entity_id, owner_name|owner_id, kind phone|account}, method='officer', stored in SQLite, audited, graph rebuilt. DELETE to undo.

FRONTEND (Graph Explorer per screenshot): search box with candidate picker, hop buttons 1-4, view toggle (Entity view / Detail view), node-type filter chips, Cytoscape canvas ('cose' layout, colour by type, size by degree, edge width by calls or amount), click node -> details panel (type, ids, owners, degree, first/last seen, links to provenance), click edge -> provenance card (source file + row/page, method, confidence), select two nodes -> shortest path highlighted, 'truncated' banner, 'Assign owner' action on unowned phones/accounts. Never render more than the server cap; expanding a node fetches its neighbours.

TESTS (run over generated scenarios, parametrised by seed; NO fixed names in assertions — read identifiers from ground_truth.json):
 - ring scenario: starting from a recruiter's phone/entity, hops=2 reaches the organiser entity; from the collection account, money-side hops reach the shell organisation; the organiser is NOT linked to any FIR node.
 - cdr_only scenario: graph builds with phones as entities, no crash, hop search works.
 - re-running ingest/rebuild gives identical node/edge counts (idempotent); another case's search returns nothing from this case.
 - shared-phone relatives are marked shared=true and not collapsed.
 - ip_log data creates IP nodes and SEEN_ON_IP edges; a shared IP alone adds no entity-view link.
 - topologies chain, hub_spoke, two_rings, sparse_tiny and random_mix: the graph builds, hop search works, rebuild is idempotent, nothing assumes a single organiser.
 - a hop query completes in < 1 s on the medium size. Show the final Cypher of the hop query.
```

**DONE WHEN:** Tum koi bhi uploaded file ka number/naam search karte ho, hops badhate ho, graph asli data se aata hai. CDR-only upload bhi chalti hai.

---

## PHASE 5 — Money Trail Explorer (hero #2)

> ### TUMHARA KAAM — PHASE 5
> **Pehle:** kuch nahi. **Beech me:** plan approve.
> **Baad me:** koi bhi account chuno, amount quantile chips se filter badlo (edges grey/hide hone chahiye), direction in/out/both try karo. Settings me threshold badal ke flags badalte dekho.
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md. Money trail runs on the BankAccount-level graph (:TRANSFERRED_TO) and works for ANY account in the uploaded data.

BACKEND services/money_trail.py + GET /cases/{id}/money-trail?account=&min_amount=&hops=&direction=in|out|both
 - account: id or partial (search, same candidate-picker idea). hops validated {1..4}. min_amount in rupees from the UI converted to paise.
 - direction out: MATCH path=(a:BankAccount {key:$key})-[:TRANSFERRED_TO*1..N]->(b) WHERE ALL(r IN relationships(path) WHERE r.amount_paise >= $min AND r.case_id=$case) RETURN path LIMIT $cap. in: reversed. both: merge. Use neo4j.Query with a timeout; on timeout return a clear 'too many paths — raise the filter or reduce hops' message. Paths over per-transaction edges multiply when one pair has many transactions: BEFORE path expansion collapse the qualifying transactions (amount >= filter) of each (from,to) pair into one weighted edge in a BankAccount-level projection (keep txn_keys for evidence), or use DISTINCT-node expansion, so 3-4 hops stay fast. Cap nodes (default 200) and set truncated.
 - Response: standard graph (aggregate parallel txns per pair for drawing, keep txn_keys), plus totals for the focus account {inflow, outflow, txn_count, counterparties}, ordered paths (accounts, amounts, dates, txn ids), and hidden_edges (edges below the filter touching visible nodes) for grey dashed drawing.
 - Amount presets are DATA-DRIVEN: GET /cases/{id}/analytics/txn-volume (implement it now; Phase 8 extends it) also returns amount quantiles (p50, p75, p90, p99) of this case; the UI offers those as quick filters plus custom input. No fixed rupee presets.
 - Account nodes show holder/owner names where known, else the account id.
PATTERN FLAGS (services/patterns_money.py; every threshold from case settings/defaults.yaml and printed in the explanation; labelled 'Potential anomaly'; add each key you need to config/defaults.yaml with a comment so it shows up in the Settings screen):
 - fan_in: >= K distinct sources into one account within W days (defaults K=3, W=7).
 - fan_out: one account to >= K distinct destinations within W days.
 - rapid_pass_through: >= R% of an account's inflow leaves within H hours of arrival (defaults R=80, H=48), computed with pandas on the transactions table.
 - near_limit_splitting: only if the user sets a 'reporting limit' in Settings: >= 3 transfers between 90% and 100% of the limit by one sender within 3 days. Disabled when no limit is set.
 Each flag: account, pattern, a sentence with real numbers and thresholds, txn ids as evidence.
FRONTEND (Money Trail per screenshot): account picker, amount filter (data-driven quantile chips + custom), hops, direction; Cytoscape directed layout (left-to-right), edge width ~ amount, label with lakh/crore formatter, hidden edges dashed grey; side panel: totals, path list, flag badges with explanations, transactions table (sortable, CSV export), click edge -> txn ids + source rows. Empty state when the case has no bank data.

TESTS (parametrised by seed, identifiers from ground_truth.json): collection account out/3 hops reaches the shell organisation; raising the filter above the smallest transfer hides it and it appears in hidden_edges; totals equal ground truth; the pooling account is flagged fan_in and rapid_pass_through; the benign_heavy shop-like decoy is NOT flagged rapid_pass_through; statement-format ingestion gives the same trail as clean format; a bank_only case works; threshold change in settings changes flags (assert via API). Run time < 1 s on medium; a pair with 500 parallel transactions plus 4 hops stays < 2 s. Show output.
```

**DONE WHEN:** Koi bhi account choose karke trail dikhta hai; filter slider/quantile chips se edges grey/hide hote hain.

---

## PHASE 6 — Text extraction + review (FIR ya koi bhi text document)

> ### TUMHARA KAAM — PHASE 6
> **Pehle (optional):** apni text-based FIR / complaint (txt, pdf, docx) `data/user_samples/` me. Scanned PDF ya sirf Devanagari documents is version me nahi padhe jaayenge (agent saaf error dega).
> **Beech me:** plan approve.
> **Baad me:** Entity Review screen me highlights, approve/reject/edit, bulk approve try karo. `python scripts/eval_extraction.py` ke precision/recall numbers note karo (judge puchega).
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md. Input: any text-based PDF, .txt, .docx or pasted text; any narrative document (FIR, complaint, bank notice, case note). FIR number and police station are OPTIONAL: a document without them is still processed. Scanned PDFs, OCR and Devanagari are OUT OF SCOPE: scanned PDFs are marked 'failed: scanned PDF — OCR not supported in this version'; a document containing Devanagari is processed on its Latin-script parts and marked 'partially supported: Devanagari text ignored'.

PIPELINE (services/extraction/)
 1. text.py: pdfplumber per-page text (keep page numbers) / plain text / python-docx paragraphs (no pages: use the paragraph index as source_ref).
 2. rules.py (deterministic; each match: value, normalised, span, page, confidence):
   phone: (?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d); account: 9-18 digits (or alphanumeric id) ONLY within ~40 chars after 'account', 'a/c', 'acct', 'A/C No', never a number already taken as phone; masked/partial accounts ('XXXXXX7890', 'ending 7890') -> type ACCOUNT_SUFFIX (confidence 0.4, never auto-linkable); vehicle: [A-Z]{2}[ -]?\d{1,2}[ -]?[A-Z]{1,3}[ -]?\d{4} normalised without spaces; amount: Rs/Rs./₹/INR, '5 lakh', '3 lac', '1.5 crore', '500000 INR' -> paise; dates in many forms -> ISO; email; IPv4; UPI id; FIR number patterns ('FIR No. 123/2026', 'FIR-2026-001').
 3. ner.py: spaCy en_core_web_sm for PERSON/GPE/ORG + fallback rule: capitalised 2-3-word sequences after titles/keywords (Shri, Smt, Mr, Mrs, Ms, accused, complainant, victim, 'named', 'alias', 'known as') are PERSON candidates (confidence 0.6; strip titles). Regex wins over NER on overlaps. Police station via 'Police Station' / 'PS' keywords.
 4. Relationship candidates ONLY from sentence (or 2-sentence window) co-occurrence of a PERSON with a PHONE/ACCOUNT/VEHICLE: confidence = min(entity confidences) * 0.8, with the sentence stored as evidence.
 5. Everything is saved as 'pending_review' in SQLite extracted_entities. NOTHING reaches the graph before an officer approves.
REVIEW API: list pending (filters type/confidence), approve, reject, edit, add missing entity manually (method='officer'), approve-all-above?threshold= (investigator only, audited). On approval: write to SQLite entities/entity_links, then rebuild_graph (FIR node {number, police_station, date}; (Person)-[:MENTIONED_IN]->(FIR) with page + sentence provenance).
FRONTEND (Entity Review per screenshot): left = FIR text with colour-highlighted spans (click selects the entity), right = entity table with confidence chips, approve/reject/edit, bulk approve for confidence >= threshold, Add entity, page numbers. Works for any number of FIRs; list of documents with their review progress.

TESTS: run on generated FIRs for several seeds: all phones, vehicles, amounts and dates found; the 10-digit account is classified ACCOUNT (because of 'a/c') not phone; 'ending NNNN' becomes ACCOUNT_SUFFIX. scripts/eval_extraction.py compares extraction with ground_truth.json and prints precision/recall per entity type for each seed. Report misses honestly. A scanned/empty-text PDF fails gracefully. Also run on text with extra whitespace, line breaks inside numbers and a Devanagari sentence: no crash, and the 'partially supported' note appears.
```

**DONE WHEN:** Koi bhi FIR upload karo → highlights → approve → graph me FIR links aate hain. `eval_extraction.py` ke numbers tumhare paas hain.

**Sachchai:** NER Indian names pe kamzor hai. Recall kam aaye to chhupao mat. "Human review isi liye hai" yehi jawab hai.

**Optional 6B (default OFF):** LLM-assisted extraction sirf synthetic text pe, jahan har returned entity string FIR text me **word-for-word** milni chahiye, warna discard; confidence cap 0.7; phir bhi officer review se guzre.

---

## PHASE 7 — Entity matching + Cross-FIR Master Profile (hero #1)

> ### TUMHARA KAAM — PHASE 7
> **Pehle:** kuch nahi. **Beech me:** plan approve.
> **Baad me:** Matches queue me HIGH suggestion approve karo, Master Profile dekho, Undo karo (graph pehle jaisa hona chahiye). Rishtedaar wali SHARED_DEVICE warning dekho. `python scripts/eval_matching.py` ke numbers note karo.
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md. services/matching.py. Decisions (suggestions, approvals, undo) are stored in SQLite (match_suggestions, profile_members); Neo4j is synced by rebuild_graph.

CANDIDATES (never O(n^2))
 a) every Phone/BankAccount/Vehicle/Email/Device shared by >= 2 distinct Person nodes -> candidate pairs; b) name blocking by normalised surname + phonetic key -> pairs within a block.
NAME COMPATIBILITY (rapidfuzz JaroWinkler.normalized_similarity; normalise: lowercase, strip titles and punctuation)
 surname_ok = surname similarity >= 0.90; first_ok = first-name similarity >= 0.85 OR initial-compatible OR one side lacks a first name; name_compatible = surname_ok AND first_ok. Surname equality alone is NOT similarity. ambiguous = an initial-only name is compatible with >= 2 DISTINCT persons.
STRENGTHS (config/defaults.yaml, tunable per case): same account 95, phone 90, vehicle 90, email 85, device(imei) 70, DOB + similar name 60, same address 35, similar name only 25, same IP 20 (very weak: never a reason to suggest a merge on its own).
LEVELS
 HIGH: shares a strong ID AND name_compatible AND NOT ambiguous.
 MEDIUM: shares a strong ID AND ambiguous; or two medium signals.
 SHARED_DEVICE flag (no merge suggestion): shares a strong ID but NOT name_compatible, or one phone/address attached to >= 3 different persons.
 LOW: name-only; listed under 'Possible'; NO approve button.
 Each suggestion: both records, level, score, human-readable reasons with the actual shared values, evidence refs (documents/pages/rows), status pending|approved|rejected|undone.
MASTER PROFILE (non-destructive): approve -> profile_members row; in Neo4j (Person)-[:RESOLVED_TO {approved_by, approved_at, match_id}]->(:MasterProfile). Person nodes are never deleted. Undo removes the link and marks the suggestion 'undone'. Both audited. rebuild_projection represents resolved persons by their MasterProfile (sum calls/amounts); detail view unchanged.
 GET /cases/{id}/profiles/{profile_id}: also_known_as, phones, accounts, vehicles, FIR list (number, station, date), connections, timeline events, every fact with its source.
 Cross-case alert (small extra): when a phone/account/vehicle value already exists in another case the officer can open, create an alert 'Seen in another case' showing only the value and that case's id/title.
ENDPOINTS: GET /cases/{id}/matches?level=&status=, POST /matches/{id}/approve|reject|undo.
FRONTEND: Matches queue (two records side by side, confidence badge, reasons, Approve/Reject), Undo with confirm dialog, SHARED_DEVICE warnings in amber, Master Profile page with 'also known as' chips and source links on every field, cross-case alert badge in the sidebar, 'Possible' tab for LOW items.

TESTS (parametrised by seed, from ground_truth.json clusters): name variants of the planted person -> HIGH suggestions into one profile; relatives sharing a phone -> SHARED_DEVICE, not merge; the initial-only FIR name compatible with 2 people -> never HIGH; approve then undo restores the previous entity-view graph exactly; scripts/eval_matching.py prints precision/recall of HIGH suggestions vs ground truth for each seed. Show output.
```

**DONE WHEN:** Name variants approve karke ek profile me aate hain; relatives pe warning; Undo kaam karta hai; eval numbers tumhare paas.

---

## PHASE 8 — Analytics engines + Lead Advisor (hero #3) + "Why this link?"

> ### TUMHARA KAAM — PHASE 8
> **Pehle:** kuch nahi. **Beech me:** plan approve.
> **Baad me:** Lead Advisor me kisi lead ka score breakdown dekho (har number ka explanation sentence), Settings me ek weight badlo aur score badalte dekho, benign_heavy data me koi decoy HIGH nahi hona chahiye. Ek lead JSON padho.
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md. All rule-based and explainable. No ML models, no LLM. Every threshold/weight from defaults.yaml, overridable per case, and printed in explanations.

A) COMMUNICATION PATTERNS (services/comm_patterns.py; pandas on call_records)
 - sudden_spike: per phone, build the daily call-count series from its OWN history. For each day, baseline = median and MAD of the preceding window (default 14 days, minimum 5 days of history); threshold = median + k * 1.4826 * MAD (k default 3) with a minimum floor (default 5 calls). Alert on days above threshold; record the first alert day and the peak day. Skip phones with insufficient history (report 'insufficient data').
 - very_frequent_pair: outliers in calls/day per pair above Q3 + 1.5*IQR of the case's pair distribution.
 - sudden_new_connection: a pair whose first call is within X days (default 7) of one side's first appearance (or SDR activation_date if known) AND whose count in the first 3 days exceeds a threshold.
 - shared_device: an IMEI used by >= 2 phones (only if imei data exists).
 - bridge: on the entity-level communication graph (NetworkX): betweenness centrality (use k-sampling with a fixed seed when nodes > 3000) and communities via louvain_communities (fixed seed); bridge = high betweenness AND adjacent to >= 2 communities. Wording: 'highest-betweenness bridge', never 'the only link'.
 - Compare the earliest alert date with the earliest FIR/document date in the case (if any) and store 'N days before first document'.
 Alerts saved in SQLite alerts with date, entity, pattern, explanation (real numbers + threshold), evidence ids. Endpoint GET /cases/{id}/alerts.

B) LEAD ADVISOR (services/lead_advisor.py; weights in defaults.yaml, sum 100; editable in Settings)
 Signals, each normalised to 0..1 using PERCENTILE RANK within this case, then multiplied by weight:
  money_flow (30): 0.6 * percentile rank of throughput = min(total inflow, total outflow) among accounts of the case with throughput > 0, + 0.4 * (1 if the entity's accounts carry fan_in / fan_out / rapid_pass_through, else 0).
  bridge (25): 0.5 * betweenness / max betweenness + 0.5 * (1 if adjacent to >= 2 communities).
  unusual_communication (20): from the strongest sudden_spike / sudden_new_connection / pair-outlier alert (peak / threshold, capped at 1).
  timing (15): 1 if a communication alert falls within +-2 days of a transaction >= the case's p90 amount touching the entity's accounts, decaying linearly to 0 at +-7 days.
  multi_document (10): distinct FIR/documents linked within 2 hops / total documents (not available when no documents).
 AVAILABILITY: a signal whose source data type was never uploaded is marked 'not available'; priority = sum(score of available signals) / sum(weights of available signals) * 100; confidence (Low/Medium/High) drops with fewer available signals and with missing 'required_data'. Never fake zeros.
 Levels: HIGH >= 70, MEDIUM 40-69, LOW < 40 (configurable). NO past-criminal-record signal (bias risk) — document why.
 patterns.yaml: a small rule library (e.g. mule_account_network: fan_in + rapid_pass_through + organisation beneficiary; communication_ring: bridge + spike) with required_data lists (full KYC documents, >= 30 days of statements, tower location data, SIM verification details, device records). 'Missing data' = required_data items not present among this case's uploaded evidence types.
 Lead object: entity/profile, priority, level, confidence, per-signal breakdown (score, max, explanation sentence with real numbers, 'not available' where relevant), evidence ids (txn keys, call ids, documents), matched pattern, missing_data, suggested_next_steps (templated from patterns.yaml, e.g. 'request KYC and SIM details through proper legal procedure'), disclaimer 'Lead for review — not a finding of wrongdoing'.
 POST /cases/{id}/leads/{lead_id}/decision {accept|reject|need_more_data, note} (investigator), audited. GET /cases/{id}/leads, GET /cases/{id}/entities/{entity_id}/why.
 Template-only plain-English summary on profile/lead pages (from computed facts, no LLM).

C) PROVENANCE ('Why this link?') GET /cases/{id}/provenance?edge_id=|node_id=: what it connects, source file(s), row/page, method, confidence, approved_by/at; for derived edges the underlying txn_keys/call counts with their own source rows.

D) ANALYTICS ENDPOINTS for the dashboard (all computed from SQLite/graph, with date-range filter): overview (files, rows ingested/rejected, entity counts by type, edges, total money volume, date span), calls-per-day (with spike markers), txn-volume (+ amount quantiles), top-entities (by degree, calls, throughput), communities (nodes with community ids), degree-distribution, call-heatmap (weekday x hour).
FRONTEND: Lead Advisor panel (suggested leads list with level badges, score-breakdown bars with 'not available' states, evidence links opening provenance, missing-data checklist, next steps, Accept/Reject/Need-more-data with note), 'Why is this entity important?' button on every node, Alerts screen, a shared ProvenanceCard component used in every graph screen.

TESTS (parametrised by seed): the planted organiser ranks #1 or in the top 3 and is HIGH; in benign_heavy no entity reaches HIGH purely on call/volume decoys; the decoy high-volume number has no sudden_spike; cdr_only case still returns leads with money signals 'not available' and lower confidence; breakdown sums to the priority; changing a weight in settings changes scores without code changes; the first alert for the planted new-SIM phone falls within +-1 day of ground truth onset; analytics endpoints reflect uploaded data only; on chain, hub_spoke, two_rings, sparse_tiny and random_mix: no crash, two_rings gives two separate high-priority leads, sparse_tiny shows 'insufficient data' labels and lower confidence. Show output and one full lead JSON.
```

**DONE WHEN:** Koi bhi data upload karke leads, alerts aur analytics aate hain; benign decoy HIGH nahi banta; settings badalne se score badalta hai.

---

## PHASE 9 — Dashboard (charts), Timeline, Settings screen, Report

> ### TUMHARA KAAM — PHASE 9
> **Pehle:** kuch nahi (Dashboard / Timeline / Report ke Stitch screens Phase 0 ke pack me hone chahiye; na ho to `UI_INVENTORY.md` ki missing list me thay). **Beech me:** plan approve.
> **Baad me:** Dashboard ke charts, Timeline, Settings ka "Recompute analytics", aur PDF report. PDF ke page images agent dikhayega: padho, galat/ajeeb wording dhoondo.
> **Bahar ka kaam:** koi nahi.

```text
Read docs/RULES.md and docs/ui/SCREEN_MAP.md. Frontend-heavy phase; everything comes from the real endpoints, and every screen is compared with its Stitch reference (rule 15, screenshots in docs/ui/compare/).

DASHBOARD (per screenshot): stat cards (files, rows ingested/rejected, entities by type, connections, money volume, date span), Recharts: calls-per-day line with detected-spike markers and a toggle for the selected phone, transaction volume per day, top entities bar (switch metric: degree/calls/throughput), call heatmap (weekday x hour), degree distribution, entity-type donut; a community-coloured Cytoscape overview (capped, expand on click); latest alerts and top leads panels with links. Global date-range filter. Everything handles empty/partial data (e.g. no bank data -> money charts show 'No bank data uploaded').

TIMELINE: GET /cases/{id}/timeline?entity=&type=&from=&to=. Events built from data: document dates, aggregated same-day same-pair transactions, daily call-volume peaks/spikes (not every call), SIM activation dates, alerts, lead decisions. Cap 500 events with server-side filtering. UI: vertical/horizontal timeline per screenshot, type colours, filters, click -> provenance card, marker 'first alert vs first document'.

SETTINGS SCREEN (per case): every threshold/weight from defaults.yaml grouped (spike k/window/floor, fan-in/out K and W, pass-through R and H, reporting limit, lead weights and levels, matching strengths); editing shows defaults vs current, 'Reset to defaults', Save (audited) and 'Recompute analytics' with job progress. Changing settings re-runs analytics only, not ingestion.

SAVED VIEWS: save/reopen {entity, filters, hops, view} per user per case.

REPORT: POST /cases/{id}/report -> PDF via ReportLab, saved under UPLOAD_DIR/reports and registered with its own SHA-256. Sections: cover (case, date, officer, status), disclaimer ('analytical leads for review; not findings'), evidence list with file names + SHA-256 + data-quality summary, entity summary, master profiles with approvals, network summary with a graph image rendered SERVER-SIDE (networkx + matplotlib from the entity graph, capped nodes), money-trail table + figure for the selected account/filter, communication alerts, charts rendered with matplotlib, timeline, leads with score breakdown + officer decisions + notes + missing data, audit-log extract for this case + chain verification result, settings used (thresholds) so results are reproducible. Every generated item labelled 'Lead for review'. Page numbers and footer. Audited. Frontend: Reports screen with section checkboxes, generate, download, history.

TESTS: report is a valid PDF, contains the SHA-256 of an uploaded file, 'Lead for review', the thresholds used, and does NOT contain 'criminal', 'suspect' or 'mastermind' (grep the PDF text); dashboard endpoints match the underlying counts; empty case renders without errors; timeline orders events and puts the first alert before the first document for the ring scenario. Show PDF page images for my review.
```

**DONE WHEN:** Upload → analysis → dashboard charts, timeline, leads, aur ek click me PDF. Sab kuch tumhare upload kiye data se.

---

## PHASE 10 — Hardening, "no hardcode" audit, multi-dataset proof, docs

> ### TUMHARA KAAM — PHASE 10
> **Pehle:** ek **bilkul nayi file** ready rakho jo kabhi kisi test ya sample me nahi gayi (isse asli "no hardcode" saabit hota hai).
> **Beech me:** plan approve.
> **Baad me:** `python scripts/reset_db.py` se khaali app banao, `docs/UNSEEN_FILE_CHECKLIST.md` follow karke nayi file upload karo, `docs/DEMO_SCRIPT.md` rehearse karo. `docs/QA.md` ke 25 sawal-jawab padho. `docs/PPT_CONTENT.md` se slides banao.
> **Bahar ka kaam:** 2-minute backup demo video record, slides final, GitHub push, SIH rulebook ka prior-work rule padho.

```text
Read docs/RULES.md.

1. HARDCODE AUDIT: extend scripts/audit_hardcode.py (created in Phase 1) so that it fails (non-zero exit) if app/ or frontend/src/ contains: any generator-produced name/number from the committed sample scenarios, any 10-digit mobile-like literal, any account-like literal, any date literal in 2020-2030 outside comments in config/docs, any fixed rupee amount literal used as a threshold (must come from config), JSON files under frontend/src that look like mock data, or the words criminal/suspect/guilty/mastermind in UI strings. Run it and fix every finding.
2. MULTI-DATASET PROOF: a pytest that for >= 3 different seeds (at least 2 chosen at random at run time and printed) x scenarios (ring, chain, hub_spoke, two_rings, benign_heavy, cdr_only, bank_only, sparse_tiny, random_mix) x formats (clean, messy, statement, paysim where applicable) runs the full API flow (upload -> accept mapping -> ingest -> analytics -> leads) and checks the properties from ground_truth.json. Print a pass/fail matrix.
3. FIRST-RUN EXPERIENCE: fresh database -> the app shows empty states and a clear 'Upload data to begin' flow; no seeded cases or data. scripts/reset_db.py wipes SQLite, Neo4j and uploads.
4. OFFLINE: the app works with the network disabled (fonts bundled, no CDN, no external API calls). Show how you verified.
5. PERFORMANCE: with the generator's large size (~200k CDR, 50k bank rows): report ingest time, rebuild_graph time, p50/p95 of hop search (1-4), money trail and lead computation, peak memory. Add indexes/batching where needed. Confirm the UI stays readable via caps and the 'truncated' banner. Be honest about what degrades.
6. ERRORS: friendly messages for Neo4j down, bad file, mapping missing required field, expired token, job failure; the page never crashes.
7. SECURITY PASS: list string-formatted Cypher/SQL (only the validated hop integer allowed), upload path traversal and type spoofing, login rate-limit, CORS scope, secrets in git history. Report findings.
8. README.md: what it is, how to run (6 commands), how to bring your own data (mapping flow, supported formats and the known limitations: text PDFs only, English only, narration patterns are bank-specific, .xls unsupported), architecture diagram (mermaid), design decisions, 'what we did NOT build'.
9. docs/QA.md: the 25 hardest judge questions about THIS code (format handling, mapping errors, entity matching, scoring, hops, false merges, scale, legal, bias, LLM use, CCTNS), each answered in 2-3 honest sentences with the real file/function.
10. docs/DEMO_SCRIPT.md: 8-minute script that starts from an EMPTY app: create case -> upload the user's files -> confirm mapping -> watch the job -> dashboard -> graph -> money trail -> lead -> provenance -> report; plus a 2-minute version and a fallback plan if Docker/Neo4j fails.
11. docs/PPT_CONTENT.md: slide-by-slide text (problem, solution, architecture, features, what makes it different, demo flow, limitations, roadmap) written ONLY from what is actually built and verified in this repo (cite the file/feature), using the honest wording from docs/QA.md; flag every claim that is an estimate. Also docs/DIAGRAMS.md with mermaid sources for the architecture, pipeline and graph model.
12. docs/UNSEEN_FILE_CHECKLIST.md: a 5-minute checklist for me to run a file nobody has seen: which screens to open, what a correct result looks like, which wrong results to expect on a bank-specific narration, how to fix the mapping and how to add a narration pattern.
Show results for each item.
```

**DONE WHEN:** `audit_hardcode.py` pass; multi-dataset matrix green; fresh laptop pe khaali app se tumhari **nayi unseen** file upload karke poora flow chalta hai (`docs/UNSEEN_FILE_CHECKLIST.md`).

---

## Tumhe kya karna hai (agent ke bas ke bahar)

- **Setup:** Docker Desktop (RAM kam ho to Neo4j Desktop), Node 20+, Python 3.11+, Git, GitHub repo + push.
- **Inputs:** `inbox/` (Stitch ZIP, PDFs, playbook). Apni files: `data/user_samples/` (agent dekh sakta hai) ya `data/private/` (agent kabhi nahi kholta).
- **Real police data:** kisi cloud AI ko mat bhejo. App local chalta hai, par agent workspace padh sakta hai. Isliye sensitive files `data/private/` me aur sirf `probe_file.py` se check karo.
- **Seekhna:** Cypher Fundamentals (Phase 4 se pehle), FastAPI basics, aur har phase me ek service file line-by-line (ingestion, matching, lead_advisor). Judge wahi puchega.
- **Process:** har phase ke baad `git commit` + tag, tests khud chalao, Cypher Neo4j Browser me khud run karo, SELF-CHECK table padho.
- **Hackathon rulebook:** prior/pre-built work rule padho. Git history rakho.
- **PPT:** `docs/PPT_CONTENT.md` se banao. Section 63 BSA 2023 ("admissible" nahi, "supports integrity documentation"); "Hindi/English FIRs" tab tak nahi jab tak bana nahi; "3-5 din", "50+ stations" ko estimate likho; "better than Palantir" mat bolo.

---

## Brutal honesty

1. **Yeh version pehle se mushkil hai.** Generic ingestion + mapping + adaptive analytics + Stitch-fidelity UI me 4-6 hafte lagte hain agar tum test karo. Time kam ho to Phase 6 ko regex-only karo, Phase 9 me Settings/Saved views skip karo. Bachao: ingestion+mapping, graph, money trail, matching, Lead Advisor, audit/hash, report.
2. **"Kisi bhi file" ka matlab "kisi bhi file, mapping ke baad".** Auto-detection 70-90% sahi hoti hai, baaki tum dropdown se theek karte ho. Real CDR/bank formats telecom/bank ke hisaab se alag hote hain. Perfect auto-parse ka claim mat karo.
3. **Bank narration parsing sabse kamzor kadi hai.** UPI/NEFT/IMPS patterns kuch hi banks cover karenge. Unmatched narrations quality report me dikhengi. Yeh limitation honestly bolo.
4. **Scoring ka matlab sambhal ke bolo.** Lead score ek heuristic hai (percentile + rules), validated sirf synthetic data pe. "Accuracy" mat bolo. Real data me false leads aayenge, isi liye human review hai.
5. **Large data:** 200k rows ingest ho jayengi, par graph browser me 200-500 nodes se zyada nahi dikhana. Caps aur filters feature hain, bug nahi.
6. **SELF-CHECK independent nahi hai.** Agent apna hi kaam check karta hai. 3 pass + random seeds + audit galtiyan bahut kam karte hain, zero nahi. Isliye tum ek baar khud: nayi unseen file, `audit_hardcode.py`, aur ek random seed se `generate_data.py` ka output upload karke dekho.
7. **Agent ki aadat:** hardcode karke "done" bol dena, ya fail hote test ko dheela kar dena. Rule 14 aur audit isi liye hain. Tests ka diff dekhna mat bhoolo.
8. **Stitch UI ki limit:** screens static hoti hain. Graph ki dragging, modals, hover, loading/empty states Stitch me nahi hote; agent unhe tokens ke hisaab se assume karega (`docs/ui/ASSUMPTIONS.md`). Result "bahut kareeb", pixel-perfect nahi. Agent compare screenshots aur bachi hui differences ki list dega.
9. **Neo4j galtiyan:** range me parameter, path pe seedha `r.amount_paise`, bina LIMIT query, `case_id` bhoolna. Tum pakdo.
10. **"AI" kitna hai:** NER, fuzzy matching, graph centrality/communities, statistical anomaly detection, rule-based scoring. Koi trained model nahi. Honestly "AI-assisted, explainable" bolo.
11. **Antigravity quotas** khatam ho sakte hain. Chhote prompts (section B ka one-liner), phase-end commit.
12. **Demo risk:** Docker/Neo4j startup, memory. Backup 2-minute video aur reset-from-empty rehearsal zaroori.
13. **Legal:** real deployment ke liye authorised access, DPDP Act 2023 aur lawyer ki salah. Tum prototype ho. Yeh bolna maturity hai.

**Tumhara asli edge:** ek aisa system jo judge ki apni file lekar bhi chale (mapping dikhaye, graph banaye, decoy pe false lead na de, Undo merge aur audit verify live dikhaye). Wahi jeetata hai.
