# Case Connect AI — UI Pack Inventory & Gap Analysis

This inventory documents all Stitch UI screens provided in the inbox pack (`docs/ui/pack/stitch_screens/`), their inferred routes, component responsibilities, and visual consistency proposals for required screens not having a standalone static Stitch export.

---

## 1. Inventory of Provided Stitch Screens

| # | Directory | Inferred Screen Name | Target Route | Code File | Confidence | Role & Notes |
|---|---|---|---|---|:---:|---|
| 1 | `login_screen` | Login Authentication | `/login` | `code.html` (14.9 KB) | 1.0 | Split 50/50 hero branding and frosted glass card login. Dark tactical aesthetic (`#030712`). |
| 2 | `role_selection_screen` | Role Selection Wizard | `/select-role` | `code.html` (19.8 KB) | 1.0 | 3-step progress wizard with role cards: Investigator, Supervisor, Admin. |
| 3 | `select_your_role_case_connect_ai` | Alternate Role Selection | `/onboarding/role` | `code.html` (19.8 KB) | 1.0 | Variant role authorization screen. |
| 4 | `dashboard_screen` | Master Command Dashboard | `/dashboard` | `code.html` (46.8 KB) | 1.0 | Top KPIs, dark SVG investigation map, recent cases, system status, and AI insights feed. |
| 5 | `dashboard_case_connect_ai` | Dashboard Variant | `/dashboard/alt` | `code.html` (46.8 KB) | 0.95 | Layout variant of Master Command Center. |
| 6 | `cases_screen` | Case Management Hub | `/cases` | `code.html` (28.7 KB) | 1.0 | Search, filter by priority, Case cards (`CC-101`), New Case modal, status indicators. |
| 7 | `upload_evidence_screen` | Evidence Ingestion & Mapping | `/cases/:id/evidence` | `code.html` (28.5 KB) | 1.0 | Drag & drop file area, SHA-256 fingerprint preview, column auto-mapping review table. |
| 8 | `investigation_graph_screen` | Multi-Hop Graph Explorer | `/cases/:id/graph` | `code.html` (51.6 KB) | 1.0 | Cytoscape.js interactive canvas, 1-4 hop buttons, entity vs detail toggle, details drawer. |
| 9 | `money_trail_explorer_screen` | Money Trail Explorer | `/cases/:id/money-trail` | `code.html` (42.1 KB) | 1.0 | Directed flow graph, data-driven amount quantile filter chips, fan-in/fan-out anomaly badges. |
| 10 | `master_profile_screen` | Cross-FIR Master Profile | `/cases/:id/profiles/:profileId` | `code.html` (36.4 KB) | 1.0 | Resolved entity dossier: aliases, linked phones, bank accounts, vehicles, linked FIRs, provenance. |
| 11 | `lead_advisor_screen` | AI Lead Advisor | `/cases/:id/leads` | `code.html` (39.2 KB) | 1.0 | Explainable lead priority cards, signal score breakdown bars, missing data checklist, Accept/Reject. |
| 12 | `report_generator_screen` | Investigation Report Generator | `/cases/:id/reports` | `code.html` (33.1 KB) | 1.0 | Report section selectors, court compliance metadata, PDF preview, one-click PDF generation. |
| 13 | `audit_log_screen` | Cryptographic Audit Trail | `/audit` | `code.html` (24.2 KB) | 1.0 | Immutable action log table, SHA-256 hash chain verification button, tamper detection indicators. |
| 14 | `users_and_roles_screen` | User Access & Administration | `/admin/users` | `code.html` (22.5 KB) | 1.0 | Admin panel for managing investigators, supervisors, active sessions, and access permissions. |

---

## 2. Analysis of Missing Screens & Visual Proposals

The following screens required by the investigation platform do not have an isolated static Stitch export. They are designed adopting the exact visual tokens, typography, and container styles of the Stitch pack:

### A. Case Workspace & Evidence Table (`/cases/:id`)
* **Proposal**: Reuses the persistent dark left sidebar and top bar from `cases_screen`. The main canvas displays a header card with Case Title, description, status pill, and assigned officers. Below is a tabbed container: Tab 1 is the Evidence Repository showing uploaded files with SHA-256 prefix badges, file sizes, row counts, and inline "Verify Integrity" buttons; Tab 2 shows Case Notes and Investigator Decision log.

### B. Entity Review & Text Extraction Queue (`/cases/:id/review`)
* **Proposal**: Split 50/50 dual-panel layout matching the `investigation_graph_screen` aesthetic. The left panel renders the raw narrative text (FIR/complaint/note) with colour-coded highlighted spans (Phone in Cyan `#06b6d4`, Bank Account in Gold `#f59e0b`, Person in Purple `#8b5cf6`, Vehicle in Emerald `#10b981`). Clicking a highlighted span focuses the right panel table showing extracted entities with confidence chips, edit button, approve/reject toggles, and bulk-approval bar.

### C. Matches Queue & Resolution Center (`/cases/:id/matches`)
* **Proposal**: Structured comparison grid inspired by `master_profile_screen`. Displays candidate pairs side-by-side with shared identifier badges (Phone, Vehicle, Account). Amber alert badge for `SHARED_DEVICE` warnings (when common device is shared without name compatibility). Actions: "Approve Merge" (creates MasterProfile link) and "Reject".

### D. Investigation Timeline (`/cases/:id/timeline`)
* **Proposal**: Integrated either as a bottom collapsible drawer on `/cases/:id/graph` or a dedicated view. Displays a dark chronological vertical/horizontal timeline with glowing event nodes: FIR registrations (Purple), peak call spikes (Crimson), high-value transfers (Blue). Each event card provides a direct link opening the source evidence provenance modal.

### E. Anomaly Alerts Center (`/cases/:id/alerts`)
* **Proposal**: Card grid using the stat card tokens from `dashboard_screen`. Categorizes detected anomalies: Communication Spikes, Sudden New Connections, Bridge Entities, Mule Network Flow (fan-in / pass-through). Each card includes real detected metrics vs threshold.

### F. Case Settings & Threshold Tuner (`/cases/:id/settings`)
* **Proposal**: Form interface encased in glass-panel cards (`bg-[#0c1322]`, `border-[#1a2742]`). Grouped into:
  1. *Communication Thresholds*: Spike MAD multiplier `k`, baseline history window.
  2. *Money Trail Thresholds*: Fan-in `K` accounts, pass-through hours `H`, threshold percentage `R%`.
  3. *Lead Advisor Weights*: Sliders for money flow, bridge centrality, unusual comms, timing, and multi-document linkage (must sum to 100).
  Includes "Save Changes" and "Recompute Analytics" buttons.
