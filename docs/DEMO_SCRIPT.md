# Case Connect AI — Master Demo Script & Rehearsal Guide

> **Target Presentation Time:** 8 Minutes (with a 2-Minute Backup Elevator Pitch)  
> **Starting State:** Clean application with zero seeded cases (`python scripts/reset_db.py --force`).

---

## 8-Minute Comprehensive Rehearsal Script

### Minute 0:00 – 0:45 | Introduction & Problem Context
- **Screen:** Login Page (`http://localhost:5173/login`)
- **Action:** Sign in as Investigator (`investigator1` / `OfficerPass1234!`).
- **Narrative:**
  > *"Respected Judges, cyber financial syndicates and organized gangs in India operate across multiple states, rotating burner SIMs, mule accounts, and shell entities. An IO in Delhi investigating an extortion case typically has an Excel sheet of CDRs, PDF bank statements from three different banks, and an FIR text. Today, synthesizing these takes weeks of manual work, and by the time links are mapped, the money has left the banking system.*
  >
  > *This is Case Connect AI: an explainable, forensic-grade network analysis platform built strictly according to Section 63 of Bharatiya Sakshya Adhiniyam, 2023."*

---

### Minute 0:45 – 1:30 | First-Run Experience & Case Creation
- **Screen:** Cases Hub (`/cases`)
- **Action:**
  1. Highlight the clean state showing *"No investigation cases found"*.
  2. Click **"Open New Case"** (or **"Open Your First Case"**).
  3. Enter:
     - **Title:** `Syndicate Operation Goldcrest (FIR 104/2026)`
     - **Description:** `Inter-state cyber fraud and financial layering network across Delhi, Haryana, and UP.`
     - **Priority:** `High`
  4. Submit. The app routes instantly to the Case Command Center.

---

### Minute 1:30 – 2:45 | Evidence Ingestion & Universal Column Mapping
- **Screen:** Evidence Repository Tab (`/cases/{id}?tab=evidence`)
- **Action:**
  1. Drag and drop raw investigation files:
     - `cdr.csv` (Telecommunications log)
     - `bank_transactions.csv` (Multi-party settlement transactions)
     - `FIR-2026-101.txt` (Police first information report)
  2. Observe immediate client-side and server-side hashing:
     - Display the **SHA-256 fingerprint badge** next to each file.
     - Click **"Verify Integrity"** to demonstrate instantaneous cryptographic validation.
  3. Click **"Map & Ingest"** on `bank_transactions.csv`:
     - Show the universal column mapper modal.
     - Point out the automatically recognized canonical headers (`from_account`, `to_account`, `amount`, `date`).
     - Click **"Confirm Mapping & Stage"** and watch the live progress bar finish.

---

### Minute 2:45 – 4:00 | Executive Dashboard & Anomaly Analytics
- **Screen:** Executive Dashboard Tab (`/cases/{id}?tab=overview`)
- **Action:**
  1. Point to the top stat cards: Total Ingested Rows, Active Entities, and Total Volume in INR (e.g. ₹47.7 Lakhs).
  2. Highlight the **Calls-per-Day Area Chart**:
     - Point out the red reference dot: *"Our Median Absolute Deviation (MAD) engine automatically flagged this spike on August 7th without static threshold rules."*
     - Use the phone dropdown to filter specifically to the organizer's line.
  3. Scroll to the **24x7 Communication Heatmap**:
     - Show coordinated nighttime call activity (between 00:00 and 03:00) highlighted on the matrix.

---

### Minute 4:00 – 5:15 | Multi-Hop Money Trail & Layering BFS
- **Screen:** Money Trail Explorer Tab (`/cases/{id}?tab=money`)
- **Action:**
  1. Select the primary collection account from the dropdown.
  2. Adjust the hop slider to **3 Hops**.
  3. Point out the directed fund flow:
     - Victim Account $\rightarrow$ Mule Account $\rightarrow$ Shell Entity.
     - Show the **Rapid Pass-Through** alert badge attached to the mule node.
  4. Click on an edge to inspect the exact transfer timestamp, amount in paise/INR, and banking reference (`NEFT/RTGS`).

---

### Minute 5:15 – 6:15 | Master Profiles & Human-in-the-Loop Dedup
- **Screen:** Master Profiles Tab (`/cases/{id}?tab=profiles`)
- **Action:**
  1. Show candidate entity resolution pairs (e.g., `Vikas Sharma` vs `V. K. Sharma`).
  2. Highlight the Soundex phonetic match and Jaro-Winkler confidence score (0.91).
  3. Click **"Approve Merge"**:
     - The profile card updates instantly.
  4. Show the **"Undo Merge"** button:
     - Click Undo to prove that Section 63 BSA compliance ensures human officers retain total control and no merge is destructive.

---

### Minute 6:15 – 7:15 | Lead Advisor & Pre-FIR Anomaly Timeline
- **Screen:**
  1. Click **Chronological Timeline Tab** (`/cases/{id}?tab=timeline`):
     - Highlight the top hero banner: *"Organized communication and transfer anomalies detected 12 days prior to formal complaint registration."*
  2. Switch to **Lead Advisor Tab** (`/cases/{id}?tab=leads`):
     - Show the ranked list of high-priority investigative leads.
     - Expand the top lead:
       - Show the 5-signal breakdown (Money Flow, Bridge Centrality, Call Spikes, Timing Coincidence, Multi-Document Presence).
       - Note: *"Zero prior criminal history or demographic bias is used—only data-driven network properties."*
     - Click **"Accept Lead"** and add officer investigation notes.

---

### Minute 7:15 – 8:00 | Section 63 BSA 2023 Court Dossier & Audit Chain
- **Screen:**
  1. Open **Report Generator Tab** (`/cases/{id}?tab=reports`):
     - Select sections (Cover, Evidence Fingerprints, Money Trail, Network Graph, Lead Dossier).
     - Click **"Generate Legal Dossier"** and open the generated PDF.
     - Show the Section 63 BSA statutory certificate and SHA-256 evidence table.
  2. Open topbar **Audit Log** (`/audit`):
     - Click **"Verify Hash Chain"**:
     - Green badge appears: `Chain Verified: 14/14 cryptographic blocks valid.`

---

## 2-Minute Elevator Pitch Script (Short Demo)

> *"Good morning. When cyber syndicates siphon crores across India, police officers face three critical challenges:*
> 1. *Fragmented data—CDRs from Airtel, statements from HDFC, and FIRs don't talk to each other.*
> 2. *Complex layering—money moves through 4 mule accounts in under an hour.*
> 3. *Court admissibility—evidence must withstand strict scrutiny under Section 63 of Bharatiya Sakshya Adhiniyam, 2023.*
>
> *Case Connect AI solves this:*
> - *We ingest arbitrary telecom and bank CSVs in seconds via universal mapping.*
> - *Our statistical MAD and BFS engines uncover rapid pass-through mules and coordinated midnight call spikes.*
> - *Our 5-signal Lead Advisor ranks targets with 100% explainable mathematical proof.*
> - *And with one click, it compiles a court-ready Section 63 forensic PDF complete with cryptographic SHA-256 hash chains.*
>
> *No black boxes, no prejudicial profiling, zero mock data. Everything you see runs locally on pure evidentiary data."*

---

## Fallback & Contingency Plan

| Potential Failure Point | Automatic Fallback Mechanism |
| :--- | :--- |
| **Docker or Neo4j Unreachable** | Case Connect AI uses SQLite as its primary source of truth and maintains an in-memory NetworkX graph cache (`build_detail_graph`). The graph canvas and money trail work smoothly even if Neo4j is offline. |
| **Network / Wi-Fi Disconnects** | All fonts (`@fontsource/inter`) and assets are bundled locally in the production build; zero external CDN calls exist in the entire codebase. The app functions 100% offline. |
| **Upload File Mismatch** | Pre-generated clean samples are committed under `data/synthetic/samples/clean/` for instant one-click drag-and-drop during presentation. |
