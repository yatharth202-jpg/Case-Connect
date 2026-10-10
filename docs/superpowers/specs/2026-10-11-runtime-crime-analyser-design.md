# Runtime Dynamic Crime Analyser & Suspect Attribution Design

## Goal
Replace all hardcoded/pre-seeded cases and static analysis views with a pure runtime file analysis engine. When a user uploads ANY investigative file (FIR/Police Complaint PDF, CDR/Bank CSV/Excel, ANPR vehicle logs, images/scans), the system autonomously parses the file, builds an interactive entity relationship graph, identifies the prime criminal/suspect with threat scoring, and visualizes the investigation in a high-end Stitch-inspired tactical UI with minimal text and maximum visual impact.

## Architecture & Data Flow
1. **Universal File Ingestion Endpoint**:
   - Accepts `.pdf`, `.docx`, `.txt`, `.csv`, `.xlsx`, `.png`, `.jpg`.
   - Generates statutory SHA-256 integrity hash.
   - Extracts raw content via `pdfplumber`/`pypdfium2`/`RapidOCR` (text/scans) or `pandas`/`csv` (tabular).
2. **Autonomous Extraction & Criminal Attribution Pipeline**:
   - Entities: Persons, Phone numbers, Bank accounts, Vehicles, FIR sections, Locations, Organizations.
   - Relationships: `TRANSFERRED_TO`, `CALLED`, `USES_VEHICLE`, `OPERATES_FROM`, `ACCOMPLICE_OF`, `OWNS_ACCOUNT`.
   - Dual-engine: Local NLP (spaCy `en_core_web_sm` + Indian legal title heuristics + regex) AND Gemini API (if `GEMINI_API_KEY` present in `.env`).
   - Crime Scoring & Prime Suspect Attribution:
     - Calculates degree centrality, money flow volume, call frequency, and crime role heuristics (e.g. accused, kingpin, handler, mastermind).
     - Ranks entities to determine the **Potential Criminal / Prime Suspect**, risk score (0-100%), and forensic rationale.
3. **Frontend Presentation (Stitch Reference Aesthetic)**:
   - Deep tactical dark mode (`#050914`, `#070d1d`, `#0b1329`, electric blue `#2563eb`, neon crimson `#ef4444`).
   - Sticky top bar with instant file dropzone & status indicator.
   - Prime Suspect Hero Dossier card with radial threat score, visual tags, and key evidence links.
   - Large interactive Cytoscape network graph (animated nodes, physics drag, zoom, glow effects).
   - Animated visual breakdown: Money flow bar, Communication volume dial, Entity distribution badges.
   - Zero hardcoded data: Empty state cleanly prompts file drop, and loading state shows animated forensic pipeline stages.

## Visual Design System
- **Background**: `#050914` with grid overlay
- **Cards**: `#091024` with border `#1a2948` and subtle glow
- **Accents**: Crimson `#f43f5e` (Prime Suspect), Electric Blue `#2563eb` (Entities), Cyan `#06b6d4` (Phones), Emerald `#10b981` (Accounts), Amber `#f59e0b` (Vehicles)
- **Typography**: Clean monospace for forensics/IDs, Plus Jakarta Sans / Inter for tactical UI.
