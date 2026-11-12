# CaseConnect AI — Demo & Real Dataset Ingestion Guide

**Document Version:** 1.0.0  
**Governing Standard:** Section 63 Bharatiya Sakshya Adhiniyam, 2023 (BSA 2023)  
**System Invariant:** 100% Data-Agnostic Ingestion (Zero Hardcoding)

---

## 1. Overview & Data-Agnostic Guarantee

CaseConnect AI is engineered to be **completely data-agnostic**. The platform accepts forensic data from **any source**—any bank (SBI, HDFC, ICICI, Axis, PNB, etc.), any telecom provider (Jio, Airtel, Vi, BSNL), and any law-enforcement portal—with **zero code changes**.

### Prime Ingestion Principles:
1. **Lossless Raw Store:** Every row and every column of every uploaded file is captured in SQLite WAL tables (`raw_sheets`, `raw_rows`). Unmapped, unexpected, or foreign columns are never dropped.
2. **Dynamic Header & Preamble Detection:** Scans cell density and type consistency to dynamically find the header row, ignoring preambles, disclaimer banners, or account holder summary boxes.
3. **Automatic Content-Based Profiling:** Even if headers are in Hindi, Hinglish, regional languages, or cryptic abbreviations (e.g., `ANUM`, `B_PARTY`, `TXN_VAL`), the system profiles column values (10-digit phones, 11-character IFSC codes, 10-character PANs, 12-digit Aadhaar, dates, amounts) to suggest mappings automatically.
4. **Officer Review & Saved Templates:** When layout ambiguity is detected, the officer confirms the column mapping once. That header signature is saved in SQLite and auto-applied to future files of that layout.

---

## 2. Supported Formats, Delimiters & Encodings

| Category | Supported Specifications |
| :--- | :--- |
| **Tabular Formats** | `.csv`, `.tsv`, `.xlsx` (Multi-sheet workbooks), `.json`, `.jsonl`, `.txt` (delimited) |
| **Documents / Text** | `.pdf` (digital and scanned statements / FIRs), `.txt`, `.docx` |
| **Delimiters** | Comma (`,`), Semicolon (`;`), Pipe (`\|`), Tab (`\t`), Space, or custom (auto-sniffed) |
| **File Encodings** | `UTF-8`, `UTF-16`, `Windows-1252` (CP-1252), `ISO-8859-1` (Latin-1) |
| **Currency Formats** | Standard decimals (`12500.50`), Indian Lakh grouping (`1,25,000.00`), negative in parentheses (`(5000)`), Dr/Cr suffix, INR/Rs prefixes. Converted strictly to **64-bit integer paise**. |
| **Date Formats** | `YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, `DD-Mon-YYYY`, ISO-8601 timestamps. Ambiguity is resolved by statistical evidence in the column. |

---

## 3. Canonical Target Vocabularies

When mapping files, the engine maps incoming columns to canonical forensic targets:

### 3.1 Call Data Records (CDR)
* `caller_phone`: A-party MSISDN (normalized to 10 digits when valid Indian mobile)
* `receiver_phone`: B-party MSISDN
* `call_datetime` / `call_date` + `call_time`: Call timestamp
* `duration_seconds`: Call duration in integer seconds
* `call_type`: `VOICE`, `SMS`, `INCOMING`, `OUTGOING`, `MISSED`
* `imei`: 14-16 digit handset hardware IMEI (Luhn verified)
* `imsi`: 15-digit SIM subscriber IMSI
* `cell_id` / `first_cell`: Cell tower ID / location

### 3.2 Bank Statements & Financial Transactions
* `from_account` / `remitter_account`: Source account number
* `to_account` / `beneficiary_account`: Destination account number
* `from_name` / `to_name`: Remitter or beneficiary account holder name
* `amount_paise`: Monetary value (stored strictly in 64-bit integer paise, never float)
* `transaction_date`: Transaction date or timestamp
* `reference_number`: UTR, IMPS reference, NEFT ID, or cheque number
* `narration`: Transaction description text
* `balance`: Account balance post-transaction

### 3.3 IP & Session Logs
* `ip_address`: IPv4 or IPv6 address
* `timestamp`: Connection timestamp
* `identifier`: Associated phone number, user ID, or IMEI
* `port`: Destination port
* `action`: Login, transfer, session start

---

## 4. How to Generate Demo Data Using ANY AI

You can generate realistic forensic datasets from **ChatGPT, Claude, Gemini, DeepSeek, or any LLM** using the copy-paste prompt templates below.

### 4.1 AI Prompt Template: CDR (Call Data Records)
```text
Generate a realistic Indian Call Data Record (CDR) CSV dataset with 30 rows.
Requirements:
1. Columns: A_Party_No, B_Party_No, Call_Date, Call_Time, Duration_Sec, Call_Type, IMEI_No, Cell_ID.
2. Use realistic 10-digit Indian mobile numbers (starting with 9, 8, 7, 6).
3. Include multiple calls between a central coordinating number and 3 other numbers.
4. Include some repeated IMEI numbers to simulate shared handsets.
5. Use comma delimiter and output ONLY valid CSV text with headers.
```

### 4.2 AI Prompt Template: Bank Statement (Multi-Hop Financial Trail)
```text
Generate a realistic Indian bank statement CSV for an account investigation with 35 transactions.
Requirements:
1. Columns: Txn_Date, Value_Date, Description, Ref_No, Debit, Credit, Balance.
2. Use Indian currency lakh formatting (e.g. 1,50,000.00).
3. Simulate a rapid pass-through / layer pattern: large credit arrives via RTGS/NEFT from Account 'ACC_ORIGIN_01', followed within 2 hours by multiple smaller debits to 3 beneficiary accounts ('ACC_BENEF_01', 'ACC_BENEF_02', 'ACC_BENEF_03').
4. Include realistic narrations like "UPI/P2A/324141/...", "NEFT-HDFC0001234-...", "IMPS/P2A/...".
5. Output ONLY valid CSV text with headers.
```

### 4.3 AI Prompt Template: Messy / Non-Standard Layout (Stress-Testing)
```text
Generate a messy CSV bank statement to test robust forensic ingestion.
Requirements:
1. Add a 4-line preamble at the top with bank branch name, account number, and customer address before the header row.
2. Header columns in mixed Hinglish: Tarikh, Vivaran, Chq_Ref, Rashi_Nikasi, Rashi_Jama, Kul_Shesh.
3. Include amounts with Rs. symbols, commas, and negative numbers in parentheses.
4. Add 2 unexpected extra columns: 'Branch_Code' and 'Channel_Type'.
5. Output ONLY raw CSV text.
```

---

## 5. What to Do When Uploading an Unfamiliar File

1. **Upload File:** Navigate to the case docket in CaseConnect AI and upload the file in the **Evidence Ingestion** tab.
2. **Review Auto-Detection:** The system automatically analyzes the file:
   - Identifies whether it is CDR, Bank Statement, or IP Log.
   - Detects the header row, ignoring preamble and trailing disclaimers.
   - Shows confidence score for each column mapping.
3. **Confirm or Adjust Mappings:**
   - If a column is unfamiliar or has confidence `< 0.80`, the **Column Mapping Modal** will prompt the officer to select the correct canonical field from the dropdown.
   - Any column that does not match a canonical field can simply be left as **"Extra / Unmapped"**. It will still be **losslessly saved in SQLite** and will appear in Excel exports and raw inspections.
4. **Save Template:** Click **Confirm & Ingest**. The layout is permanently remembered for future uploads of that exact bank or telecom layout.

---

## 6. Verifying Ingestion Integrity

After ingestion:
* **Reconciliation Check:** CaseConnect AI asserts `rows_in_file == staged + rejected + preamble + blank`. If any row is missing, the ingestion job marks the file with a clear diagnostic warning.
* **Lossless Store:** Click **Raw Store Inspection** to view the verbatim raw row JSON tokens for any staged record.
* **Reversibility:** Every ingested file can be surgical rolled back with a single click without affecting other evidence in the case docket.

