# Runtime Dynamic Crime Analyser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a 100% dynamic, runtime file analysis experience where any uploaded file is parsed into an interactive animated graph, prime suspect attribution, and tactical visual cards with zero hardcoded data.

**Architecture:** A streamlined backend analysis endpoint + robust local/Gemini entity extraction pipeline feeding into a high-end Stitch-inspired React frontend featuring interactive Cytoscape network graph, suspect threat dial, and animated forensic indicators.

**Tech Stack:** FastAPI, SQLite, NetworkX, spaCy (`en_core_web_sm`), RapidOCR, Google Gemini (optional enhancement), React, Vite, TailwindCSS, Cytoscape.js.

**Spec:** `docs/superpowers/specs/2026-10-11-runtime-crime-analyser-design.md`

## Global Constraints
- Zero hardcoded mock cases or static suspect names in the runtime analysis flow.
- Support both offline (spaCy + regex) and online (Gemini API) operation seamlessly.
- Visual-first design: large interactive graph, glowing suspect indicators, minimal text clutter.
- Responsive dark-mode layout matching Stitch design parameters.

---

### Task 1: Autonomous File Ingestion & Criminal Attribution API
**Files:**
- Modify: `backend/app/services/ai/router.py` or `backend/app/services/analytics/router.py`
- Modify: `backend/app/services/extraction/pipeline.py`
- Modify: `backend/app/services/extraction/ner.py`

**Interfaces:**
- Input: Uploaded multipart file or raw text input
- Output: Dynamic analysis payload:
  `{ file_info, summary, entities, relationships, prime_suspect, network_graph, metrics }`

- [ ] **Step 1: Enhance entity & relationship extraction** with robust Indian legal terms, accused/mastermind identification, phone, account, vehicle, and cash patterns.
- [ ] **Step 2: Add direct `/analytics/analyse-file` endpoint** that takes an uploaded file or text, computes SHA-256, extracts entities & relationships, runs NetworkX centrality/flow, identifies the prime suspect, and returns the full investigation model in one shot.
- [ ] **Step 3: Test endpoint** with sample test file and verify structured JSON output.

---

### Task 2: High-End Stitch Tactical UI Redesign
**Files:**
- Modify: `frontend/src/pages/QuickCrimeAnalyser.jsx`
- Create/Modify: `frontend/src/components/DynamicSuspectCard.jsx`
- Create/Modify: `frontend/src/components/DynamicInvestigationGraph.jsx`
- Modify: `frontend/src/api/client.js`

**Interfaces:**
- Ingests: `/analytics/analyse-file` API output
- Produces: High-end interactive UI with animated graph, threat meter, entity pills, and prime suspect card.

- [ ] **Step 1: Connect API client** with `/analytics/analyse-file` and direct upload handler.
- [ ] **Step 2: Build `DynamicSuspectCard.jsx`** with glowing crimson accent, threat risk percentage meter, criminal role badge, evidence citations, and why they are the potential criminal.
- [ ] **Step 3: Build `DynamicInvestigationGraph.jsx`** with Cytoscape.js, customized tactical node colors, animated edge flows, interactive zoom/drag, and node inspection.
- [ ] **Step 4: Update `QuickCrimeAnalyser.jsx`** with Stitch layout: clean hero dropzone, zero hardcoded states, animated processing sequence, and instant transition to the interactive dashboard upon file upload.

---

### Task 3: Verification & Integration Testing
- [ ] **Step 1: Test with PDF / text files** containing criminal cases, FIRs, and financial trails.
- [ ] **Step 2: Verify responsive behavior** and error handling for empty/corrupted files.
- [ ] **Step 3: Verify Gemini API key integration** seamlessly works when key is supplied in `.env`.
