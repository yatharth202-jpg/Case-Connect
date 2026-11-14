# CaseConnect UNIT-X — Production Antigravity / Full-Stack Implementation Prompts

Use these comprehensive system architecture and frontend/backend prompts in Antigravity, Cursor, v0, or custom LLM code pipelines to build the exact two screens.

---

## 📄 PROMPT 1: Case Intake & File Ingestion Screen (`/intake`)

```markdown
### SYSTEM ARCHITECTURE & UI SPECIFICATION: CaseConnect UNIT-X Intake

**Role**: You are a Principal Full-Stack Engineer and Tactical UI/UX Specialist building an air-gapped Indian Law Enforcement (Cyber Crime & Intelligence Cell) ingestion terminal.

#### 1. Tech Stack & Styling:
- **Framework**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, Lucide-React / Phosphor Icons.
- **Theme & Colors**:
  - Background: Deep Obsidian / Void Slate (`#06080e`, `#0a0e17`).
  - Terminal Borders & Hairlines: Technical 1px borders (`#1a2233`, `#26334a`) with monospace crosshair brackets (`[+]`, `[-]`).
  - Accents: Law Enforcement Verified Green (`#05df72`), Cyber Amber (`#f59e0b`), Crimson Critical (`#ef4444`).
  - Fonts: Inter or Geist for sans headings, JetBrains Mono or Space Grotesk for technical telemetry, docket IDs, and hashes.

#### 2. Persistent Navigation Bar (Header):
- **Brand**: `[CASECONNECT // UNIT-X]` with pulsing green node status `AIR-GAPPED CLASSIFIED`.
- **Navigation Tabs**: `INTAKE` (Active state with glowing underline/pill), `LEAD TRIAGE`, `AUDIT TRAIL`, `GRAPH EXPLORER`, `CORRELATION ANALYTICS`, `EVIDENCE VAULT`.
- **Top Actions**: Docket reference tracker `#I4C-CYBER-DEL-0412`, Saved Cases counter (`14`), Secure Terminal indicator.

#### 3. Core Hero / Ingestion Dropzone:
- Minimalist background featuring subtle connected cyber topology nodes / subtle radar grid line vector (no generic map outlines).
- **Badge**: Monospace pill `[STAGE 01 // MULTI-SOURCE INGESTION]`.
- **Headline**: "Drop the case files." (Clean, high-contrast white sans-serif).
- **Subtext**: "FIR reports, call detail records (CDR/IPDR), banking ledgers, and device IMEI telemetry."
- **Dropzone Area**:
  - Drag-and-drop boundary with dashed border (`border-emerald-500/30`), corner crosshairs, and file category chips: `CDR / IPDR (.csv, .xlsx)`, `Scanned FIR (.pdf)`, `Bank Statements (.csv)`, `Dump (.zip)`. Max size cap: 200MB.
- **Input Fields**:
  - Case Title / Docket Name: Input field with `[MANDATORY]` badge (e.g. "Hawala Syndicate: North Corridor Ingestion").
  - Case Reference Number (Optional): Input field with Police CCMS / CCTNS hint (e.g. "# CR-2026-DEL-0412").
- **CTA Actions**:
  - Sample case quick-loader pill: "Try sample case: Hawala syndicate dump (₹1.84 Cr)".
  - Primary button: `INITIATE CASE ANALYSIS →` with tactical green border, high contrast, routing to `/graph`.

#### 4. Compliance & Authority Footer:
- Cryptographic verification ledger: `AIR-GAPPED LEDGER • SHA-256 GENESIS ANCHORED • LEO AUTHORIZED INGESTION`.
- Legal Compliance Strip: `UNIT-X FORENSIC ENGINE • CYBER CRIME & INTELLIGENCE CELL | SECURE | TRUSTED | LAW ENFORCEMENT INDIA | DPDP ACT 2023 COMPLIANT | SECTION 63 BSA 2023 COMPLIANT AUDIT LEDGER`.
- Status telemetry: `UNITX CASE ASSISTANT (ONLINE) • UTC+5:30 IST`.
```

---

## 📄 PROMPT 2: Real-Time Graph Explorer & Scrollable Analytics Webpage (`/graph`)

```markdown
### SYSTEM ARCHITECTURE & UI SPECIFICATION: CaseConnect UNIT-X Forensic Dashboard & Scrollable Analytics

**Role**: Build a high-performance, scrollable real-time network intelligence and forensic analysis webpage for cyber crime investigators analyzing financial hawala rings and call records.

#### 1. Page Layout & Scroll Flow:
- **Global Header**: Persistent tactical navigation bar with Case Title: "Hawala Syndicate: North Corridor Intercept", Key Metrics Banner:
  `Vol: ₹1.84 Cr | CDR: 4,812 | Entities: 28 Linked | Targets: 3 Primary | ML Conf: 94.8% | WS Stream: 14ms`.
- **SECTION 1: Interactive Real-Time Topology Canvas (Viewport Height)**:
  - Central Cytoscape / Visx / Canvas 2D force-directed graph node engine.
  - Nodes: Tier-1 Target (Vikram S. - red pulse), Mule Banks (Alpha Logistics, Tariq Mir - green/amber), Cell Tower Pings (DEL-S-04 Hauz Khas - cyan), Telegram OTC Gateway (amber).
  - Overlay tools: Physics Toggle, Heatmap Mode, Geofence Radar, Zoom & Pan controls.
  - Floating Left Drawer: Ingested Evidence stream selector pills (`CDR 2.4k`, `Bank 18`, `FIR 4`, `IMEI 31`), Syndicate Risk Score gauges (`Hawala Certainty: 94.8%`, `Flight Risk: HIGH`), Live Transaction Ingestion ticker.
  - Floating Right Drawer: Suspect Dossier card, Section 63 Bharatiya Sakshya Adhiniyam (BSA) 2023 cryptographic chain-of-custody hash (`SHA-256`), AI Copilot micro-geofence anomaly insight, and Quick Action buttons: `ISSUE BSA LOOKOUT CIRCULAR` & `GENERATE LEGAL DOSSIER (PDF)`.

- **SECTION 2 (Scroll down): Financial Flow & Mule Layering Breakdown**:
  - Waterfall Sankey / Flow diagram showing progression: Unexplained Deposits → Shell Company (Alpha Logistics ₹98.0L) → Smurfed UPI Batches (4x ₹77,500) → Dubai OTC Gateway.
  - Interactive table with filters for suspicious volume thresholds, KYC match flags, and PAN verification status.

- **SECTION 3 (Scroll down): Telecom & Cell Tower Geofence Triangulation**:
  - Timeline scrubber of burner phone handovers, IMSI/IMEI switching clusters, tower ping correlation table (Hauz Khas, Saket, Aerocity).
  - Geofence co-location radar showing target burner within 200m of ATM withdrawal within 45-minute window.

- **SECTION 4 (Scroll down): Cryptographic Chain of Custody & BSA Sec 63 Legal Audit Log**:
  - Full immutable ledger with SHA-256 block hashes, telecom operator certificate verification status (Airtel/Jio LEA feed signed), officer badge authorization stamp.
  - Exportable 65B/Sec 63 Indian Evidence Act forensic certificate generator.

#### 2. Backend WebSocket Integration Specs:
- Connect to `wss://api.caseconnect.gov.in/v1/cases/docket-0412/stream`.
- Handle events: `NEW_INGESTION_CHUNK`, `NODE_EXPAND`, `EDGE_TRANSACTION`, `RISK_ALERT`.
- Keep memory layout immutable using Immer / Zustand for 60fps graph physics updates.
```
