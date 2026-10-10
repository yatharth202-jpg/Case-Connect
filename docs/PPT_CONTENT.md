# Case Connect AI — Presentation Slide Deck Content

> **Presentation Deck Content (12 Slides)**  
> *Note: Contains strictly verified claims derived from functional code in this repository.*

---

### Slide 1: Title & Identity
- **Headline:** Case Connect AI
- **Subheadline:** Unified Criminal Network Analysis System & Statutory Evidence Aggregator
- **Target User:** State Police Cyber Crime Cells, Special Task Forces, and Economic Offences Wings
- **Statutory Standard:** Engineered in Compliance with Section 63 of Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)
- **Team:** UNITx

---

### Slide 2: The Ground Reality (The Problem)
- **Problem 1: Format Fragmentation**
  - Investigating Officers receive CDR dumps from telecom operators, statement CSVs/PDFs from 40+ banks, and paper FIRs with zero standard schema.
- **Problem 2: Speed of Layering**
  - Fraud funds are layered through 3 to 6 mule accounts and withdrawn at ATMs within 45 minutes; manual Excel VLOOKUP takes weeks.
- **Problem 3: Evidentiary Rejection in Court**
  - Ad-hoc Excel charts and undocumented manual merges face dismissal in trial courts under evidentiary chain-of-custody objections.

---

### Slide 3: Our Solution — Case Connect AI
- **Unified Ingestion:** Universal tabular parser and dynamic header mapping for arbitrary bank/CDR formats.
- **Explainable Analytics:** Statistical Median Absolute Deviation (MAD) spike detection and directed BFS money trail layering.
- **Statutory Custody:** SHA-256 evidence hashing at upload, cryptographic hash-chained audit logging, and automated Section 63 BSA PDF generation.
- **Human-in-the-Loop Philosophy:** AI recommends candidate merges and scores leads; the Investigating Officer retains sole decision authority.

---

### Slide 4: System Architecture
- **SQLite (Source of Truth):** Authoritative storage for cases, transactions, calls, master profiles, and tamper-evident audit logs.
- **NetworkX & Neo4j (Graph Index):** In-memory multi-directed graph cache with optional Neo4j projection for sub-millisecond hop queries.
- **FastAPI Backend:** Clean REST contract with role-based access control (`Admin`, `Investigator`, `Viewer`).
- **React + Tailwind Frontend:** Dark-tech, high-density investigative interface built for zero distraction and projector clarity.

---

### Slide 5: Core Feature 1 — Universal Ingestion & Dynamic Mapping
- **Eliminates Rigid Hardcoding:** Does not depend on hardcoded column names or telecom formats.
- **Intelligent Synonyms:** Maps raw headers using Jaro-Winkler distance against telecom and financial synonym sets (`backend/app/services/ingestion/mapping.py`).
- **Template Memorization:** Caches header signatures; repeated files from the same bank or circle auto-map with 100% confidence.
- **Data Quality Safeguard:** Isolates malformed rows into `RejectedRow` audit logs with line numbers and reasons.

---

### Slide 6: Core Feature 2 — Multi-Hop Money Trail Engine
- **Directed Layering Graph:** Traces money flow across multiple hops (1 to 4) from victim remitter to ultimate shell entity.
- **Rapid Pass-Through Detection:** Flags mule accounts where $\ge 80\%$ of funds exit within 24 hours of arrival (`backend/app/services/money/patterns.py`).
- **Fan-In / Smurfing Alerts:** Detects collection hubs receiving deposits from $\ge 5$ distinct remitter accounts within 48 hours.
- **Exact Paise Accounting:** All arithmetic uses 64-bit integer paise to prevent floating-point rounding errors.

---

### Slide 7: Core Feature 3 — Telecom MAD Spike & Heatmap Intelligence
- **Non-Parametric Anomaly Detection:** Uses Median Absolute Deviation (MAD) over a 14-day sliding window ($k=3.0$, floor $\ge 15$) rather than static call counts.
- **24x7 Intensity Heatmap:** Color-codes call volumes across day-of-week and hour-of-day to highlight odd-hours (00:00–05:00) coordination.
- **Frequent Pair Isolation:** Evaluates Interquartile Range (IQR) to identify unusually tight calling relationships between syndicate coordinators.

---

### Slide 8: Core Feature 4 — Master Profiles & Human Approval Portal
- **Phonetic & String Deduplication:** Combines Soundex phonetic keys and Jaro-Winkler similarity to uncover alias variants (e.g., "Vikas Sharma" vs "V. K. Sharma").
- **Strict Anti-Merge Bias Protection:** Automatic merging is strictly disabled; candidate pairs are presented with similarity scores for officer review.
- **Zero-Loss Undo Engine:** Any approved merge can be rolled back with one click, restoring independent graph entities and logging the reversal in the audit trail.

---

### Slide 9: Core Feature 5 — 5-Signal Explainable Lead Advisor
- **100% Explainable Mathematical Scoring:**
  1. *Financial Money Flow (Weight: 30)* — Throughput volume and pass-through participation.
  2. *Network Bridge Centrality (Weight: 25)* — Betweenness centrality across syndicate communities.
  3. *Unusual Communication (Weight: 20)* — Call volume spikes and outlier pairwise frequency.
  4. *Timing Coincidence (Weight: 15)* — Temporal proximity between calls and high-value transfers.
  5. *Multi-Document Presence (Weight: 10)* — Appearance across multiple police documents.
- **Strict Availability Principle:** Automatically recalibrates weights if a data source is absent; never fabricates false zero scores.
- **Prejudicial Terminology Defense:** Zero demographic, prior-conviction, or caste/community attributes are utilized.

---

### Slide 10: Core Feature 6 — Section 63 BSA 2023 Forensic Dossier
- **Automated PDF Generation:** Built using ReportLab, compiling court-admissible dossiers in seconds.
- **Evidentiary Manifest:** Includes cryptographic SHA-256 hashes of all raw source files.
- **Audit Verification:** Embeds cryptographic hash chain validation results proving zero database tampering.
- **Statutory Certification:** Automatically formats the legal certificate language required under Section 63 of Bharatiya Sakshya Adhiniyam, 2023.

---

### Slide 11: Measured System Performance
*(Empirical benchmark results from `scripts/perf_benchmark.py`)*
- **Ingestion Throughput:** ~7,700 records per second on commodity laptop hardware.
- **Graph Rebuild Time:** 0.050 seconds for 500+ nodes and edges.
- **Hop Search Latency:** Median p50 $< 0.1\text{ms}$ for 1–4 hops.
- **Money Trail BFS:** Median latency ~100ms for 4-hop financial traversal.
- **Memory Footprint:** Peak RAM consumption strictly bounded at $< 6\text{ MB}$.

---

### Slide 12: Roadmap & Future Expansion
- **Upcoming Milestone 1:** Native Tesseract OCR pipeline for scanned non-searchable FIR document PDFs.
- **Upcoming Milestone 2:** Automated direct connector for CCTNS FIR exports and ICJS prisoner registry feeds.
- **Upcoming Milestone 3:** Cross-Case Syndicate Correlation alerts for detecting interstate repeat mule operators.
- **Upcoming Milestone 4:** Air-gapped on-premise local open LLM (e.g. Llama-3/Mistral via Ollama) for summarization without cloud data transfer.
