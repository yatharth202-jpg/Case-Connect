---
name: Tactical Forensic Intelligence
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#bacbb9'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#859585'
  outline-variant: '#3c4a3d'
  surface-tint: '#18e376'
  primary: '#46fc8b'
  on-primary: '#003918'
  primary-container: '#05df72'
  on-primary-container: '#005d2b'
  inverse-primary: '#006d34'
  secondary: '#a5e7ff'
  on-secondary: '#003543'
  secondary-container: '#00d2ff'
  on-secondary-container: '#00566a'
  tertiary: '#ffd89d'
  on-tertiary: '#432c00'
  tertiary-container: '#ffb410'
  on-tertiary-container: '#6b4900'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#62ff96'
  primary-fixed-dim: '#18e376'
  on-primary-fixed: '#00210b'
  on-primary-fixed-variant: '#005226'
  secondary-fixed: '#b6ebff'
  secondary-fixed-dim: '#47d6ff'
  on-secondary-fixed: '#001f28'
  on-secondary-fixed-variant: '#004e60'
  tertiary-fixed: '#ffdeac'
  tertiary-fixed-dim: '#ffba38'
  on-tertiary-fixed: '#281900'
  on-tertiary-fixed-variant: '#604100'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0.02em
  body-lg:
    fontFamily: JetBrains Mono
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 16px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.06em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.1em
spacing:
  gutter: 1rem
  gutter-dense: 0.5rem
  margin: 1.5rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

This design system is engineered for state-level cybersecurity operations centers, digital forensics extraction suites, and national Law Enforcement Agency (LEA) cyber command units. The visual narrative rejects generic consumer "sci-fi" tropes and decorative gradients in favor of utilitarian operational readiness: high-density data matrices, deterministic status indicators, forensic timeline telemetry, and secure command structures.

### Target Audience & Operational Tone
- **Audience:** Digital forensics investigators, CERT-In response analysts, cyber intelligence officers, and criminal investigation directors.
- **Tone:** Authoritative, uncompromisingly precise, vigilant, and mission-critical. The interface instills confidence through rigorous visual structure and zero-latency clarity under stress.
- **Design Style:** Hardline Tactical Terminal / Defense Monospace Brutalism. It pairs ultra-low-reflection cyber-navy surfaces with high-acuity emerald terminal telemetry, cold signal cyan indicators, and alert-state amber/crimson telemetry badges.

## Colors

The palette simulates specialized field monitor phosphors within darkened command centers, optimizing long-duration optical comfort while preserving critical contrast for threat vectors.

### Palette Architecture
- **Primary (`#05DF72`):** Phosphor Terminal Emerald. Represents operational baseline, active telemetry capture, verified evidence integrity, and system nominal states.
- **Secondary (`#00D2FF`):** Signal Intercept Cyan. Used for active tracking channels, secure socket tunnels, network routing nodes, and secondary metadata readouts.
- **Tertiary (`#FFB300`):** Tactical Warning Amber. Signals anomalous protocol behavior, hash verification warnings, cross-jurisdiction notifications, and evidentiary holds.
- **Critical Alert (`#FF2E4D`):** Tactical Crimson. Applied strictly to threat detection, compromised certificates, intrusion interrupts, and warrant authorization flags.
- **Neutral Core (`#090D16`):** Cyber Navy Deep. The unyielding foundation canvas that absorbs optical glare.
- **Structural Neutral (`#1E2638`):** Slate Steel Surface. Delineates command deck panes, panel headers, and technical perimeter borders.
- **Data Text Neutral (`#BAC7DB`):** Tactical Fog. Provides legible, glare-free telemetry text without burning optical rods.

## Typography

Typography prioritizes cryptographic readouts, byte-level inspection, and situational awareness. 

- **Display & Headings:** `Space Grotesk` delivers an authoritative, engineered character for primary operational sectors and dashboard identifiers, maintaining disciplined horizontal tracking.
- **Telemetry & Body:** `JetBrains Mono` handles all running evidence logs, packet captures, network topology summaries, and interface labels. Standardized character widths guarantee vertical column alignment across hash tables, IP traces, and timeline indices.
- **Labels & Tactical Tags:** Set uppercase with intentional letter-spacing (`0.06em` to `0.1em`) to replicate engraved hardware chassis labels and secure terminal command interfaces.

## Layout & Spacing

The layout is built on a 12-column fixed-maximum fluid grid engineered for dense, multi-display command workstations and hardened mobile field units.

- **Grid Architecture:** Multi-pane modular layouts allow dynamic workspace splitting (terminal stdout, packet graphs, evidence chain-of-custody). Gutter spacing contracts to `gutter-dense` (0.5rem) inside telemetry matrices to maximize real-estate efficiency.
- **Breakpoints & Adaptations:**
  - **Desktop / Multi-Monitor (≥1280px):** 12-column fluid grid, locked split-view sidebars, perpetual terminal footer status.
  - **Tablet (768px - 1279px):** 6-column grid; peripheral telemetry collapses into drawer overlays; investigation panels stack vertically.
  - **Field Mobile (≤767px):** 4-column compact grid, margins compress to `margin-mobile` (0.75rem), complex data tables morph into indexed key-value cards with sticky triage actions.

## Elevation & Depth

This system avoids blurred atmospheric drop shadows, skeumorphic lighting, and glossy ambient gradients. Elevation is conveyed strictly through structural planar layering and technical contrast boundaries.

- **Base Deck (`#090D16`):** The primary background canvas, representing the deepest operational tier.
- **Surface Tier (`#101626`):** Elevated modules, tactical consoles, and data visualization viewports.
- **Panel Outlines:** Panels feature a 1px solid perimeter boundary using `#1E2638`. When in an active or focused state, the outline sharpens to `#05DF72` or `#00D2FF` with zero diffusion.
- **Critical Intercept Overlays:** Modals and priority alert drawers utilize `#0E1422` with a 1px hard border of `#FF2E4D` and a crisp, opaque tactical backdrop barrier (`#090D16` at 85% opacity, non-blurred) to preserve immediate readability.

## Shapes

The shape system is strictly architectural and non-rounded (`0px`). Curves and softened corners are deliberately omitted to preserve the aesthetic of hardened tactical computing terminals, avionics displays, and defense instrumentation consoles.

- **Cut Corners & Notches:** Primary module headers and critical alert badges may feature a 45-degree chamfered corner (4px) to indicate physical security hardware lineage.
- **Structural Dividers:** Crisp, hairline (1px) borders divide tabular forensic output without soft separators or radiused dividers.

## Components

### Action Controls (Buttons)
- **Primary Intercept Action:** Background `#05DF72`, foreground `#090D16`, bold monospace uppercase. No corner radius. Focus states apply a 2px offset border in `#05DF72`.
- **Secondary / Command Line Action:** Background transparent, 1px border `#1E2638`, text `#00D2FF`. Hover triggers `#1E2638` surface tint with `#00D2FF` border glow.
- **Critical / Interruption Trigger:** Background transparent, 1px solid `#FF2E4D`, text `#FF2E4D`. Active click fills background with `#FF2E4D` and sets text to `#090D16`.

### Tactical Chips & Status Badges
- **Status Indicators:** 1px bordered micro-chips (`label-sm`). Text in full uppercase (e.g., `CASE//RESOLVED`, `SEV-1//EXPLOIT`, `CHAIN-OF-CUSTODY//VALID`).
- **Telemetry Indicators:** Include a 6px square glyph preceding the text (e.g., green square for live node connection, pulsing amber square for packet dropped).

### Data Tables & Forensics Lists
- **Structure:** Monospaced cell formatting with alternating row fills (`#090D16` and `#0D1322`).
- **Grid Lines:** Hairline 1px horizontal borders in `#1E2638`.
- **Hashes & Network Telemetry:** Truncated strings use midpoint ellipsis with instant click-to-verify state transitions.

### Checkboxes & Toggle Switches
- **Checkboxes:** 14px sharp-edged squares, 1px border `#1E2638`. Checked state renders a solid `#05DF72` fill with a centered `#090D16` dot.
- **Toggle Switches:** Segmented, rigid dual-block displays (e.g., `[ OFF | ON ]`) rather than sliding pill toggles. The active state highlights with solid slate or terminal emerald.

### Form Inputs & Terminal Command Prompts
- **Input Fields:** Crisp 1px `#1E2638` border on `#0B101D` fill. Focus changes border to `#00D2FF` with zero ambient shadow.
- **Prefixed Inputs:** Shell prompt syntax (`cmd://` or `investigation#`) fixed inside the leading edge of input fields in `#05DF72`.

### Forensic Dossier Cards
- **Structure:** Modular boxes featuring an explicit header band containing system classification markers (e.g., `CONFIDENTIAL // LEA USE ONLY`).
- **Footer Metadata:** Compact monospaced timestamp and audit signature rendered in `body-sm` `#BAC7DB`.