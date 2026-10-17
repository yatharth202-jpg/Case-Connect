# Design System & UX Specification (DESIGN.md) — Case Connect AI

**Document Version:** 1.0.0  
**Status:** Approved Source of Truth  
**Target Environment:** High-Stakes Tactical Forensic Workstations & Presentation Displays  
**Foundation Reference:** PRD.md & Production Forensic Engineering Protocol  

---

## 1. Visual Direction & Design Principles

Case Connect AI is built for police investigators, cyber forensic specialists, and supervisory officers. The interface reflects agency-grade rigor, clarity, and visual restraint.

### Core Principles
1. **Tactical Monochromatic Depth:** A restrained dark palette (`#030712`, `#070b14`, `#0c1322`) eliminates ocular fatigue in dimmed control rooms and provides high contrast against dense relationship networks.
2. **Deterministic Clarity Over Flashiness:** No rainbow gradients, decorative 3D blobs, or cartoonish rounded bubbles. Every pixel communicates investigative hierarchy.
3. **Forensic Semantic Color Coding:** Color carries legal and investigative meaning: Cyan is communication (Phones), Gold is financial (Accounts), Purple is identity (Persons), and Crimson is high-risk anomaly.
4. **Actionable State Hygiene:** Zero generic AI placeholders or lorem ipsum. Every screen provides explicit loading skeletons, clear error remedies, and meaningful empty states.
5. **No Prejudicial Visuals:** Status indicators avoid sensationalist labels like "Criminal" or "Guilty". High anomalies are presented as objective mathematical flags (e.g. `HIGH PRIORITY LEAD`, `CALL SPIKE > 3 MAD`).

---

## 2. Color Palette & Semantic Tokens

### 2.1 Backgrounds & Surfaces
| Token Name | Hex Value | Purpose / Placement |
| :--- | :--- | :--- |
| **`bg-base-darkest`** | `#030712` | Root application canvas, viewport background |
| **`bg-base-header`** | `#070b14` | Fixed top bar, persistent navigation backgrounds |
| **`bg-canvas-deep`** | `#060d1f` / `#0b132b` | Cytoscape graph canvas, timeline wells |
| **`bg-surface-card`** | `#0c1322` / `#0d172e` | Forensic cards, data panels, modals |
| **`bg-frosted-panel`** | `rgba(8, 18, 38, 0.75)` | Floating inspector drawers (`backdrop-blur: 20px`) |

### 2.2 Borders & Dividers
| Token Name | Hex / RGBA Value | Purpose / Placement |
| :--- | :--- | :--- |
| **`border-subdued`** | `#1a2742` | Card outlines, table row dividers |
| **`border-structural`**| `#1e293b` | Major column splits, drawer boundaries |
| **`border-neon-cyan`** | `rgba(56, 189, 248, 0.2)` | Interactive forensic panels |
| **`border-focus`** | `#38bdf8` | Focused inputs, selected graph nodes |

### 2.3 Semantic Accents & Status Indicators
| Token Name | Hex Value | Semantic Meaning & Entity Mapping |
| :--- | :--- | :--- |
| **`accent-primary-blue`**| `#2563eb` | Primary actions, navigation selection |
| **`accent-phone-cyan`** | `#00d2ff` / `#06b6d4` | Phone entities, CDR nodes, communication links |
| **`accent-person-purple`**| `#8b5cf6` / `#9855ff`| Person profiles, identity cards, AI lead badges |
| **`accent-account-amber`**| `#f59e0b` | Bank accounts, money nodes, medium-risk alerts |
| **`accent-vehicle-green`**| `#10b981` | Vehicles, verified chain-of-custody, low risk |
| **`status-high-crimson`** | `#e11d48` / `#ef4444` | High-risk alerts, pass-through mules, audit breaks |

---

## 3. Typography System

* **Primary Font Family:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
* **Local Offline Bundle:** `@fontsource/inter` (Weights: 300, 400, 500, 600, 700, 800)
* **Monospace Font Family:** `'JetBrains Mono', 'Fira Code', 'Courier New', monospace` (Used for SHA-256 hashes, transaction IDs, IMEI numbers, and IP addresses)

### Type Hierarchy
| Scale Name | Size / Rem | Weight | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Display / Hero** | `2.25rem` (36px) | 800 (Extra Bold) | `-0.025em` | Case title header, login banner |
| **Screen Title** | `1.5rem` (24px) | 700 (Bold) | `-0.02em` | Section headers, workspace title |
| **Section Heading**| `1.125rem` (18px) | 600 (Semi-Bold) | `-0.01em` | Panel titles, modal headers |
| **Body Regular** | `0.875rem` (14px) | 400 (Regular) | `normal` | General descriptions, table data |
| **Body Medium** | `0.875rem` (14px) | 500 (Medium) | `normal` | Form labels, navigation links |
| **Micro / Badges** | `0.75rem` (12px) | 600 (Semi-Bold) | `+0.05em` | Badges, tags, status chips |
| **Technical Mono** | `0.75rem` (12px) | 400 (Regular) | `normal` | Cryptographic hashes, cell IDs |

---

## 4. Spacing & Layout System

### 4.1 Structural Dimensions
* **Persistent Sidebar:** `260px` fixed width on desktop (`z-index: 30`). Collapsible to `64px` icon mode or hidden drawer on tablet/mobile.
* **Header Height:** `64px` sticky top (`z-index: 40`) with case breadcrumbs, officer badge indicator, and global search.
* **Canvas Work area:** `calc(100vh - 64px)` with zero window-level horizontal scroll (`overflow-x: hidden`).
* **Inspector Drawer:** `420px` sliding lateral sheet with backdrop blur.

### 4.2 Spacing Scale
* `space-1` = `4px` | `space-2` = `8px` | `space-3` = `12px` | `space-4` = `16px`
* `space-6` = `24px` | `space-8` = `32px` | `space-12` = `48px`

### 4.3 Border Radii
* **Inputs & Action Buttons:** `rounded-lg` (`8px`)
* **Standard Data Cards & Panels:** `rounded-xl` (`12px`)
* **Floating Shells & Modals:** `rounded-2xl` (`16px`)
* **Tags & Priority Chips:** `rounded-full` (`9999px`)

---

## 5. Reusable Components & Specifications

### 5.1 StatCards & KPI Blocks
* **Container:** Deep navy background (`#0c1322`), 1px subtle border (`#1a2742`), soft top-edge highlight.
* **Layout:** Top row icon badge and semantic label, middle row large metric value (`28px`, font-bold), bottom row context/delta string.

### 5.2 Dropzone Evidence Uploader
* **State Default:** Dashed border (`rgba(56, 189, 248, 0.3)`), centered cloud upload icon (`#00d2ff`), accepted format chips (`.CSV`, `.XLSX`, `.JSON`, `.PDF`, `.TXT`).
* **State Drag-Over:** Animated neon cyan border, pulsating background tint (`rgba(0, 210, 255, 0.08)`).
* **State Processing:** Step progress indicator bar with percentage counter and active sub-task label.

### 5.3 Column Mapping Table & Dropdowns
* **Columns:** Source File Column Name, Sample Detected Value, Target Canonical Field (Select Dropdown), Confidence Match Indicator (% pill).
* **Validation:** Missing mandatory fields (Date, Identifier, Amount) highlighted with amber caution border.

### 5.4 Graph Canvas (Cytoscape.js)
* **Background:** Deep well (`#060d1f`) with subtle grid coordinates.
* **Nodes:**
  - Person: Purple rounded glyph with initials and display name.
  - Phone: Neon cyan ring with telephone icon and 10-digit mobile number.
  - Bank Account: Amber hex badge with currency symbol and masked account.
* **Edges:**
  - Communication: Solid neon blue line, thickness proportional to call frequency.
  - Financial: Directed arrows, thickness weighted by transfer amount in paise.

### 5.5 Lead Triage Cards
* **Header:** Priority level chip (`HIGH` crimson, `MEDIUM` amber, `LOW` teal), confidence rating score (`88%`).
* **Body:** Entity label, matched pattern badge (`Rapid Pass-Through`, `Call Spike > 3 MAD`), mathematical breakdown bars.
* **Footer:** Decision buttons (`Accept Lead`, `Reject`, `Need More Data`) with instant confirmation toast.

---

## 6. Navigation & Form Systems

### 6.1 Persistent Left Sidebar
* **Top:** Case Connect AI shield branding and department badge.
* **Case Selector:** Dropdown showing active case ID, title, and priority indicator.
* **Navigation Links:**
  - Dashboard (`/dashboard`)
  - Cases (`/cases`)
  - Evidence Repository (`/cases/:id/evidence`)
  - Graph Explorer (`/cases/:id/graph`)
  - Money Trail (`/cases/:id/money-trail`)
  - AI Lead Advisor (`/cases/:id/leads`)
  - Cryptographic Audit (`/audit`)
  - Court Reports (`/cases/:id/reports`)

### 6.2 Forms & Input Fields
* **Default State:** Background `#0d172e`, border `#1e293b`, text `#f1f5f9`, placeholder text `#64748b`.
* **Focus State:** Border `#38bdf8`, soft outer cyan glow (`box-shadow: 0 0 12px rgba(56, 189, 248, 0.3)`).
* **Disabled State:** Opacity 50%, cursor not-allowed.
* **Validation:** Inline warning text below input with icon.

---

## 7. Loading, Empty & Error States

### 7.1 Skeleton Pulse Loaders
* All data tables, statistics cards, and detail panels render pulsating skeleton rectangles (`#1e293b` with shimmer effect) while asynchronous API fetches execute. Never show a blank screen.

### 7.2 Empty States
* Whenever an entity list or graph has zero records:
  - An SVG icon reflecting the specific domain (e.g., folder with magnifying glass).
  - Clean title: e.g., `"No Evidence Uploaded for This Case"`.
  - Concrete instruction: `"Upload CDR files, Bank Statements, or FIR reports to populate the network."`
  - Direct call-to-action button: `"Upload Evidence File"`.

### 7.3 Actionable Error Boundaries
* If an API call fails:
  - Non-intrusive crimson alert banner or toast notification.
  - User-facing plain-English explanation (e.g. `"Failed to parse statement: Date format in row 42 could not be recognized"`).
  - Recovery action button: `"Retry Ingestion"` or `"Adjust Column Mapping"`.

---

## 8. Micro-Interactions & Transitions

* **Transition Duration:** Strict 150ms to 200ms ease-out transitions (`transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1)`).
* **Card Hover:** Subtle upward translation (`translateY(-2px)`) and border illumination to cyan.
* **Node Hover:** Connected relationship edges illuminate; unconnected nodes diminish to 20% opacity.
* **Button Press:** Active depression effect (`scale(0.98)`).

---

## 9. Responsive Behavior & Screen Constraints

* **Primary Target:** 1920x1080 (Full HD control room monitors) and 1366x768 (Field laptops).
* **Tablet / Projector Displays (1024px to 1280px):** Sidebar collapses automatically to icon bar; inspector drawers open as overlay sheets.
* **Data Table Responsiveness:** All tables maintain sticky header rows and horizontal internal scrolling without triggering global page horizontal overflow.

---

## 10. Accessibility & Statutory Verification

* **Contrast Ratios:** All body text (`#f1f5f9` on `#0c1322`) satisfies WCAG 2.1 AA standard (contrast ratio > 7:1).
* **Color Blindness Accommodation:** Statuses and alerts pair colors with distinct icons (Triangle alert for Warning, Octagon for Danger, Checkmark for Verified).
* **Keyboard Navigation:** Full tab-order navigation across all modals, form inputs, and graph controls.
