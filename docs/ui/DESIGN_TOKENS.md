# Case Connect AI — Design System & Visual Tokens

Extracted directly from the Stitch UI HTML templates (`docs/ui/pack/stitch_screens/*/code.html`).
All UI components, charts, and graph elements adhere to these tokens to ensure consistent dark-mode tactical agency-grade aesthetics.

---

## 1. Color Palette

### 1.1 Foundation & Backgrounds
* **Base Darkest**: `#030712` (App body, outer backdrop)
* **Base Dark / Header**: `#070b14` (TopBar, navigation background)
* **Deep Navy Canvas**: `#060d1f` / `#0b132b` (Graph canvas background, deep wells)
* **Surface Card**: `#0c1322` / `#0d172e` (StatCards, panels, modal containers)
* **Frosted Glass Panel**: `rgba(8, 18, 38, 0.75)` with `backdrop-blur: 20px`

### 1.2 Borders & Dividers
* **Card Border Subdued**: `#1a2742`
* **Structural Border**: `#1e293b`
* **Subtle Neon Border**: `rgba(56, 189, 248, 0.2)`
* **Active / Focused Border**: `#38bdf8` (Neon cyan glow)

### 1.3 Accents & Highlights
* **Primary Royal Blue**: `#2563eb` (Primary buttons, active indicators)
* **Neon Cyan**: `#00d2ff` / `#06b6d4` (Phone entities, data tags, active filters)
* **Cyber Purple**: `#8b5cf6` / `#9855ff` (Persons, AI Lead Advisor badges)
* **Amber / Warning Gold**: `#f59e0b` (Bank accounts, medium risk, SHARED_DEVICE flag)
* **Emerald / Teal**: `#10b981` (Vehicles, verified status, low risk)
* **High-Risk Crimson**: `#e11d48` / `#ef4444` (Organiser/bridge alerts, high priority)

---

## 2. Typography

* **Font Family**: `'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif`
* **Local Offline Font Bundle**: `@fontsource/inter` (Weights: 300, 400, 500, 600, 700, 800)
* **Scale**:
  - Display / Hero Headline: `2.25rem` (36px), font-extrabold, tracking-tight
  - Screen Title: `1.5rem` (24px), font-bold
  - Section Heading: `1.125rem` (18px), font-semibold
  - Body Text: `0.875rem` (14px), font-normal, text-slate-300
  - Micro / Badges: `0.75rem` (12px), font-medium, tracking-wide
  - Monospace (Identifiers / Hashes): `font-mono`, text-xs (SHA-256 prefixes, account numbers, IP addresses)

---

## 3. Shadows, Glows & Glassmorphism

```css
/* Glass Panel Token */
.glass-panel {
  background: rgba(8, 18, 38, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(56, 189, 248, 0.2);
  box-shadow: 0 0 50px -10px rgba(0, 140, 255, 0.15), inset 0 0 20px rgba(56, 189, 248, 0.05);
}

/* Focused Input Glow */
.neon-border-focus:focus-within {
  border-color: #38bdf8;
  box-shadow: 0 0 15px rgba(56, 189, 248, 0.35);
}

/* High-Risk Red Pulsing Node */
.glow-node-red {
  box-shadow: 0 0 25px 4px rgba(225, 29, 72, 0.65), inset 0 0 10px rgba(225, 29, 72, 0.4);
}
```

---

## 4. Spacing & Dimensions

* **Sidebar Width**: `260px` (Persistent on desktop)
* **Header Height**: `64px` (Sticky top)
* **Border Radii**:
  - `rounded-lg`: `8px` (Buttons, inputs, chips)
  - `rounded-xl`: `12px` (Cards, dialog headers)
  - `rounded-2xl`: `16px` (Floating containers, modal shells)
* **Responsive Baseline**: Desktop-first layout optimized for `1366x768` and `1920x1080` displays.

---

## 5. Icon System

* **Icon Library**: `lucide-react`
* Replaces external CDN font icons (FontAwesome/Material Symbols) with local tree-shakable SVG elements to guarantee offline capability.
