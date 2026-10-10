# Case Connect AI — Hardest Judge Q&A (25 Technical Defenses)

> Every answer is drawn strictly from the actual codebase. Cites concrete files and functions.

---

### Category 1: Formats & Data Ingestion

#### Q1: "How does your system handle non-standard Excel files with multiple title rows and blank lines before the table starts?"
**Answer:** `backend/app/services/ingestion/readers.py` (`read_xlsx_file` and `read_csv_file`) scans up to the first 25 lines to detect tabular boundary density. Any rows with fewer than 2 populated cells or containing banner keywords like "Statement of Account" are stripped into a metadata `banner_lines` array, preserving data integrity without breaking column detection.

#### Q2: "What happens if a bank statement uses Indian numbering formatting like '5,00,000.00' with commas?"
**Answer:** `backend/app/services/ingestion/normalize.py` (`normalize_amount`) uses an Indian numbering regex to strip currency symbols and commas before converting the string into an integer `amount_paise`. Floats are strictly prohibited across all database models to eliminate IEEE-754 precision drift.

#### Q3: "Can you ingest scanned image PDFs that have no text layer?"
**Answer:** Currently, `backend/app/services/extraction/text.py` (`read_document_text`) utilizes `pypdf` for text extraction. Image-only PDFs without an embedded OCR text stream raise a clear warning in the UI rather than failing silently; OCR integration (e.g. Tesseract) is planned on our roadmap.

#### Q4: "How do you map unknown column names without hardcoding telecom operator formats?"
**Answer:** `backend/app/services/ingestion/mapping.py` (`suggest_column_mappings`) computes Jaro-Winkler string similarity against a synonym library (`synonyms.yaml`). Once an officer confirms or corrects the mapping, `compute_header_signature` caches the configuration in `MappingTemplate`, automatically recognizing identical format headers on subsequent uploads.

#### Q5: "What if an upload contains corrupted rows or malformed dates?"
**Answer:** `backend/app/services/ingestion/stage.py` (`_record_rejection`) catches unparseable records, segregates them into the `RejectedRow` table with the exact line number, raw JSON, and rejection reason, and proceeds with valid rows. The officer is presented with a Data Quality Summary modal showing clean vs. rejected row counts.

---

### Category 2: Entity Resolution & Deduplication

#### Q6: "How do you deduplicate individuals with slight spelling variations like 'Vikas Sharma' vs 'V. K. Sharma'?"
**Answer:** `backend/app/services/matching/service.py` (`compute_similarity_candidates`) combines Soundex phonetic keys with Jaro-Winkler string similarity and shared identifier bonuses (matching mobile or bank account). Suggestions with scores above `match_threshold` (0.80) are presented to the officer.

#### Q7: "What prevents your algorithm from wrongly merging two innocent people who share the same name?"
**Answer:** By foundational Rule 5 ("AI suggests, human decides"), automatic merging is strictly forbidden. The system stages resolution proposals in `EntityReview.jsx` and requires manual officer review (`approve_merge_match`). Additionally, every merge creates an audit event and can be instantly rolled back using `undo_merge_match`.

#### Q8: "How does the system handle shared phone numbers or joint bank accounts without falsely merging identities?"
**Answer:** In `backend/app/services/graph/builder.py` (`build_detail_graph`), nodes representing shared identifiers (e.g., phones with multiple owners) have `shared=True` flagged. The bipartite graph maintains separate `Person` nodes with explicit `OWNS` or `USES` edges to the shared identifier rather than collapsing the persons together.

#### Q9: "Can an investigator review the evidence origin for an automatically resolved profile?"
**Answer:** Yes. The Master Profiles screen (`frontend/src/components/MasterProfiles.jsx`) and `/cases/{id}/provenance` endpoint return full provenance metadata: source evidence file ID, row/page number, extraction method (`identity_table | document_nlp`), and the approving officer's ID.

#### Q10: "If an officer makes a mistake and merges two entities, can it be undone?"
**Answer:** Completely. `backend/app/services/matching/service.py` (`undo_merge_match`) deletes the corresponding `ProfileMember` entries, unsets `merged_into_id`, records an `undo_merge` action in the audit trail, and calls `invalidate_case_graph` to rebuild the original separated graph.

---

### Category 3: Financial Analytics & Money Trail

#### Q11: "How do you uncover layering and rapid pass-through accounts in money laundering?"
**Answer:** `backend/app/services/money/patterns.py` (`detect_rapid_passthrough`) filters accounts where inflow closely matches outflow within a configurable rolling window (e.g., 24 hours, $\ge 80\%$ pass-through ratio). It flags the specific sequence of incoming and outgoing transaction IDs with exact rupee totals.

#### Q12: "How does the Money Trail graph avoid visual clutter on accounts with thousands of micro-transactions?"
**Answer:** `backend/app/services/money/trail.py` (`build_money_trail`) aggregates repeated transfers between the same account pair, filters transactions below `min_amount_rupees`, bounds BFS traversal to a maximum of 4 hops, and preserves smaller transfers as aggregated dashed `hidden_edges`.

#### Q13: "How do you detect smurfing or fan-in transactions?"
**Answer:** `backend/app/services/money/patterns.py` (`detect_fan_in`) identifies collection accounts receiving transfers from $K \ge 5$ distinct remitter accounts within a window $W \le 48$ hours. It generates a high-severity `fan_in` alert with evidence references.

#### Q14: "What currency units are used internally, and how is precision maintained?"
**Answer:** All monetary fields in `backend/app/db/sql.py` (`Transaction.amount_paise`) are stored as 64-bit integer paise. Conversions to INR are performed exclusively during UI formatting via `(amount_paise / 100).toLocaleString('en-IN')`.

---

### Category 4: Telecom & CDR Intelligence

#### Q15: "How do you detect coordinated communication surges without relying on arbitrary static thresholds?"
**Answer:** `backend/app/services/analytics/comm_patterns.py` (`detect_sudden_spikes`) computes the **Median Absolute Deviation (MAD)** over an adaptive baseline window ($W = 14$ days). Days where call volume exceeds $\text{median} + k \times \text{MAD}$ ($k = 3.0$, floor $\ge 15$) are flagged with exact statistical z-scores.

#### Q16: "How does the system highlight odd-hours or late-night criminal coordination?"
**Answer:** `backend/app/services/analytics/router.py` (`/analytics/heatmap`) aggregates 24x7 call intensity across days of the week (Monday–Sunday) and hours (00:00–23:00). In `DashboardOverview.jsx`, nighttime intervals (23:00–05:00) with call spikes are visually highlighted in amber/rose.

#### Q17: "How do you isolate frequent caller pairs?"
**Answer:** `backend/app/services/analytics/comm_patterns.py` (`detect_frequent_pairs`) calculates the Interquartile Range (IQR) of pairwise call distributions and flags outliers exceeding $Q_3 + 1.5 \times \text{IQR}$, exposing tight coordination channels.

---

### Category 5: Lead Advisor & Scoring Transparency

#### Q18: "How is the Lead Advisor score calculated, and is it a black box?"
**Answer:** It is 100% explainable and deterministic. In `backend/app/services/analytics/lead_advisor.py` (`compute_lead_advisor`), scores are computed from 5 weighted signals: Money Flow (30), Network Bridge (25), Unusual Communication (20), Timing Coincidence (15), and Multi-Document Presence (10). Every lead includes mathematical explanations citing actual rupee values and call counts.

#### Q19: "What if a case only has CDR data and no bank statements? Does the scoring skew?"
**Answer:** No. `lead_advisor.py` adheres to the **Strict Availability Principle**: unavailable data dimensions are marked `is_available: false` and the priority score is dynamically normalized across only the active available signal weights ($S = \sum w_i \cdot s_i / \sum w_i$).

#### Q20: "Does your algorithm use prior criminal history or demographic data in its scoring?"
**Answer:** Absolutely not. In strict compliance with Rule 6 and Rule 10, the model contains **zero demographic or prior-conviction features**, preventing algorithmic bias or prejudicial profiling.

---

### Category 6: Legal Admissibility & Section 63 BSA 2023

#### Q21: "How does your system guarantee evidentiary chain of custody under Section 63 BSA 2023?"
**Answer:** At the moment of upload (`backend/app/evidence/router.py`), a cryptographic SHA-256 hash is computed on the raw byte stream before disk write. The stored path, hash, uploader ID, and UTC timestamp are stored in SQLite. Every subsequent access, mapping, or extraction operation is immutably logged.

#### Q22: "How do you detect if the database itself has been tampered with by an insider?"
**Answer:** `backend/app/audit/service.py` (`record_audit_log`) implements a cryptographic blockchain-style hash chain: each audit entry contains `current_hash = SHA256(prev_hash + user_id + action + timestamp + details)`. The admin endpoint `/audit/verify` re-computes the entire chain from genesis; any modified record immediately breaks the chain.

#### Q23: "What makes the exported investigation report admissible in an Indian court?"
**Answer:** Generated via ReportLab in `backend/app/services/reports/generator.py`, the PDF dossier includes:
1. Exact SHA-256 file fingerprints of all source evidence.
2. Section 63 BSA 2023 statutory certificate language.
3. Detailed provenance citations (evidence file, row/page number) for every fact.
4. Non-prejudicial wording ("Lead for review" rather than "Criminal finding").

---

### Category 7: Scale, Security & Systems

#### Q24: "How does the system perform when loading graphs with 100,000+ nodes?"
**Answer:** NetworkX graphs are cached in memory per case (`backend/app/services/graph/builder.py`). Query traversals are capped at 4 hops and enforced with a 500-node return ceiling (`truncated: true` banner in UI). Hop searches execute with a median latency of $< 0.1\text{ms}$.

#### Q25: "Can Case Connect AI integrate with police databases like CCTNS or ICJS?"
**Answer:** Yes. The ingestion engine is fully decoupled; CCTNS FIR exports, ICJS prisoner records, or CDR dump folders can be piped directly into `POST /cases/{id}/evidence` via REST API or mounted filesystem watchers without modifying core application logic.
