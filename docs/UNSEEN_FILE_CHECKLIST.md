# Case Connect AI — 5-Minute Unseen File Verification Checklist

> **Purpose:** Use this checklist when testing an unseen file from an external real-world police station, bank branch, or telecom operator that has never been processed by this system.

---

### Phase 1: Pre-Upload Inspection (1 Minute)
1. **Probe Without Exposing Sensitive Data:**
   - Run the zero-copy probe script:
     ```bash
     python scripts/probe_file.py --path "path/to/unseen_file.csv"
     ```
   - Inspect detected file type, row count, detected encoding (`utf-8`, `cp1252`), and header columns.
2. **Confirm Supported Extensions:**
   - Supported: `.csv`, `.xlsx`, `.json`, `.jsonl`, `.txt`, `.pdf`, `.docx`.
   - Note: `.xls` (legacy 1997-2003 binary format) is not supported; convert to `.xlsx` or `.csv` if encountered.

---

### Phase 2: Ingestion & Column Mapping (1.5 Minutes)
1. **Create Clean Investigation Case:**
   - Open browser to `http://localhost:5173/cases`.
   - Click **"Open New Case"**, enter a title and description, and submit.
2. **Upload the Unseen File:**
   - Go to **Evidence Repository** tab.
   - Drag and drop your unseen file.
   - Verify that the **SHA-256 fingerprint** appears immediately.
3. **Review & Confirm Column Mapping:**
   - Click **"Map & Ingest"**.
   - Review proposed canonical fields (`caller`, `receiver`, `date`, `time` for CDR; `from_account`, `to_account`, `amount`, `date` for Bank).
   - If a custom column was not recognized, use the dropdown to set the appropriate canonical attribute.
   - Click **"Confirm Mapping & Stage"**.
   - Check the **Data Quality Summary** modal: verify staged row count vs rejected row count.

---

### Phase 3: Inspecting Forensic Results (1.5 Minutes)
1. **Executive Dashboard (`overview` tab):**
   - Verify Total Ingested Rows and Total Volume match expected summary metrics.
   - Look for detected **MAD communication spikes** (red markers) or transaction volume peaks.
2. **Investigation Graph (`graph` tab):**
   - Click **"Rebuild / Sync Graph"** if graph is newly uploaded.
   - Verify nodes represent Phone, BankAccount, or Person entities.
   - Check that degree centralities and shared connections render correctly.
3. **Money Trail (`money` tab):**
   - Search for the primary remitter or victim account.
   - Trace fund layers across 2 to 4 hops.
   - Confirm if any node exhibits a **Rapid Pass-Through** or **Fan-In** alert badge.
4. **Lead Advisor (`leads` tab):**
   - Verify that candidate leads are ranked with explainable signal breakdowns.
   - Confirm that unuploaded modalities are displayed as *"Not available"* without crashing or fabricating zeros.

---

### Phase 4: Troubleshooting Known Boundary Conditions (1 Minute)

#### 1. Bank Narration Parsing Mismatch
- **Symptoms:** Transactions show `COUNTERPARTY_UNKNOWN` or fail to link recipient accounts in single-account bank statements.
- **Root Cause:** The issuing bank utilizes a proprietary narration format differing from standard NEFT, RTGS, IMPS, or UPI patterns.
- **Resolution:**
  - Open `backend/app/services/ingestion/statement.py`.
  - Add the bank's regex pattern to `NARRATION_PATTERNS`:
    ```python
    # Example: BANKNAME/TRANSFER/<ACCT>/<NAME>
    re.compile(r"BANKNAME/(?:TRF|NEFT)/(?P<account>[A-Z0-9]+)/(?P<name>[A-Z\s]+)", re.I)
    ```
  - Re-upload the file or re-stage via mapping.

#### 2. Preambles or Multi-Row Headers
- **Symptoms:** Column mapper displays garbage headers or offset rows.
- **Resolution:**
  - The file has multiple banner rows before the column headers.
  - The universal reader (`readers.py`) strips up to 25 banner rows automatically. If the file has $>25$ header rows, remove the top disclaimer rows or adjust `max_banner_rows=50` in `backend/app/services/ingestion/readers.py`.

#### 3. Date Formatting Outliers
- **Symptoms:** Dates fail normalization and are routed to `RejectedRow`.
- **Resolution:**
  - Check rejected row reason in SQLite: `SELECT * FROM rejected_rows WHERE reason = 'INVALID_DATE'`.
  - Ensure dates follow standard formats (`DD/MM/YYYY`, `YYYY-MM-DD`, `DD-Mon-YYYY`).
