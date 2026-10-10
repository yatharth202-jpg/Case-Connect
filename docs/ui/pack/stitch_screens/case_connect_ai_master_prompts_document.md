# Case Connect AI - Architecture & Antigravity Master Prompts Documentation

This document contains the exact production prompts for all 12 unique modules of **Case Connect AI**, verified against layout parameters, dark-mode design system specs, and sidebar navigation routing.

---

### Global Design System Specifications
- **Viewport**: 100vh / fixed height desktop app layout (`h-screen overflow-hidden` or single fixed screen, non-scrolling, internal panel scrolling only).
- **Navigation Model**: Persistent Left Sidebar (260px) + Header bar (64px) with dynamic internal routing.
- **Color Palette**:
  - Background Base: `#070b14` / `#0b132b`
  - Surface Containers: `#0d172e` / `#132247` with border `#1e293b` / `#1e3a8a33`
  - Accents: Electric Blue `#2563eb` / `#3b82f6`, Neon Purple `#8b5cf6`, Amber `#f59e0b`, High-Risk Crimson `#ef4444`, Success Emerald `#10b981`
- **Render Engine**: Pure CSS / SVG for all graphs, radial charts, node connections, sparklines, and maps (no static mock raster images).

---

### Module 1: Login Screen
```text
Screen Title: Login Screen
Type: Standalone Authentication Page (Desktop 1920x1080 / 100vh Fixed Layout)
Layout: Split 50/50 Screen Layout with dark tactical aesthetic.

Left Section (Hero Branding):
- Deep navy background (#070B14) with subtle glowing radial gradients and digital police grid lines.
- Indian Police crest emblem icon at top left with gold/amber glow.
- Large Typography: "Case Connect AI", Sub-badge: "AI-Powered Criminal Network Analysis System".
- Headline: "Connect the dots. Uncover the truth."
- Subtext: "Unified analysis of FIRs, call records, bank data and more to reveal hidden connections in criminal networks."
- 5 Feature Capability Badges in a horizontal row:
  1. FIR Analysis (Document icon)
  2. Call Record Insights (Phone icon)
  3. Financial Tracking (Bank icon)
  4. Network Mapping (Network node icon)
  5. AI-Powered Leads (Brain/AI icon)

Right Section (Login Card):
- Centered floating frosted card (backdrop-blur-md, bg-#0d172e/90, border-slate-700/50, rounded-2xl, p-10, max-w-lg).
- Header: "Welcome Back" (white) + "Back" (neon blue), subtitle: "Sign in to continue your investigation".
- Form Fields:
  - User ID / Email: input with user silhouette icon, placeholder "Enter your user ID or email".
  - Password: input with lock icon, eye toggle icon for show/hide, placeholder "Enter your password".
  - Row: "Remember me" checkbox on left, "Forgot password?" blue link on right.
- Primary CTA: Gradient button (purple #8b5cf6 to royal blue #2563eb, font-medium, rounded-xl, py-3) with label "Login →".
- Divider: "OR - Login with".
- Secondary Action Buttons:
  - "Department SSO" (with police shield icon)
  - "Aadhaar (Govt. Login)" (with fingerprint icon)
- Bottom Fixed Status Bar: "🔒 Secure & Encrypted | Trusted for a Safer India | For Law Enforcement Only | Case Connect AI | Smart India Hackathon 2026 | Team UNITx".
```

---

### Module 2: Role Selection Screen
```text
Screen Title: Role Selection Screen
Type: Onboarding / Access Authorization (Desktop 100vh Fixed Viewport)
Layout: Top Navbar + Left 3-Step Wizard Progress Indicator + 3-Column Interactive Role Selection Grid + Bottom Compliance Footer.

Top Navbar:
- Left: Case Connect AI Shield emblem and title.
- Right: Action buttons "Need Help?" and "Logout".

Left Step Indicator:
- Step 1 (Active/Glowing Blue): "Select Role - Choose your role to access features".
- Step 2 (Pending/Gray): "Verify Access - Authentication check".
- Step 3 (Pending/Gray): "Go to Dashboard - Start your investigation".

Main Center Area:
- Page Header: "Select Your Role" (Gradient text) - "Access the features and data based on your responsibility".
- 3 Role Cards Grid:
  Card 1 (Investigator - SELECTED STATE with blue glowing border and ring):
  - Banner header: Tactical dark operations room.
  - Role Icon: Blue search/magnifying glass badge.
  - Title: "Investigator", Subtitle: "View and analyse cases, upload evidence, explore networks and generate leads."
  - Feature Checklist:
    ✓ Create and manage cases
    ✓ Upload and analyse evidence
    ✓ Explore investigation graph
    ✓ View money trail and leads
  - Button: "Selected ✓" (Full width electric blue button).

  Card 2 (Supervisor - Default State):
  - Banner header: Police officers briefing room.
  - Role Icon: Purple group/team badge.
  - Title: "Supervisor", Subtitle: "Review, approve and monitor investigations. Ensure data quality and team performance."
  - Feature Checklist:
    ✓ Review and approve cases
    ✓ Monitor team investigations
    ✓ Manage cross-FIR links
    ✓ Generate and share reports
  - Button: "Select Role" (Outline dark button).

  Card 3 (Admin - Default State):
  - Banner header: Server room data center.
  - Role Icon: Green gear/settings badge.
  - Title: "Admin", Subtitle: "Manage users, data, system settings and overall platform configuration."
  - Feature Checklist:
    ✓ User and role management
    ✓ Data source configuration
    ✓ System settings and security
    ✓ View audit logs
  - Button: "Select Role" (Outline dark button).

Bottom Notice Bar:
- Information icon: "Your role determines what data you can access and what actions you can perform. All activities are logged for security and audit purposes."
- Trust badges: "Secure | Trusted | For a Safer India".
```

---

### Module 3: Dashboard Screen
```text
Screen Title: Dashboard Screen
Type: Master Command Center (Desktop 100vh, Persistent Sidebar Navigation, No page scroll)
Layout: Persistent Left Sidebar + Sticky Header + 4 Top KPI Cards + 2:1 Main Interactive Canvas + 3-Column Bottom Data Grid.

Left Sidebar (Persistent across app):
- App Logo: Golden Indian Police Shield + "Case Connect AI (AI-Powered Criminal Network Analysis System)".
- Nav Items: Dashboard (active indicator), Cases, Upload Evidence, Investigation Graph, Money Trail, Master Profiles, Lead Advisor, Reports, Audit Log, Users & Roles, Settings.
- Sidebar Footer: Indian Flag emblem + "Together for Safer India - Central Crime Branch Network".

Top Header:
- Title: "Dashboard - Overview of investigations, evidence and key insights".
- Global Omni-search bar: "Search cases, people, phone numbers, accounts...".
- Date indicator: "Thu, 12 Oct 2026 | 10:24 AM".
- Notification bell with unread badge "3".
- Profile Badge: "Inspector Meera - Lead Investigator".

Top KPI Stats Row (4 Metric Cards with inline SVG glowing trendlines):
1. Total Cases: "12" (+20% up sparkline)
2. Active Investigations: "4" (+33% up sparkline)
3. People Identified: "28" (+15% up sparkline)
4. Bank Accounts: "17" (+21% up sparkline)

Middle Section (2:1 Grid):
- Left (Investigation Map - Live Overview):
  - Filter Pills: People, Phone Numbers, Bank Accounts, Locations.
  - Interactive Dark Geographic Network Map: Built with inline SVG coordinate nodes (Delhi [High Risk Red], Mumbai, Bengaluru, Kolkata) with animated pulsating connection paths and node counter badge "18 Nodes Active • 4 Cross-Jurisdictions".
  - SVG Zoom (+ / - / Reset) map controls on top-right.
- Right Column:
  - "Quick Actions" Card: 4 quick buttons: "+ Create New Case", "Upload Evidence", "Explore Investigation Graph", "Analyse with AI".
  - "System Status" Card: Status items with pulsing green dots: AI Analysis Engine (Online), Evidence Processing (Online), Graph Database (Online), Report Generation (Online).

Bottom Row (3 Columns):
1. "Recent Cases" Table: Columns for Case ID (CC-101, CC-100, CC-099, CC-098), Title, Date, Status badge (Active, Analysis, Closed).
2. "Recent Activity" Timeline: Event log entries with icons for file uploads, suspect correlations, and transaction anomalies.
3. "AI Insights" Cards: High-risk network alert, ₹2.3 Crore transaction anomaly, and 2 new cross-FIR links found.
```

---

### Module 4: Cases Screen
```text
Screen Title: Cases Screen
Type: Case Management & Intake Dossier (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + Two-Column Split (Create Case Form vs Existing Cases Search Table) + Bottom Case Overview Details Panel.

Top Section (Split Grid):
- Left Card ("Create New Case"):
  - Form Fields:
    - Case Title (e.g., "Cyber Fraud Ring")
    - FIR Number (e.g., "FIR/2026/00123")
    - Case Type (Dropdown: Cyber Crime, Financial Fraud, Narcotics, Organized Crime)
    - Police Station & District (Dropdown selectors)
    - Case Date picker (e.g., "12 Oct 2026")
    - Case Description textarea
    - Initial Evidence Upload dropzone with drag-drop icon and file size limit.
  - Buttons: "Reset" (Ghost button) and "Create Case" (Gradient Blue CTA).

- Right Card ("Open Existing Case"):
  - Search Bar with filter query input and "Search" button.
  - Filter Tabs: All Cases, Active, Under Analysis, Closed, Case Type.
  - Data Table:
    - Columns: Case ID, Title, Police Station, Date, Status, Action ("Open" button).
    - Rows: CC-101 (Active), CC-100 (Analysis), CC-099 (Closed), CC-098 (Active), CC-097 (Closed), CC-096 (Analysis), CC-095 (Closed).
  - Pagination: "Showing 1-7 of 32 cases" with numbered page buttons.

Bottom Panel ("Case Overview - CC-101"):
- Tab Bar: Overview (active), Evidence, Investigation Graph, Money Trail, AI Insights, Reports, Status badge (Active).
- 3-Column Dossier Summary:
  1. Basic Information: Case ID, Title, FIR Number, Case Type, Station, District, Date, Description.
  2. Key Statistics: 4 metric tiles: 12 Evidence Files, 8 Persons Identified, 15 Phone Numbers, 6 Bank Accounts, 4 Locations, 11 Cross-FIR Links.
  3. Recent Updates Feed: Live chronological log of new evidence uploads, suspect identity correlations, and AI generated leads.
```

---

### Module 5: Upload Evidence Screen
```text
Screen Title: Upload Evidence Screen
Type: Evidence Ingestion & AI Extraction Pipeline (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header with 4-Step Pipeline Bar + Top Evidence Intake Area + Bottom Processing Ledger & Extracted Entity Drawer.

Top Pipeline Stepper:
- 1. Upload Files (Active) → 2. Extract Data → 3. Review & Verify → 4. Analyse & Link.

Top Row (Split View):
- Left: Drag & Drop Upload Zone:
  - Cloud upload SVG icon, prompt "Drag and drop files here or Click to browse".
  - Formats: PDF, CSV, Excel, Images (JPG, PNG), Text files (Max 50MB per file).
  - Button: "Choose Files" (Electric blue).
- Middle: Supported Evidence Types Card:
  - FIR / Police Reports (PDF, Text)
  - Call Records CDR (CSV, Excel)
  - Bank Statements (PDF, CSV)
  - Other Documents (Chat logs, DOCX).
- Right: File Processing Status Progress Bars:
  - FIR_CC101.pdf (80% Extracting text and entities)
  - CallRecords.csv (45% Parsing call records)
  - BankStatement.pdf (0% In queue)
  - WhatsAppChat.pdf (100% Completed, Green bar).

Middle / Bottom Row:
- Left: "Uploaded Files (4)" Table:
  - Bulk action: "Remove Selected".
  - Columns: Checkbox, File Name, Type, Upload Date, Size, Status pill (Processed, Processing), Extracted Records, Action ("View" button).
- Right: "Extracted Data Summary (CC-101)":
  - Metric badges: 12 Persons Identified, 18 Phone Numbers, 6 Bank Accounts, 4 Locations, 45 Chat Messages, 8 Other Entities.
  - Preview Extracted Data tabs: Persons (12), Phone Numbers (18), Bank Accounts (6), Locations (4).
  - Entity table showing Name, Type, Source File, AI Confidence (e.g., 98%, 95%), and "View" action.
- Bottom Workflow Graphic:
  - Pure SVG connected flow diagram: Text Extraction → Entity Recognition → Data Standardization → Linking Across Files.
```

---

### Module 6: Investigation Graph Screen
```text
Screen Title: Investigation Graph Screen
Type: Complex Network Intelligence Graph (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Filter Sidebar + Central Force-Directed Network Graph + Right Suspect Inspector Panel + Bottom Cross-Entity Summary Ledger.

Header Bar:
- Title: "Investigation Graph – Case CC-101".
- Subtitle: "Visualize connections between people, phone numbers, bank accounts, locations and organisations."
- Right Action Buttons: "Graph Analytics", "Export Graph", "Fullscreen".

Left Graph Filters Panel:
- Node Types (Checkboxes with color dots & counts): Persons (24), Phone Numbers (18), Bank Accounts (12), Locations (8), Organisations (6).
- Relationship Types: Calls (52), Bank Transactions (28), Common Location (16), Co-occurrence FIR (11), Association (9).
- Time Range selector dropdown ("Last 6 months") and "Apply Filters" CTA button.

Center Graph Canvas (Built via inline SVG network graph):
- Dark graph canvas with grid backdrop.
- Node legend on top: Nodes: 68 | Edges: 116 | Clusters: 5 | High-Risk Nodes: 8.
- Search input inside graph: "Search in graph...".
- Core Hub: Primary Suspect node "Rohan Sharma (Prime Target)" glowing high-risk crimson red with glowing pulse rings.
- Surrounding interconnected orbital SVG nodes with labeled edge lines:
  - HDFC Bank & AXIS Bank nodes (gold/amber) with financial transfer arrows.
  - Co-accused nodes: "Amit Verma (Associate)", "Neha Patel (Financial Link)", "Vikram Singh (Co-accused)", "Sanjay Mehta (Suspect)".
  - Shell company node: "Shree Traders Pvt Ltd".
  - Location nodes: Delhi, Mumbai, Bengaluru.
- SVG floating zoom controls (+, -, center).

Right Panel ("Node Details"):
- Suspect Card: Rohan Sharma (ID: P-001, High Risk).
- Tabs: Overview, Connections (18), Evidence (7).
- Bio Attributes: Full Name, Aliases (R. Sharma, Rohit S.), Phone Numbers (3 linked), Bank Accounts (2 linked), Locations (5 linked), Related FIRs (CC-101, CC-099, CC-087).
- Risk Score Meter: Progress bar at 92% (High Risk Crimson).
- AI Summary Box: "Rohan Sharma appears to be a key node with multiple financial transactions linked to shell companies. Connected across 3 different FIRs with common phone numbers and locations."

Bottom Summary Strip (4 Columns):
- Key Connections (Name, Type, Relationship, Strength 0.92)
- Top Locations (Delhi, Mumbai, Bengaluru)
- Top Phone Numbers (+91 98765 43210, +91 91234 56789)
- Top Bank Accounts (AXIS, HDFC, SBI, ICICI, PNB).
```

---

### Module 7: Money Trail Explorer Screen
```text
Screen Title: Money Trail Explorer Screen
Type: Financial Forensics & Fund Layering Visualizer (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + Left Transaction Filters + Center Circular Radial Fund Flow Network + Right Selected Account Dossier + Bottom Ledger & Bar Chart.

Header:
- Title: "Money Trail Explorer – Case CC-101".
- Actions: "Switch to Graph View", "Export Report", "Fullscreen".

Left Filters:
- Time Range: "Last 6 months".
- Amount Range (₹ Min/Max inputs).
- Account Type dropdown.
- Transaction Types: All, Incoming (Green), Outgoing (Red), Self Transfer (Blue).
- Suspicion Level: High Risk, Medium Risk, Low Risk, Normal.
- Button: "Apply Filters".

Center Visualizer ("Money Flow Network - Top Accounts"):
- Header Stats: Accounts: 18 | Transactions: 124 | Total Flow: ₹12.4 Crore.
- Pure SVG Radial Financial Topology Diagram:
  - Central Core: "AXIS Bank A/c XXXX3210 (HIGH RISK)" in red pulsing circle.
  - Inflow & Outflow radial vectors with labeled transfer amounts:
    - Arrow from Rohan Sharma (Primary): ₹18.5L
    - Arrow to Neha Patel: ₹2.3L
    - Arrow from Vikram Singh: ₹18.5L
    - Arrow to Shree Traders Pvt Ltd: ₹4.7L / ₹6.4L
    - Arrow to ICICI Bank: ₹2.5L
    - Arrow to M/s Tech Solutions: ₹2.2L
    - Arrow to Shell Company A: ₹1.8L
    - Arrow to Cash Withdrawal (ATM): ₹2.5L
    - Arrow from Sanjay Mehta: ₹9.2L / ₹3.1L.

Right Panel ("Selected Account Details"):
- Card: AXIS Bank A/c XXXX3210 (High Risk).
- Attributes: Account Holder (Rohan Sharma), Account Type (Savings), IFSC Code, Linked Phone Numbers (3), Linked Persons (5), Linked Companies (2).
- Balances: Total Inflow (₹8,72,34,500), Total Outflow (₹8,55,12,300), Current Balance (₹17,22,200).
- "AI Insight" Box: Detecting multiple round transactions, shell company layering, and frequent cash withdrawals.

Bottom Split Section:
- Left: "Recent Transactions (AXIS Bank)" Table with Date, From, To, Amount, Type (Incoming/Outgoing), and Risk badge.
- Middle: "Flow Over Time" pure SVG dual-bar chart showing monthly Inflow vs Outflow over 6 months.
- Right: "Top Receiving Accounts" summary ranking.
```

---

### Module 8: Master Profile Screen
```text
Screen Title: Master Profile Screen
Type: Entity Intelligence Dossier & Cross-FIR Correlator (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + Suspect Overview Strip + Left Personal Dossier & Tabs + Center Star Identity Network + Right FIRs/Associates Lists + Bottom AI Insight Panel.

Header:
- Title: "Master Profile – Rohan Sharma (P-001)".
- Subtitle: "Consolidated view of a person with links across multiple FIRs, phone numbers, bank accounts, locations and organisations."
- Actions: "Generate Profile Report", "Explore in Graph", Options dropdown.

Top KPI Stats Strip (6 Metric Tiles):
1. 5 Linked FIRs
2. 3 Phone Numbers
3. 4 Bank Accounts
4. 6 Locations
5. 3 Companies
6. 8 Related Persons.

Center-Left Section:
- Profile Card: Photo avatar of Rohan Sharma, ID: P-001, "High Risk" crimson badge.
- Bio Data: Aliases (R. Sharma, Rohit S., Rohan S.), Father's Name (Manoj Sharma), DOB (14 Mar 1992, Age 34), Nationality (Indian), Known Addresses (3 locations linked), Occupation (Director - Shell Company), Risk Score Bar: 92%.
- Tabbed Data View: Phone Numbers (3) | Bank Accounts (4) | Addresses (3) | Organisations (3) | Evidence (12).
  - Phone Numbers table with Number, Type, Linked FIRs, First/Last Seen, Status (Active/Inactive), Action ("View").
  - Bank Accounts table with Account Number, Bank Name, Type, Total Txns, Risk Status.

Center Section ("Identity Network - Linked Entities"):
- Pure SVG radial star diagram centered on Rohan Sharma with connector lines branching out to:
  - 3 Phone Numbers (Green node)
  - 4 Bank Accounts (Amber node)
  - 3 Companies (Blue node)
  - 6 Locations (Magenta node)
  - 8 Related Persons (Cyan node)
  - 5 FIRs (Purple node).

Right Column:
- "Linked FIRs" list: CC-101 (Active), CC-099 (Active), CC-087 (Under Analysis), CC-066 (Closed), CC-054 (Under Analysis).
- "Related Persons" list: Amit Verma (Associate), Neha Patel (Financial Link), Vikram Singh (Co-accused) with avatars and link counts.
- "Linked Locations": Delhi (12 events), Mumbai (8 events), Bengaluru (5 events).
- "Linked Companies": Shree Traders Pvt Ltd (Shell Company), M/s Tech Solutions (Under Scanner).

Bottom Row ("AI Insights"):
- 4 Alert Cards: Multiple FIR Links across 3 states, Common Phone Network with co-accused, Shell Companies involvement, and Frequent Locations correlations.
```

---

### Module 9: Lead Advisor Screen
```text
Screen Title: Lead Advisor Screen
Type: AI Lead Prioritization & Case Action Recommendations (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + 3 Priority Metric Cards + Left Prioritized Leads Queue + Right Lead Deep-Dive Dossier + Bottom Related Entities & Evidence Snapshot.

Header:
- Title: "Lead Advisor – AI Generated Leads".
- Subtitle: "Get intelligent lead suggestions based on analysed evidence, patterns and network connections."
- Actions: "Refresh Leads", "Export Leads".

Top KPI Cards:
1. Total Leads: "12" (+3 new)
2. High Priority: "4" (+1 new) [Crimson badge]
3. Medium Priority: "5" (+2 new) [Amber badge].

Left Section ("AI Generated Leads"):
- Filter Tabs: All Leads (12), High (4), Medium (5), Low (3).
- Vertical Lead Cards Queue:
  1. Lead 1 (SELECTED with blue active border): "Link to Shell Company - Rohan Sharma linked to M/s Tech Solutions..." (High Priority, Banking/Company tags, 12 Oct 2026).
  2. Lead 2: "Common Phone Network - +91 98765 43210 appears in 3 different FIRs..." (Phone/Cross-FIR tags, 11 Oct 2026).
  3. Lead 3: "Large Fund Transfers - ₹18.5L transferred from AXIS Bank to HDFC Bank..." (Money Trail/High Value tags, 10 Oct 2026).
  4. Lead 4: "Location Pattern - Neha Patel and Vikram Singh present at same locations..." (Location/Co-occurrence tags, 09 Oct 2026).
  5. Lead 5: "New Associated Person - Amit Verma connected through shared phone numbers..." (Person/Network Expansion tags, 08 Oct 2026).

Right Section ("Lead Details"):
- Header: "Link to Shell Company", High Priority Badge, Confidence Score: 92% (Progress bar), Action: "Mark as Reviewed".
- Sub-tabs: Summary (active), Supporting Evidence (5), Related Entities (4), Graph View.
- "AI Analysis" Narrative: "Rohan Sharma is linked to M/s Tech Solutions through common bank transactions, shared directors, and matching addresses. The company also appears in FIRs CC-087 and CC-099, suggesting a possible shell company used for layering funds."
- Two-Column Action Plan:
  - "Key Points": ₹18.5L transferred, same director (Sanjay Mehta), registered address matches FIR CC-087, multiple round transactions.
  - "Recommended Actions" Checklist:
    ✓ Verify company registration details
    ✓ Check additional bank accounts
    ✓ Investigate directors and shareholders
    ✓ Cross-check with other linked FIRs
    ✓ Conduct site verification at registered address.

Bottom Section:
- Left: "Related Entities" table (Rohan Sharma [92% risk], M/s Tech Solutions [85%], AXIS Bank A/c [78%], Sanjay Mehta [74%]).
- Middle: "Evidence Preview" file chips (Bank Statement, Call Records CSV, FIR PDF, Company Docs).
- Right: "Graph Snapshot" mini pure SVG node view showing Rohan Sharma connecting to M/s Tech Solutions and Sanjay Mehta.
```

---

### Module 10: Report Generator Screen
```text
Screen Title: Report Generator Screen
Type: Investigation Dossier & PDF Export Builder (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + 4-Column Builder Workflow (Report Type → Select Sections → Live Document Preview → Report Settings).

Header:
- Title: "Report Generator – Case CC-101".
- Subtitle: "Generate structured investigation reports with evidence, analysis and network insights."
- Actions: "Saved Reports", "Report Templates", "Preview & Export".

Column 1 ("1. Select Report Type"):
- Vertical selection cards:
  - Investigation Summary (Active with blue glowing border) - "Overall case summary with key findings and links."
  - Financial Analysis Report - "Detailed money trail analysis with transactions."
  - Network Analysis Report - "Graph insights and entity relationships."
  - Evidence Compilation Report - "List of all uploaded evidence with extracted data."
  - Custom Report - "Choose sections and generate custom report."

Column 2 ("2. Select Sections"):
- Action: "Select All".
- Checkbox list with icons:
  ✓ Case Overview (Basic details, FIRs)
  ✓ Key Findings (Summary of important findings)
  ✓ Persons Involved (Main persons and relationships)
  ✓ Phone Numbers (Call records summary)
  ✓ Bank Accounts (Transaction summary and money trail)
  ✓ Locations (Important locations and movements)
  ✓ Network Graph (Entity relationship graph)
  ✓ AI Generated Insights (Patterns, risk indicators)
  ✓ Supporting Evidence (List of documents)
  ☐ Conclusion & Next Steps (Optional).

Column 3 ("Report Preview"):
- A4 Styled Document Sheet container with zoom controls (Page 1 / 8, 100% zoom):
  - Document Header: Case Connect AI logo, "Investigation Report - CONFIDENTIAL" red badge.
  - Report Title: "Case CC-101: Cyber Fraud Network - Investigation Summary Report".
  - Metadata Grid: Case ID, FIR Numbers, Station, Period, Generated Date, Generated By (Inspector Meera).
  - Executive Summary Section text.
  - Key Findings Bullet points.
  - Embedded SVG Visualizations inside preview: Mini entity network graph + Transaction summary bar chart.

Column 4 ("Report Settings"):
- File Format: PDF (Recommended) dropdown.
- Toggles: Include Graph Images (ON), Include Transaction Charts (ON), Include Evidence Annexure (ON).
- Page Orientation: A4 (Portrait) dropdown.
- Classification Marking: Confidential dropdown.
- Custom Notes textarea.
- Primary CTA: "Generate Report" (Gradient Blue/Purple button with PDF icon).
- "Recent Reports" download list (CC-101_Investigation_Report.pdf, CC-087_Financial_Analysis.pdf, CC-099_Network_Report.pdf).
```

---

### Module 11: Audit Log Screen
```text
Screen Title: Audit Log Screen
Type: Security, Compliance & System Audit Trail (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + Comprehensive Filter Bar + Left Main Audit Log Ledger + Right Activity Analytics (Donut Chart, Top Users, Trendline) + Bottom Critical Actions Alert.

Header:
- Title: "Audit Log – Case CC-101".
- Subtitle: "Track all system activities, user actions and data changes for transparency and accountability."
- Actions: "Export Logs", "Fullscreen".

Filter Bar:
- Date Range: "Last 30 days"
- User: "All Users"
- Action Type: "All Actions"
- Module: "All Modules"
- Case: "CC-101"
- Status: "All Status"
- Button: "Apply Filters", "Reset".

Left / Center Section ("Audit Logs - 256 entries"):
- Data Table:
  - Columns: Date & Time, User (with avatar & designation), Action (with icon), Module, Details, IP Address, Status, Action ("View").
  - Rows:
    - 12 Oct 2026, 10:32 AM | Inspector Meera | Uploaded File | Evidence | FIR_CC-087.pdf (12.4 MB) | 192.168.1.105 | Success
    - 12 Oct 2026, 10:28 AM | Inspector Meera | Generated Report | Reports | Case_Summary_CC-101.pdf | 192.168.1.105 | Success
    - 12 Oct 2026, 10:15 AM | Inspector Meera | Viewed Graph | Investigation Graph | Viewed network graph for CC-101 | 192.168.1.105 | Success
    - 11 Oct 2026, 04:21 PM | SI Arjun Kumar | Searched Entity | Master Profile | Search: +91 98765 43210 | 192.168.1.118 | Success
    - 11 Oct 2026, 03:50 PM | Inspector Meera | Viewed Money Trail | Money Trail | Account: AXIS XXXX3210 | 192.168.1.105 | Success
    - 10 Oct 2026, 11:12 AM | SI Arjun Kumar | Updated Case | Cases | Updated case details (CC-101) | 192.168.1.118 | Success
    - 09 Oct 2026, 06:30 PM | Admin Rajesh | Changed Settings | Settings | Updated user role: SI Arjun Kumar | 192.168.1.10 | Success.

Right Column (Analytics):
- "Activity Summary (Last 30 days)": Pure SVG Donut Chart with center label "256 Total Actions", colored slices for Evidence (27%), Investigation Graph (20%), Money Trail (15%), Reports (11%), Cases (10%), Settings (7%), Others (10%).
- "Top Users by Activity": Inspector Meera (128 actions), SI Arjun Kumar (76), Constable Priya (32), Admin Rajesh (20) with horizontal progress meters.
- "Top Action Types": File Upload, Graph View, Report Generation, Search Entity, Case Update.
- "System Activity Trend (Last 7 days)": Pure SVG glowing area/line curve chart showing daily action peaks.

Bottom Panel ("Recent Critical Actions"):
- Red alert strip:
  - Deleted File: Old_analysis.csv by Admin Rajesh
  - Accessed High-Risk Data: Money trail AXIS XXXX3210 by Inspector Meera
  - Changed User Role: Promoted SI Arjun to Investigator by Admin Rajesh.
```

---

### Module 12: Users and Roles Screen
```text
Screen Title: Users and Roles Screen
Type: Identity, Access Management & RBAC Administration (Desktop 100vh, Persistent Sidebar Navigation)
Layout: Persistent Sidebar + Header + 4 Role Metric Distribution Cards + Main User Directory Grid + Right Add User Form + Bottom Permissions Matrix & Activity Timeline.

Header:
- Title: "Users & Roles".
- Subtitle: "Manage system users, roles and permissions to ensure secure and controlled access."
- Action Button: "+ Add User" (Primary blue CTA).

Top Role Distribution Cards (4 Metric Cards with icons):
1. Administrator: "3 Users" - Full system access (Crown icon, red border accent)
2. Investigator: "12 Users" - Case investigation access (Shield icon, blue border accent)
3. Analyst: "8 Users" - Data analysis and reporting (Bar chart icon, purple border accent)
4. Viewer: "6 Users" - Read-only access (Eye icon, green border accent).

Main Center-Left Section:
- "System Users (29)":
  - Search input ("Search users by name, email or designation...") + "Filters" button.
  - Data Grid:
    - Columns: #, Name, Designation, Role (Colored badge), Department, Email, Status (Active badge), Last Active, Action ("...").
    - Rows:
      1. Inspector Meera | Inspector | Administrator (Red badge) | Cyber Cell | meera@delhipolice.gov.in | Active | 12 Oct 2026, 10:32 AM
      2. SI Arjun Kumar | Sub Inspector | Investigator (Blue badge) | Cyber Cell | arjun@delhipolice.gov.in | Active | 12 Oct 2026, 09:15 AM
      3. Constable Priya | Constable | Viewer (Green badge) | Cyber Cell | priya@delhipolice.gov.in | Active | 11 Oct 2026, 05:42 PM
      4. Analyst Rohan | Data Analyst | Analyst (Purple badge) | Economic Offences | rohan@delhipolice.gov.in | Active | 12 Oct 2026, 08:20 AM
      5. Admin Rajesh | System Admin | Administrator (Red badge) | IT Department | rajesh@delhipolice.gov.in | Active | 12 Oct 2026, 06:45 AM.

Right Side Panel ("Add New User"):
- Provision fresh credentials and role allocations form:
  - Full Name input
  - Email Address input (@delhipolice.gov.in)
  - Designation input
  - Role dropdown selector (Administrator, Investigator, Analyst, Viewer)
  - Department dropdown selector (Cyber Cell, Economic Offences, Crime Branch, IT)
  - Phone Number input (+91 ...)
  - Action Buttons: "Cancel" (Ghost button) and "Create User" (Blue CTA).

Bottom Split Section:
- Left: "Role Permissions" Matrix:
  - Selector: "Select Role: Investigator"
  - Table: Module / Feature, Administrator, Investigator, Analyst, Viewer checkmark/cross matrix:
    - Access Cases (Admin ✓, Investigator ✓, Analyst ✓, Viewer ✕)
    - Upload Evidence (Admin ✓, Investigator ✓, Analyst ✕, Viewer ✕)
    - View Investigation Graph (Admin ✓, Investigator ✓, Analyst ✓, Viewer ✓)
    - Access Money Trail (Admin ✓, Investigator ✓, Analyst ✓, Viewer ✕)
    - View Master Profiles (Admin ✓, Investigator ✓, Analyst ✓, Viewer ✓)
    - Use Lead Advisor (Admin ✓, Investigator ✓, Analyst ✕, Viewer ✕)
    - Generate Reports (Admin ✓, Investigator ✓, Analyst ✓, Viewer ✕)
    - View Audit Logs (Admin ✓, Investigator ✕, Analyst ✕, Viewer ✕)
    - Manage Users & Roles (Admin ✓, Investigator ✕, Analyst ✕, Viewer ✕)
    - System Settings (Admin ✓, Investigator ✕, Analyst ✕, Viewer ✕).
- Right: "User Activity Overview" (Last 30 days):
  - Horizontal progress indicators for Admin Actions (156), Case Updates (124), Evidence Uploads (98), Report Generation (62), Graph Analysis (54).
  - Recent Role Changes log.
```
