# Case Connect AI — Forensic Platform Production Hygiene Protocol

This master checklist integrates all 6 quality pillars (Visual Aesthetics, UX Hygiene, Configuration & Infrastructure, Secrets & Tokens, Authentication & Authorization, Input Validation & Security). 
Every phase and component must pass this 6-layer audit 3 to 4 times before being marked ready.

---

## Pillar 1: Law Enforcement Visual Aesthetics
*Avoid generic software cliches. Deliver high-end, agency-grade law enforcement software.*

1. **NO Harsh or Rainbow Gradients**: Use restrained, calibrated dark surfaces (`#030712`, `#070b14`, `#0d172e`) with monochromatic depth.
2. **NO Generic Icon Slop**: Use intentional, restrained icons only where they add semantic clarity. Never decorate every paragraph with icons.
3. **NO Pure White / Eye-Straining Backgrounds**: Strict dark mode foundation tailored for forensic control rooms and projectors.
4. **NO Drop Shadow Overload**: Use subtle borders (`#1a2742`, `#1e293b`) and micro-elevations instead of muddy, heavy drop shadows.
5. **NO Repetitive "3 Feature Cards in a Row"**: Use asymmetric, functional layout hierarchies (split screens, data tables, analytical drawers).
6. **NO Emojis in UI**: Strictly prohibited in judicial/police software. Use professional typography and clear status badges.
7. **NO Liquid Glass / Cheap Blur Overload**: Minimalist, clean surfaces with crisp borders. No distracting blurry blobs.
8. **NO Em-Dashes (—) Slop in Copywriting**: Use concise, professional English and clear technical descriptions.
9. **Curated Typography**: Use clean Inter with tuned weights and letter-spacing; no gimmicky space grotesk or trendy fonts.
10. **NO Colored Left Stripes on Every Card**: Status indicated through subtle text badges (`HIGH`, `MEDIUM`, `LOW`).
11. **NO Fake Testimonials or Marketing Fluff**: The app is an analytical tool for police investigators, not a SaaS landing page.
12. **NO Generic Bento Grids**: Every grid panel must serve a specific forensic data purpose (CDR timeline, money trail, entities).
13. **NO Fake Terminal Windows**: Provide real functional UI components and real downloadable log tables.
14. **NO Gimmick Copy ("It's not X, it's Y")**: Plain, factual statements only.
15. **NO Checkmark Bullet Slop**: Use structured data lists, data tables, and key-value inspect drawers.
16. **NO Pricing Tiers**: Dedicated to law enforcement case workflows.
17. **Real Forensic Capabilities Only**: Zero fake mock diagrams; every chart and graph is rendered from real uploaded inputs.
18. **Crisp Corners**: Tuned 8px - 12px radii; no cartoonish, overly round bubbly pill shapes.
19. **NO Purple & Black Cliche Overuse**: Calibrated slate navy with functional semantic accents (Cyan = Phone, Gold = Account, Blue = Link).
20. **Skeleton Loaders Required**: Loading states must use pulse skeletons; never leave empty white/black flashing screens.
21. **NO Radial Orbs or Decorative Blurred Blobs**: Clean, focused tactical workspace without visual distraction.
22. **NO Dot Grid Background Noise**: Flat, high-contrast forensic surfaces.
23. **NO Sparkle / Magic AI Icons**: In criminal analysis, AI is a deterministic rule-based assistant ("Lead for review"), never "magic".
24. **NO Animated Bouncing Arrows**: Direct, predictable buttons and navigation.
25. **Legal & Compliance Documents Present**: Terms of Service (DPDP Act 2023) and Evidence Integrity Policy (Section 63 BSA 2023).
26. **Subtle Micro-Interactions**: Hover states should be crisp, immediate, and functional (150ms transitions, no dizzying zooms).
27. **NO Neon Bleed**: Muted, accessible contrast ratios that pass WCAG AA standards.
28. **NO Basic Pastel Tones**: High-clarity, high-contrast dark theme.

---

## Pillar 2: UX & Frontend Hygiene
1. **Zero Horizontal Scrolling**: Viewport locked (`overflow-x-hidden`), layout desktop & laptop responsive (`1366x768` to `1920x1080`).
2. **Zero Broken Links**: Every route, anchor, and internal link must resolve to a valid route or modal.
3. **Responsive Navigation**: Collapsible sidebar with accessible mobile/tablet drawer.
4. **Custom Forensic Favicon**: Clean SVG shield badge.
5. **Accurate Page Titles**: Dynamic page titles per screen (`Case Connect AI — Investigation Graph`, etc.).
6. **Descriptive Meta Tags**: Meta description, viewport, author, and security headers.
7. **Complete Footer**: Working legal notices, version number, court compliance badges.
8. **Custom 404 Error Screen**: Dedicated, styled error page with "Return to Dashboard" action.
9. **Correct Timestamp & Year**: Active case year `2026` (Smart India Hackathon 2026).
10. **Optimized Assets**: Pure SVGs, local bundled fonts, no uncompressed raster images.
11. **Interactive Buttons with Feedback**: Loading spinners and disabled states during API calls.
12. **Toast Success Messages**: Clear notification when evidence is uploaded, mapping confirmed, or lead accepted.
13. **Actionable Error Messages**: Clear explanation of failures (e.g., "Invalid column mapping: missing date column"), never raw stack traces.
14. **Zero Placeholder Text**: No "Lorem Ipsum", "John Doe", or generic filler. Real empty states ("Upload CDR CSV to begin").
15. **Zero Dead Navigation Items**: Any route under development must show an informative state or be clearly marked.
16. **No Mobile Overflow**: All tables scroll horizontally *inside their containers* without breaking the page width.
17. **Clickable Branding**: Logo navigates to `/dashboard` or active case view.
18. **Clickable Contact & System Actions**: Official support modal with copyable police helpline & department ID.
19. **Complete Mobile/Projector Optimization**: Tested and verified at standard presentation aspect ratios.

---

## Pillar 3: Configuration & System Hygiene
1. **Strict CORS Scoping**: Backend CORS limited strictly to authorized origins (`http://localhost:5173`, `http://127.0.0.1:5173`). Wildcard `*` is banned in production paths.
2. **No Exposed Source Maps**: Production frontend build strips debugging source maps from public output.
3. **No Sensitive Data Leaks**: Strict `data/private/` isolation; server logs never output passwords, tokens, or raw PII.
4. **Zero Vulnerable Dependencies**: Pinned versions, regular audit checks, and no deprecated insecure libraries (bcrypt used directly, NOT passlib).

---

## Pillar 4: Secrets & Token Safety
1. **JWT Secret Protection**: `JWT_SECRET` loaded strictly from environment variable / `.env`; never hardcoded in source.
2. **Zero API Secrets in Code**: All API keys, DB credentials, and private keys restricted to `.env`.
3. **Safe Storage**: Auth tokens stored safely; sensitive case payloads cached only in memory/session.
4. **Zero Default Passwords**: `scripts/seed_users.py` demands manual terminal password creation with validation. No hardcoded `admin/admin` credentials.

---

## Pillar 5: Authentication & Access Control
1. **BOLA / IDOR Defense (Broken Object Level Authorization)**: Every case-scoped endpoint (`/cases/{id}/...`, `/evidence/{id}/...`, `/matches/{id}/...`) strictly verifies case membership of the requesting user.
2. **Rate Limiting**: Brute-force protection on authentication routes (`/auth/login`).
3. **Military-Grade Password Hashing**: Hashed with bcrypt (12 salt rounds) before database storage.
4. **Server-Side RBAC Enforcement**: Role permissions (`admin`, `investigator`, `viewer`) verified server-side on every request; never rely on frontend UI hiding alone.
5. **Row Level Security / Case Scoping**: SQLite and Neo4j queries always parameterised with `WHERE case_id = $case_id`.

---

## Pillar 6: Injection & Input Validation
1. **SQL Injection Defense**: 100% SQLAlchemy ORM and parametrised queries. No string-concatenated SQL queries anywhere.
2. **Cypher Injection Defense**: Parametrised Cypher only. Variable-length hop parameter `$n` strictly validated as integer `{1,2,3,4}` before string formatting.
3. **XSS Protection**: React automatic HTML escaping, strict Content-Security-Policy headers, no `dangerouslySetInnerHTML`.
4. **CSRF Protection**: Bearer token JWT architecture with SameSite cookie controls where applicable.
5. **Strict File Upload Validation**:
   - Extension validation (`.csv`, `.xlsx`, `.json`, `.txt`, `.pdf`, `.docx`).
   - Magic byte header checks (prevent executable file renaming).
   - Strict size caps (<= 200 MB for data files, <= 20 MB for document files).
   - Stream-computed SHA-256 fingerprinting for chain of custody.
6. **SSRF Defense**: Backend makes zero outbound network calls to user-supplied URLs. Offline-first architecture.
