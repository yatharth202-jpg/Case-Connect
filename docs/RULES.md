# Case Connect AI — Project Rules (Non-Negotiable)

These 17 rules govern all architecture, backend, frontend, database, analytics, and documentation work across all phases. Every phase finishes with the SELF-CHECK protocol verifying adherence to these rules.

1. **NO HARDCODING**: `app/` and `frontend/src/` must contain NO sample names, phone/account numbers, dates, amounts, or case-specific constants. Test data lives only in `tests/` and `scripts/generate_data.py`.
2. **NO MOCK DATA in production code paths**: If nothing is uploaded, screens show an empty state with an "Upload data to begin" call-to-action.
3. **Source of truth is SQLite**: Neo4j is a rebuildable index (`rebuild_graph(case_id)`). Approvals, undo actions, officer decisions, and staged rows are stored in SQLite and synced to Neo4j.
4. **Config-driven thresholds & weights**: All thresholds and scoring weights come from `backend/config/defaults.yaml`, overridable per case via `case_settings`. Every flag and score explanation states the actual threshold and actual values used.
5. **AI suggests, the human decides**: Never merge identities automatically. Merges are suggestions with confidence scores and require officer approval. Every merge is undoable. The ONLY exception is exact normalised-name equality inside one case (Phase 4): it is recorded as `method='name_equality'` and explicitly shown in the UI.
6. **No prejudicial terminology**: Never output the words "criminal", "suspect", "guilty", or "mastermind" in UI text, API responses, or reports. Use "lead for review", "high-priority entity", or "potential anomaly".
7. **Provenance on every graph node, relationship, and staged row**: Includes `case_id`, `source_file` (evidence ID), `source_ref` (row number or page), `method` (`'structured' | 'regex' | 'ner' | 'officer' | 'derived'`), `confidence` (0.0 to 1.0), and `approved_by` when applicable.
8. **Parametrised Cypher only**: Cypher queries must be parametrised. The ONLY exception is variable-length range (`*1..N`), where `N` is validated as an integer in `{1, 2, 3, 4}` and formatted safely into the query string. Conditions on relationships of a variable-length path use `ALL(r IN relationships(path) WHERE ...)`. Always specify `LIMIT` and use timeouts for graph traversals.
9. **Strict case scoping**: Everything is scoped to `case_id`. No query crosses cases except the explicit cross-case alert.
10. **Canonical units and formats**:
    - Money is stored as integer PAISE (`amount_paise`).
    - Dates are ISO-8601 strings.
    - Phone numbers are normalised to 10-digit mobile where valid (`valid_mobile=True`); other numbers are kept as-is with `valid_mobile=False`.
    - Account identifiers are normalised strings (uppercase, trimmed) and may be alphanumeric.
11. **Security**: Passwords hashed with bcrypt, access tokens are JWT (HS256), secrets read only from `.env`.
12. **Privacy**: Never open, print, or transmit anything under `data/private/` or user-uploaded evidence without explicit instruction. Files in `data/user_samples/` may be analysed to verify parser robustness, but their contents must never be copied into code, tests, or docs. Tests use generator output only.
13. **SELF-CHECK PROTOCOL** (Mandatory at the end of every phase and big task):
    - **PASS 1 - RUN**: Run all tests of this phase and earlier phases, `scripts/audit_hardcode.py`, and the frontend build/lint. Paste the real output.
    - **PASS 2 - REVIEW**: Re-read changed files against this `RULES.md` and the phase's DONE WHEN criteria. Fix any violations or doubts found.
    - **PASS 3 - HELD-OUT DATA**: Pick 2 random seeds, generate fresh data in scenarios/formats different from development, run end-to-end checks against `ground_truth.json`, and run on `data/user_samples/` if present.
    - Finish with a summary verification table: `check | result | what you fixed`.
14. **NO OVERFITTING**: Never write logic tailored only to synthetic generator names, headers, row counts, or column orders. Parsers, matchers, and scorers must work from detected structures and configuration. When a test fails, fix the code; never weaken the test.
15. **UI FIDELITY**: Build screens according to `docs/ui/SCREEN_MAP.md` and `docs/ui/DESIGN_TOKENS.md`. Layout, colours, typography, and container structures must align with the Stitch UI pack; example content shown in screenshots is never copied.
16. **HONEST REPORTING**: State clearly what is incomplete, approximate, or fragile (e.g. low NER recall on regional names, bank-specific narrations). Never disguise a failing test or omitted item.
17. **SMALL STEPS**: Split complex tasks, finish and verify each part, then continue. Never leave half-wired features that silently return fake data.
18. **PRODUCTION FORENSIC HYGIENE PROTOCOL**: Every screen, backend route, and configuration must strictly pass the 6 pillars defined in `docs/PRODUCTION_HYGIENE_CHECKLIST.md` (no harsh/rainbow gradients, no generic icon/emoji slop, no liquid glass/blur overload, no placeholder copy, no dead links, proper mobile/projector responsiveness, custom 404, strict CORS, BOLA/IDOR defense, parametrised queries, bcrypt passwords, and validated file uploads).
