# Antigravity Production Prompt: CaseConnect UNIT-X (Frontend & Backend Integration)

Use this complete architectural prompt in **Antigravity**, **Cursor Composer**, or **v0** to generate or integrate the production full-stack frontend connected directly to your existing backend API & WebSocket server.

---

```markdown
# CASECONNECT UNIT-X // PRODUCTION FULL-STACK & BACKEND INTEGRATION SPECIFICATION

## 1. PROJECT OVERVIEW & GOALS
Build a production-grade, air-gapped Indian Law Enforcement Cyber Crime & Intelligence Cell interface ("CaseConnect UNIT-X").
The frontend consists of two core views:
1. `/intake` — Case Intake & Multi-Source File Ingestion Terminal (FIRs, CDR/IPDR CSVs, Bank Statements, IMEI dumps).
2. `/graph` — Scrollable Multi-Module Real-Time Graph Explorer & Forensic Intelligence Webpage with live Cytoscape/Visx canvas, AML Smurfing Layering pipeline, Telecom Geofence radar, and Section 63 BSA 2023 tamper-evident legal ledger.

Connect all user interactions and streaming widgets to the live backend REST & WebSocket endpoints described below.

---

## 2. DESIGN SYSTEM & VISUAL TOKENS
- **Aesthetic**: Minimalist Cyberpunk / Law Enforcement Tactical Cyber Forensics (Palantir Gotham + Bloomberg Terminal fidelity).
- **Background**: Deep void obsidian `#05070c` / `#0a0e17` with subtle technical 1px hairlines (`#181b25`, `#26334a`).
- **Accent Palette**:
  - Primary LEA Verified Green: `#05df72` (Glows: `rgba(5, 223, 114, 0.15)`)
  - Warning / Layering Amber: `#f59e0b`
  - Critical Alert / Primary Target Red: `#ef4444`
  - Signal / Telemetry Cyan: `#00e5ff`
- **Typography**:
  - Headings & UI: `Inter` or `Geist Sans`
  - Telemetry, Docket IDs, Timestamps & Hashes: `JetBrains Mono` or `Space Grotesk`
- **Spacing & Layout**: Generous padding (`gap-6` to `gap-8`), spacious cards with glassmorphism (`backdrop-blur-md bg-[#0c101a]/85 border border-[#1e2738]`), corner brackets (`[+]`, `[-]`), and no cluttered borders.

---

## 3. BACKEND API CONTRACT & REST SPECIFICATION

Ensure the frontend service layer (`lib/api.ts` or `services/caseService.ts`) implements the following endpoints:

### A. Case Intake & Ingestion (`/api/v1/cases`)
1. **POST `/api/v1/cases/intake`**
   - **Form Data**:
     - `case_title`: string (Mandatory, e.g. "Hawala Syndicate: North Corridor Ingestion")
     - `case_ref_number`: string (Optional, e.g. "CR-2026-DEL-0412")
     - `files`: File[] (MIME types: `text/csv`, `application/pdf`, `application/zip`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
     - `tags`: string[] (e.g. `["AML", "CDR_TRIANGULATION", "HAWALA"]`)
   - **Response** (`201 Created`):
     ```json
     {
       "status": "success",
       "docket_id": "I4C-CYBER-DEL-0412",
       "ingestion_job_id": "job_998124fa",
       "entities_detected": 28,
       "total_volume_inr": 18430000,
       "redirect_url": "/graph?docket=I4C-CYBER-DEL-0412"
     }
     ```

2. **GET `/api/v1/cases/sample-hawala`**
   - Pre-loads sample case data when the user clicks "Try sample case: Hawala syndicate dump (₹1.84 Cr)". Returns pre-analyzed dataset and redirects immediately to `/graph`.

---

### B. Graph Topology & Analytics (`/api/v1/cases/:docketId`)
1. **GET `/api/v1/cases/:docketId/topology`**
   - Returns node graph data:
     ```json
     {
       "nodes": [
         {
           "id": "node_vikram_01",
           "type": "TARGET_PRIMARY",
           "name": "Vikram S.",
           "role": "Broker / Layering Lead",
           "age": 38,
           "pan": "*****9121K",
           "layered_flow": "₹1,28,50,000",
           "intercept_pings": 412,
           "flight_risk": "HIGH",
           "certainty": "94.8%",
           "coordinates": { "x": 104.2, "y": 88.6 }
         },
         {
           "id": "node_alpha_mca",
           "type": "SHELL_COMPANY",
           "name": "Alpha Logistics Pvt Ltd",
           "hold_balance": "₹98,00,000",
           "pan": "AAACA1294F"
         },
         {
           "id": "node_tariq_mule",
           "type": "MULE_RING",
           "name": "Tariq Mir & Mule Rings",
           "smurfed_sum": "₹54,20,000",
           "accounts_count": 14
         },
         {
           "id": "node_cell_tower",
           "type": "CELL_TOWER",
           "name": "DEL-S-04 Hauz Khas",
           "pings": 412,
           "azimuth": 140
         },
         {
           "id": "node_otc_crypto",
           "type": "CRYPTO_GATEWAY",
           "name": "OTC Telegram Gateway #4",
           "wallet": "Tkr8X...qn3L",
           "volume_usdt": "$188,400"
         }
       ],
       "edges": [
         { "source": "node_vikram_01", "target": "node_alpha_mca", "amount": 9800000, "label": "₹98.0L Hawala Flow", "animated": true },
         { "source": "node_alpha_mca", "target": "node_tariq_mule", "amount": 5420000, "label": "UPI Smurfing", "animated": true },
         { "source": "node_tariq_mule", "target": "node_otc_crypto", "amount": 3420000, "label": "TRC-20 USDT Bridge", "animated": true },
         { "source": "node_vikram_01", "target": "node_cell_tower", "amount": 0, "label": "412 Call Intercepts", "style": "dashed" }
       ]
     }
     ```

2. **GET `/api/v1/cases/:docketId/financial-ledger`**
   - Returns the Smurfing Layering stages (1 to 4) + table transactions with pagination and high-velocity filter.

3. **GET `/api/v1/cases/:docketId/telemetry`**
   - Returns telecom timeline events, burner IMSI swaps, and 200m micro-geofence radar coordinates (`{ targetLat, targetLng, atmKioskLat, atmKioskLng, directDistanceMeters: 184 }`).

4. **GET `/api/v1/cases/:docketId/bsa-chain-of-custody`**
   - Returns cryptographic records:
     - `evidence_id`, `extraction_source`, `sha256_hash`, `operator_cert_signature`, `admissibility_status`.

5. **POST `/api/v1/cases/:docketId/actions/lookout-circular`**
   - Dispatches emergency alert to Bureau of Immigration / Seaports / Land Checkposts. Returns confirmation timestamp & LOC reference ID.

6. **POST `/api/v1/cases/:docketId/actions/export-dossier`**
   - Generates and streams digitally signed PDF/SHA-256 compliant Section 63 BSA legal compilation package.

---

## 4. WEBSOCKET REAL-TIME STREAMING CONTRACT

Connect client to `wss://api.caseconnect.gov.in/v1/cases/:docketId/stream` or `ws://localhost:8000/ws/docket-0412`.

### WebSocket Events (Incoming):
```typescript
type IngestionEvent = 
  | {
      type: "LIVE_INGESTION_TICKER";
      payload: {
        id: string;
        title: string;
        description: string;
        amount: string;
        badge: string;
        badgeType: "smurfing" | "aml_alert" | "triangulated";
        timestamp: string;
      };
    }
  | {
      type: "TOPOLOGY_EDGE_PULSE";
      payload: {
        edgeId: string;
        flowValue: number;
        currency: "INR" | "USDT";
      };
    }
  | {
      type: "CO_LOCATION_ALERT";
      payload: {
        burnerImei: string;
        distanceMeters: number;
        locationName: string;
        timestamp: string;
      };
    }
  | {
      type: "STREAM_LATENCY";
      payload: {
        latencyMs: number;
      };
    };
```

### WebSocket Client Implementation:
- Handle automatic reconnection with exponential backoff.
- Feed incoming transactions directly into Zustand / Redux state:
  `addLiveTransaction(event.payload)` triggers animated toast/ticker on the left stream drawer.
- Pulse edge signals across canvas lines using requestAnimationFrame.

---

## 5. COMPLETE COMPONENT ARCHITECTURE (NEXT.JS 14 / REACT)

```
src/
├── app/
│   ├── intake/
│   │   └── page.tsx               # Screen 1: File dropzone, docket input, sample case loader
│   ├── graph/
│   │   └── page.tsx               # Screen 2: Scrollable multi-module intelligence webpage
│   └── layout.tsx                 # Root layout with Geist & Space Grotesk fonts
├── components/
│   ├── layout/
│   │   ├── PersistentHeader.tsx   # Brand [CASECONNECT // UNIT-X], tabs, docket status
│   │   └── ComplianceFooter.tsx   # DPDP Act 2023 & Sec 63 BSA audit strip
│   ├── intake/
│   │   ├── DragDropZone.tsx       # File dropzone with category chips (CDR, FIR, Bank)
│   │   └── CaseForm.tsx           # Docket inputs and primary CTA button
│   ├── graph/
│   │   ├── Module01Topology.tsx   # Viewport-height graph canvas + floating drawers
│   │   │   ├── CytoscapeGraph.tsx # Canvas 2D / Cytoscape force-directed engine
│   │   │   ├── LeftStreamPanel.tsx# Live Ingestion Stream & Risk Gauges
│   │   │   └── RightDossier.tsx   # Suspect Dossier, BSA admissibility & AI Copilot
│   │   ├── Module02Financial.tsx  # 4-stage Smurfing flow cards + Correlated Ledger Table
│   │   ├── Module03Telecom.tsx    # Chronological Tower handover timeline + 200m Radar
│   │   └── Module04Compliance.tsx # Sec 63 BSA SHA-256 table + Action CTAs
│   └── ui/
│       ├── CrosshairCard.tsx      # Reusable card with corner [+] brackets
│       └── MetricPill.tsx         # Monospace status badges
├── hooks/
│   ├── useCaseSocket.ts           # WebSocket subscription hook
│   └── useTopologyData.ts         # SWR / TanStack Query data fetcher
├── store/
│   └── useCaseStore.ts            # Active suspect, zoom state, filter states
└── services/
    └── api.ts                     # Axios / Fetch client matching backend endpoints
```

---

## 6. INSTRUCTIONS FOR LLM / ANTIGRAVITY ENGINE
1. Scaffold clean, modular TypeScript files conforming to the folder structure above.
2. Ensure full accessibility, zero layout shifts, and high visual contrast matching the verified Tactical Dark palette (`#05070c`, `#05df72`, `#f59e0b`, `#ef4444`).
3. Connect all dummy mock data to fallback gracefully when backend environment variables (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`) are omitted, allowing smooth local testing and immediate production hookup when plugged into real microservices.
```
