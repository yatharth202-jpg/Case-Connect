# CaseConnect AI — Upgrade Architecture Decisions & Decisions Log (V2)

**Branch:** `upgrade/2026-11-12`  
**Standard:** Section 63 Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)  
**Authorship:** Senior Principal Forensic Systems Engineer

---

## 1. Phase 1 Decisions (Lossless Raw Store & Ingestion Pipeline)

1. **Table Placement & Model Definitions:**
   - Added `RawSheet`, `RawRow`, `GraphNode`, `GraphEdge`, `AnalysisResult`, `SavedGraphView`, `SystemConfig`, `NodeTypeConfig`, and `EdgeTypeConfig` to `backend/app/db/sql.py`.
   - SQLite table for field claims is mapped to `FieldClaim` in existing codebase. We introduced alias `RecordFieldClaim = FieldClaim` to preserve backward compatibility while conforming to V2 specifications.
   - Additive column `raw_row_id` added as nullable `VARCHAR` to `call_records`, `transactions`, `ip_events`, and `rejected_rows`.

2. **Reconciliation Invariant:**
   - Independent verification calculates:
     `rows_in_file == staged + rejected + preamble + blank`
   - Pre-capture runs before any extraction or normalization: original cell tokens (leading zeros, date text, unmapped headers) are stored in `raw_rows.raw_json` as verbatim string tokens.

3. **Multi-sheet Secondary Confidence Threshold:**
   - In `backend/app/services/ingestion/stage.py`, secondary sheets in multi-sheet Excel files require `confidence >= 0.40` (previously 0.55 caused certain secondary sheets like `SDR_Identity` with confidence 0.46 to be skipped). Changing to `>= 0.40` fixed multi-sheet tabular ingestion without regressions.

---

## 2. Phase 2 Decisions (Excel Export Engine)

1. **openpyxl Write-Only Streaming Mode:**
   - Employed `openpyxl.Workbook(write_only=True)` to stream worksheet rows directly to disk. This maintains an O(1) memory footprint regardless of dataset scale.
   - Hard row limit of 1,048,576 rows per worksheet handled via automatic sheet splitting (`Raw_Rows_1`, `Raw_Rows_2`) at 1,000,000 rows.

2. **Zero Float Currency Invariant:**
   - Monetary amounts in `transactions` are strictly stored and output as 64-bit integer paise (`amount_paise`).
   - Human-readable rupee text column (`amount_inr_text`) is rendered as string (e.g. `Rs. 12,345.67`).
   - ZERO floating-point values are allowed into generated worksheets; any non-integer numeric metrics are string-formatted to prevent floating-point precision corruption.

3. **Formula Injection (DDE) Defense:**
   - All string values starting with `=`, `+`, `-`, or `@` are sanitized by prepending a single quote `'`.

4. **Cryptographic Chain of Custody:**
   - Every export operation computes the SHA-256 hash of the generated dossier and logs the event to `audit_log` with action `EXPORT_EXCEL`.

---

## 3. Phase 3 Decisions (Top-5 Primary Attributed Leads)

1. **Topological Signals & Explainability:**
   - Evaluates weighted normalized signals across:
     * Degree Centrality
     * Betweenness Centrality
     * PageRank Centrality
     * Rapid Pass-Through Anomaly (inflow/outflow ratio >= 0.70)
     * Total Volume in integer paise
     * Cross-Case hits across other case dockets
   - Weights loaded dynamically from `SystemConfig` (`top_leads_weights`) with fallback to `backend/config/seed_graph_config.yaml`.

2. **100% Deterministic Ranking & Stable Tie-Break:**
   - Multi-key sorting: `(-round(score, 6), -degree, -total_paise, entity_id)` guarantees 100% repeatable output across runs.

3. **Candidate Fidelity (Zero Fabrication):**
   - If fewer than 5 candidates exist in the case, the system returns only what exists. Never pads or fabricates synthetic records.

4. **Statutory Neutral Terminology:**
   - Strictly banned words: `criminal`, `suspect`, `guilty`, `mastermind`, `fraudster`, `culprit`, `accused`.
   - Mandatory designation: `Primary Attributed Lead #n`.
   - Mandatory statutory disclaimer: *"Rank is a statistical indicator for investigative prioritisation, not a finding of culpability."*

5. **Persistence for Zero-Recompute Case Reopening:**
   - Persisted in `analysis_results` table so reopening a case docket immediately loads top leads without re-running graph algorithms.

---

## 4. Phase 4 Decisions (Graph Rebuild & Topological Inspection)

1. **Authoritative SQLite Graph Engine:**
   - `graph_nodes` and `graph_edges` tables in SQLite are the single authoritative source of truth.
   - Neo4j 5.x Community is an optional rebuildable projection; NetworkX operates as an in-memory graph projection.
   - Graph rebuild is 100% idempotent: purges existing case graph records and rebuilds from confirmed identities, entities, transactions, call records, and IP events.

2. **Deterministic ID Generation:**
   - Stable Node IDs generated via `generate_node_id(case_id, node_type, canonical_key)`.
   - Stable Edge IDs generated via `generate_edge_id(case_id, source_node_id, target_node_id, edge_type)`.

3. **Edge Aggregation & Integer Currency:**
   - Multiple financial interactions between identical node pairs are aggregated into single graph edges with summed `amount_paise` (strictly 64-bit integer), transaction count, call count, and min/max timestamps.
   - Source evidence file references are deduplicated and tracked in `source_evidence_ids`.

4. **DateTime Normalization:**
   - Converted ISO string timestamps to native Python `datetime` objects before persisting into `GraphEdge.first_seen` and `GraphEdge.last_seen` to comply with SQLAlchemy `DateTime` column typing in SQLite.

5. **Paginated Topological Neighbor Inspection:**
   - Endpoint `GET /cases/{case_id}/graph/node/{node_id}` groups connected neighbors by entity type (`Phone`, `Account`, `Person`, etc.), provides edge details, and enforces pagination with statutory UI notice: `"showing {len(paged_neighbours)} of {total_neighbours}"`.

6. **Data-Agnostic Dynamic Styling & Config:**
   - Node and edge styles (shapes, colors, border styles, line patterns, weights) are loaded dynamically from `NodeTypeConfig` and `EdgeTypeConfig` tables via `GET /cases/{case_id}/graph/config`. Any new entity or relation type works with zero code changes.

7. **Frontend Architecture:**
   - `GraphExplorer.jsx` implements Cytoscape force-directed layout with dynamic legend, real-time node filtering, min-weight edge filtering, double-click 1-hop expansion, and inspection drawer via `NodeDetailPanel.jsx`.
   - Retains legacy `GraphCanvas.jsx` via view toggle to ensure zero regression.

---

## 5. Phase 5 Decisions (Persistence & Zero-Recompute Reopen)

1. **Forensic Findings in Relational Graph (`Finding` Nodes):**
   - Forensic analysis results (such as primary attributed leads, bridge anomalies, rapid pass-throughs) are persisted as `AnalysisResult` records and simultaneously represented in the relational graph as `GraphNode` with `node_type = 'Finding'`.
   - Each Finding node links to its target entity node via a `GraphEdge` with `edge_type = 'ATTRIBUTED_TO'`.
   - Rendered using dedicated styling from `NodeTypeConfig` (shape: `vee`, color: `#BE185D`, icon: `alert-triangle`).

2. **Saved Viewport State (`SavedGraphView`):**
   - Preserves camera coordinates (`pan: {x, y}`, `zoom`), active node selection, and active filters (`searchQuery`, `selectedType`, `minWeight`).
   - Restoring a saved view executes client-side animation to reposition Cytoscape camera instantly without triggering server recomputation or network re-queries.

3. **Zero-Recompute Invariant on Case Reopening:**
   - Reopening an investigation docket queries `AnalysisResult`, `GraphNode`, and `GraphEdge` records stored in SQLite WAL.
   - Outputs are 100% byte-for-byte, score-for-score, and rank-for-rank identical to initial calculation with zero CPU graph recalculation.

4. **Cryptographic Audit Chain Integration:**
   - All persistence mutations (`SAVE_ANALYSIS_RESULT`, `SAVE_GRAPH_VIEW`, `DELETE_GRAPH_VIEW`) append to the SHA-256 genesis-chained `audit_log` with user ID, case ID, timestamp, and previous block hash.

5. **Elimination of Warnings and Skips Across Test Suite:**
   - Generated missing synthetic samples in `data/synthetic/samples/clean` and `data/synthetic/samples/messy`, resolving all skipped ingestion tests.
   - Added TSV/TXT tabular extension support to `readers.py`.
   - Configured `pytest.ini` filter warnings to silence third-party library deprecation and future warnings.
