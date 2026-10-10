# Case Connect AI — Screen Map & Data Wiring

This document defines the route, components, API endpoints, required data fields, interactions, and empty/loading states for every screen in the application.

---

### 1. Login Screen (`/login`)
* **Components**: `HeroBranding`, `LoginForm`, `SSOButtons`, `StatusFooter`.
* **Endpoints**: `POST /auth/login`.
* **Fields**: `username`, `password`.
* **Interactions**: Submit credentials, toggle password visibility, department SSO redirection.
* **States**:
  - Loading: Button spinner `Signing in...`.
  - Error: Inline crimson alert "Invalid username or password".

---

### 2. Role Selection Wizard (`/select-role`)
* **Components**: `StepIndicator`, `RoleCardGrid` (Investigator, Supervisor, Admin).
* **Endpoints**: `GET /auth/me`, `PATCH /users/{id}` (if role change permitted).
* **Interactions**: Select role card, confirm access, proceed to dashboard.

---

### 3. Dashboard (`/dashboard`)
* **Components**: `Sidebar`, `TopBar`, `KpiStatCards` (Total Cases, Active Investigations, Entities, Bank Accounts), `InteractiveMapPreview`, `RecentCasesTable`, `AIInsightsFeed`.
* **Endpoints**:
  - `GET /cases`
  - `GET /cases/{id}/analytics/overview`
  - `GET /cases/{id}/alerts`
* **States**:
  - Empty: When no cases exist, KPI cards show `0`, and table shows `No cases found. Create your first case to begin`.
  - Loading: Skeleton pulse blocks for cards and tables.

---

### 4. Case Management Hub (`/cases`)
* **Components**: `CaseSearchFilterBar`, `NewCaseModal`, `CaseCardGrid`, `Pagination`.
* **Endpoints**:
  - `GET /cases`
  - `POST /cases`
* **Fields**: `title`, `description`, `priority`, `status`, `assigned_officers`.
* **Interactions**: Click case to open workspace (`/cases/:id`), create case modal with priority selector.

---

### 5. Evidence Upload & Auto-Mapping (`/cases/:id/evidence`)
* **Components**: `DropzoneUploader`, `FileQueueTable`, `FilePreviewModal`, `ColumnMappingEditor`, `IngestJobProgress`.
* **Endpoints**:
  - `POST /cases/{id}/evidence` (multipart)
  - `GET /evidence/{id}`
  - `POST /evidence/{id}/mapping`
  - `POST /evidence/{id}/ingest`
  - `GET /jobs/{id}`
* **Fields**: `file`, `detected_type`, `suggested_mapping`, `sha256`, `preview_rows`.
* **Interactions**: Drag & drop files, review detected type and column dropdowns, adjust mappings, click "Start Ingestion", watch real-time step progress card.
* **States**:
  - Empty: "Drag and drop CDR (CSV/Excel), Bank statements, or FIR (PDF/Text) files here".
  - Loading: Progress bar (0..100%) with step labels.

---

### 6. Investigation Graph Explorer (`/cases/:id/graph`)
* **Components**: `OmniSearchBar`, `CandidatePickerDropdown`, `HopSelector` (1, 2, 3, 4), `ViewModeToggle` (Entity vs Detail), `CytoscapeCanvas`, `NodeDetailDrawer`, `ProvenanceCard`, `AssignOwnerModal`.
* **Endpoints**:
  - `GET /cases/{id}/graph/search`
  - `GET /cases/{id}/graph/path`
  - `POST /cases/{id}/links`
  - `DELETE /cases/{id}/links/{id}`
* **Fields**: `nodes`, `edges`, `truncated`, `meta`.
* **Interactions**: Search person or number, click hop button to expand, drag nodes, click node to view details panel, select 2 nodes for shortest path, click edge to inspect provenance modal.
* **States**:
  - Empty: "Upload evidence to generate the investigation graph."
  - Loading: Cytoscape spinner with "Querying graph projection...".

---

### 7. Money Trail Explorer (`/cases/:id/money-trail`)
* **Components**: `AccountSelector`, `QuantileFilterChips` (p50, p75, p90, p99), `HopsSlider`, `DirectionToggle` (In / Out / Both), `DirectedTrailCanvas`, `AccountTotalsSidebar`, `TransactionsTable`, `ExportCsvButton`.
* **Endpoints**:
  - `GET /cases/{id}/money-trail`
  - `GET /cases/{id}/analytics/txn-volume`
* **Fields**: `nodes`, `edges`, `totals` (inflow, outflow, throughput), `flags` (fan-in, pass-through).
* **Interactions**: Select bank account, toggle amount quantile chips, filter by date, inspect grey dashed lines for below-threshold transfers.
* **States**:
  - Empty: "No financial transaction data uploaded for this case."

---

### 8. AI Lead Advisor (`/cases/:id/leads`)
* **Components**: `LeadCardList`, `PriorityBadge` (HIGH, MEDIUM, LOW), `SignalBreakdownBars`, `PatternMatchCard`, `MissingDataChecklist`, `DecisionActionButtons` (Accept / Reject / Need More Data).
* **Endpoints**:
  - `GET /cases/{id}/leads`
  - `GET /cases/{id}/entities/{entityId}/why`
  - `POST /cases/{id}/leads/{leadId}/decision`
* **Fields**: `priority`, `confidence`, `signals` (money, bridge, comms, timing, docs), `matched_pattern`, `missing_data`.
* **Interactions**: Filter leads by level, click lead to expand full mathematical explanation, submit officer decision with investigator notes.
* **States**:
  - Empty: "No leads generated. Ingest evidence files to compute network priorities."

---

### 9. Cross-FIR Master Profile (`/cases/:id/profiles/:profileId`)
* **Components**: `ProfileHeroHeader`, `AliasChipsList`, `LinkedIdentitiesGrid` (Phones, Accounts, Vehicles), `AssociatedFIRsTable`, `ChronologicalTimelineMini`, `ProvenanceDrawer`.
* **Endpoints**:
  - `GET /cases/{id}/profiles/{profileId}`
  - `GET /cases/{id}/timeline`
* **Fields**: `name`, `also_known_as`, `phones`, `accounts`, `vehicles`, `firs`, `timeline`.
* **Interactions**: Click alias to view source FIR page, expand provenance for any fact.

---

### 10. Cryptographic Audit Trail (`/audit`)
* **Components**: `AuditFilterBar`, `AuditLogTable`, `HashChainStatusBanner`, `VerifyLogButton`, `TamperAlertBanner`.
* **Endpoints**:
  - `GET /audit`
  - `GET /audit/verify`
* **Fields**: `id`, `ts`, `user_id`, `action`, `object_type`, `object_id`, `hash`, `prev_hash`.
* **Interactions**: Click "Verify Integrity" to recalculate SHA-256 chain from genesis block; displays verification count or flags broken row ID in crimson.

---

### 11. Investigation Report Generator (`/cases/:id/reports`)
* **Components**: `SectionCheckboxGrid`, `ComplianceBadge` (Section 63 BSA 2023), `GeneratePdfButton`, `ReportHistoryTable`, `DownloadPdfButton`.
* **Endpoints**:
  - `POST /cases/{id}/report`
  - `GET /cases/{id}/reports`
  - `GET /reports/{id}/download`
* **Interactions**: Select sections to include, click "Generate Court Report", download cryptographically stamped PDF.
