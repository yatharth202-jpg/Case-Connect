# Case Connect AI — File Probing & Ingestion Diagnostic Report

This report documents the performance of the universal ingestion engine against external and messy file structures generated during Phase 1.

---

### 1. Evaluated Test Sets

| Format | File Tested | Header Structure | Detected Type | Confidence | Auto-Mapped Columns |
|---|---|---|---|:---:|:---:|
| **Clean Tabular** | `data/synthetic/samples/clean/cdr.csv` | Single clean header | `cdr` | 100% | 6 / 6 (100%) |
| **Clean Banking** | `data/synthetic/samples/clean/bank_transactions.csv` | Standard tabular | `bank_transactions` | 100% | 8 / 8 (100%) |
| **Messy Excel CDR** | `data/synthetic/samples/messy/cdr_messy.xlsx` | 3 banner rows, A-Party/B-Party, MOC/MTC | `cdr` | 98% | 6 / 6 (100%) |
| **Messy Banking CSV** | `data/synthetic/samples/messy/bank_messy.csv` | 2 title banners, Indian commas, cp1252 | `bank_transactions` | 95% | 6 / 6 (100%) |
| **Single Account Statement** | `data/synthetic/samples/statement/statement_*.csv` | Account banner, debit/credit/narration | `bank_statement` | 92% | 5 / 5 (100%) |
| **PaySim Time-Step** | `data/synthetic/samples/paysim/paysim_transactions.csv` | Step, nameOrig, nameDest, amount | `bank_transactions` | 90% | 8 / 10 (80%) |

---

### 2. Core Diagnostic Findings

1. **Banner Row Handling**:
   - The scanner correctly skipped 2–4 title banner rows in `cdr_messy.xlsx` and `bank_messy.csv`.
   - In statement files, account numbers embedded in banner lines (`Account No: ...`) are extracted automatically without manual entry.

2. **Encoding Auto-Detection**:
   - Files encoded with `CP1252` and `UTF-8-SIG` are decoded seamlessly without raising `UnicodeDecodeError`.

3. **Narration Extraction (Rule 1)**:
   - Structured counterparty VPAs (e.g., `MeghaBa@okhdfc`) and NEFT UTR codes are extracted from messy free-text narration strings via `narration_patterns.yaml`.
   - Cash / ATM transactions without an extractable beneficiary are staged as `unlinked` transactions, preserving accurate ledger volume while avoiding false graph edges.

4. **Trailing Total Rows**:
   - Summary rows (`TOTAL,,,,...`) at the bottom of bank exports are truncated before staging, preventing false million-rupee ghost transactions.
