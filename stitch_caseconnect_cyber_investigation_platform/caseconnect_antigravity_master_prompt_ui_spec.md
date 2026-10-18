# CaseConnect — Master Antigravity Execution Prompt
*Copy-paste this directly into Antigravity / Cursor / Claude Code to build the exact single-page 3D cyber forensic dossier.*

---

## 🎯 Project Overview
- **Project**: CaseConnect (Cybercrime Investigation Platform by Team UNITx)
- **Stack**: React 18 (Vite) + Tailwind CSS + Three.js (`@react-three/fiber` & `@react-three/drei` or vanilla Three.js in a canvas) + Lucide Icons + GSAP / Lenis
- **Core Visual Philosophy**: Anti-AI aesthetic. ZERO gaudy neon cyan (`#00F0FF`), zero purple gradients, zero rainbow glow. Restrained, high-end editorial defense intelligence dossier. All foreground sections sit in authentic frosted glass (`.glass`) floating above a fixed 3D cyber dotted India map.

---

## 🎨 Theme & Color Tokens (`tailwind.config.js` & CSS Variables)
```css
:root {
  --ink: #07090D;                   /* Deepest page background */
  --ink-2: #0D1117;                 /* Section alternate surface */
  --glass: rgba(13, 17, 23, 0.55);  /* Glass panel background */
  --glass-line: rgba(255, 255, 255, 0.08); /* Hairline frosted border */
  --text: #ECE8DF;                  /* Editorial warm white */
  --muted: #8B93A1;                 /* Muted metadata gray */
  --accent: #F2A33A;                /* Saffron / Amber (single accent) */
  --data: #3FB6A8;                  /* Surgical analytical teal */
  --alert: #E5484D;                 /* Strict risk / alert red */
}

/* Glass Utility */
.glass {
  background: var(--glass);
  border: 1px solid var(--glass-line);
  border-radius: 20px;
  backdrop-filter: blur(20px) saturate(130%);
  -webkit-backdrop-filter: blur(20px) saturate(130%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.06) inset, 0 20px 50px -15px rgba(0, 0, 0, 0.7);
}
```

---

## 🔤 Typography Specification
- **Display Headings & Primary Big Numbers**: `Instrument Serif` or `Newsreader` (serif font, sizes 44–56px, hero numbers 80–120px). Gives a prestigious, custom-designed editorial look.
- **UI, Labels & Navigation**: `Inter Tight` or `Inter` (sans-serif, clean, 11–14px, uppercase tracking for labels).
- **Forensic Data, Hashes, Amounts, Coordinates**: `JetBrains Mono` (monospace).
- **Copy Rule**: Section title max 3–4 words. Subtitle max 12 words. No marketing fluff ("AI-powered", "revolutionary", etc.).

---

## 🗺️ Fixed Background: 3D Cyber India Map
1. **Container**: `position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 0; pointer-events: none;`.
2. **Foreground Readability**: Place a subtle radial vignette / gradient mask (`pointer-events: none`) between the map and the UI panels (`background: radial-gradient(circle at center, rgba(7,9,13,0.4) 0%, rgba(7,9,13,0.85) 100%)`) so foreground text and numbers remain 100% crisp and readable.
3. **Geometry**:
   - Dotted point-cloud representing official Survey of India boundary (approx 6,000–9,000 sampling points inside official bounds).
   - Point colors: dim cyber slate (`#1e3a5f`), surgical teal (`#3fb6a8`), and saffron amber (`#f2a33a`).
   - Luminous glowing rings on critical metropolitan cyber hubs: **Delhi**, **Mumbai**, **Surat**, **Kolkata**, and **Bangalore** with pulsing animation.
   - Faint coordinate wireframe grid lines on the ground plane.
4. **Scroll Dynamics**:
   - Listen to `window.scrollY` / Lenis scroll progress.
   - As user scrolls from top to bottom:
     - Map rotates gently in 3D perspective (`rotation.x` tilts from `0.2` to `0.65`, `rotation.y` pans `-0.15` to `0.35`).
     - Point lights dynamically shift brightness and focus between North, West, and Central nodes.
     - Never obstructs UI text; stays atmospheric and deep in the background.

---

## 📑 Page Sections Structure (Single Smooth Scroll)

### 1. Sticky Frosted Header
- Left: **CaseConnect** in serif font (clicking triggers smooth reset to top / home).
- Center: Nav pills with smooth-scroll anchors (`#intake`, `#suspect`, `#trail`, `#network`, `#forensics`, `#evidence`).
- Right: Saved Cases pill badge (`Saved Cases (4)`), Active Officer badge (`Inspector V. Sen | CYBER CELL`), and secure air-gapped status.

### 2. Step 01 · Intake & Ingestion (`#intake`)
- Serif Heading: *"Drop the case files."*
- Subtitle: *"FIR reports, call records (CDR), bank statements, and IP logs."*
- Glass drop-zone with dashed border and drag-and-drop icon.
- Auto-detect file chips: `FIR_408_CyberCrime.pdf [FIR]`, `Hawala_AxisBank_Stat.csv [BANK]`, `CDR_Dump_Delhi_Noida.xlsx [CDR]`.
- Input fields: Case Title, Case Reference Number.
- Primary CTA: Amber button **"Analyse Case →"** + *"Try sample case: Hawala syndicate dump (₹1.8 Cr)"* seed link.

### 3. Section 01 · Priority Threat (`#suspect`)
- Serif Heading: *"Lead suspect identified."*
- Left: Monochrome silhouette avatar placeholder with `RV` initials (strictly NO fake AI faces), `Attach official photo` action, UID tag.
- Center: Large serif name **Rakesh Verma**, Hawala orchestrator badges, key stats chips (3 devices, 5 accounts, 2 static IPs, ₹ 1.84 Cr routed, 41-call spike on 14-Oct). Expandable *"Why flagged for arrest ▾"*.
- Right: Large dynamic **87%** confidence ring in red/amber with cross-corroboration vectors count.
- Below: 4 secondary entity cards in a row (Vicky Sharma - 74%, Anil Kulkarni - 68%, Farooq Malik - 61%, Meera Desai - 42%) that swap the main dossier when clicked.

### 4. Section 02 · Geo-Financial Flow Centerpiece (`#trail`)
- Serif Heading: *"Follow the money and calls across India."*
- Pinned / visual 3D arc container:
  - Ballistic arcs drawn between Mumbai, Surat, Delhi, and Kolkata.
  - Teal thin arcs = VoIP/GSM Call bursts.
  - Amber thick arcs = Hawala RTGS layering flows.
  - Glowing red loop alert: *"Layering Detected: ₹42,00,000 looped back to Delhi through shell garment exporter."*
- Right telemetry side-card: Total volume (₹ 1,84,50,000), 1,842 corroborated calls, 14 cell towers.

### 5. Section 03 · Linkage Topology Graph (`#network`)
- Serif Heading: *"Intelligence Network Graph."*
- Filter pills: All Entities (18), Persons (5), Mule Accounts (7), Phones (4), IPs (2).
- Search bar: *"Search phone, name, IP, bank account..."* with instant node focus.
- Interactive graph canvas showing interconnected nodes (Kingpin red, Bridges amber, mules/IPs teal/grey).
- Summary bar below: Visual chain `Rakesh V. → called (14×) → Vicky S. (Surat) → transferred ₹42L via IMPS → A/C **9014 → Delhi Return Loop`.

### 6. Section 04 · Quantitative Forensics (`#forensics`)
- Serif Heading: *"Corroborated analytical metrics."*
- 6 clean glass metric cards (strictly teal/amber/red palette):
  1. *Calls per day* (sparkline with Oct-14 peak spike marker).
  2. *Daily Volume* (histogram of layering spikes).
  3. *Vector Distribution* (donut chart: CDR 58%, Bank 28%, IP 14%).
  4. *Density Matrix* (curfew hour × day heat grid with night surge indicator).
  5. *Centrality Rank* (horizontal bars showing Degree influence).
  6. *Sub-clusters* (Louvain modularity partition).

### 7. Section 05 · Chain of Custody Ledger (`#evidence`)
- Serif Heading: *"Verified forensic evidence ledger."*
- Filter tabs: `Timeline`, `Phone (CDR)`, `Entities`.
- Filter search input for hash or keyword.
- Table with columns: Timestamp (IST), Artifact Type badge (`BANK_TXN`, `CDR_CALL`, `IP_SESSION`, `FIR_COMPLAINT`), Observation / Finding, Source File, SHA-256 Integrity Hash with verified tick, Action button (*Preview*).

### 8. Section 06 · Executive UNITx Footer
- Large serif typography: **UNITx**.
- Subline: *"Built by team UNITx for Smart India Hackathon. Air-gapped forensic intelligence."*
- Badges: `AI-Assisted Graphing`, `SIH-2024`, `NCRP Core Interop`, `Strict Zero-Hallucination Evidence Contract`.

### 9. Persistent Floating AI Copilot Drawer
- Bottom-right amber-accented button: *"AI Case Copilot // UNITx"*.
- Opens a 420px slide-over glass drawer.
- Strictly answers queries based on case files with verifiable evidence IDs (e.g. *"Explain Rakesh's money trail"*, *"List proof for SIM box bypass"*).
