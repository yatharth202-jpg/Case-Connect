# Case Connect AI — Architectural & Pipeline Diagrams (Mermaid)

> Use these Mermaid diagram sources for documentation, presentations, and technical reports.

---

## 1. System Architecture Diagram

```mermaid
graph TD
    Client["Investigator Workstation (React + Vite SPA)"]
    
    subgraph FastAPI Application Server
        Auth["OAuth2 JWT Auth & RBAC (Admin, Investigator, Viewer)"]
        IngestService["Ingestion Engine (Readers, Normalizers, Mappers)"]
        GraphService["Graph & NetworkX In-Memory Cache"]
        MoneyService["Money Trail BFS & Pattern Detection"]
        AnalyticsService["Telecom MAD Spikes & 5-Signal Lead Advisor"]
        ReportService["ReportLab Section 63 BSA PDF Generator"]
        AuditService["SHA-256 Hash Chained Audit Service"]
    end

    subgraph Persistent Storage Layer
        SQLite[("Authoritative SQLite Database (app.db)")]
        Neo4j[("Neo4j Graph Database (Optional Projection)")]
        Uploads[("Secure Evidence Storage (uploads/)")]
    end

    Client -->|HTTPS / REST| Auth
    Auth --> IngestService
    Auth --> GraphService
    Auth --> MoneyService
    Auth --> AnalyticsService
    Auth --> ReportService
    Auth --> AuditService

    IngestService -->|Store Byte Stream & Hashes| Uploads
    IngestService -->|Stage Rows & Entities| SQLite
    GraphService -->|Read Staged Relationships| SQLite
    GraphService -->|Project Subgraphs| Neo4j
    MoneyService -->|Query Ledger Rows| SQLite
    AnalyticsService -->|Compute Leads & Alerts| SQLite
    ReportService -->|Compile Court Dossier| Uploads
    AuditService -->|Append Immutable Blocks| SQLite
```

---

## 2. Evidence Ingestion & Normalization Pipeline

```mermaid
flowchart LR
    Upload["Raw File Upload (.csv, .xlsx, .json, .txt, .pdf)"] --> Hash["Compute SHA-256 Fingerprint"]
    Hash --> Validate["Magic Byte & Extension Validation"]
    Validate --> Classify{"File Category?"}

    Classify -->|Tabular: CDR / Bank / SDR| Parse["Universal Tabular Reader (Strip Banners)"]
    Classify -->|Unstructured: FIR / Seizure| DocNLP["Text Extractor & Rule-based NER"]

    Parse --> Map["Dynamic Header Alignment (Jaro-Winkler + Synonyms)"]
    Map --> Template{"Template Cached?"}
    Template -->|Yes| AutoMap["Auto-Apply Confirmed Mapping (1.0 Conf)"]
    Template -->|No| Prompt["Officer Confirmation Modal"]

    AutoMap --> Normalize["Field Normalization (Paise, 10-Digit Mobile, ISO Dates)"]
    Prompt --> Normalize

    Normalize --> Filter{"Row Valid?"}
    Filter -->|Valid| Stage["Stage into SQLite (CallRecord / Transaction)"]
    Filter -->|Malformed| Reject["Log to RejectedRow Table with Line No."]

    Stage --> Audit["Record 'ingest_evidence' in Cryptographic Audit Log"]
    DocNLP --> StagedEntities["Stage Extracted Entities for Officer Review"]
```

---

## 3. Unified Heterogeneous Graph Data Model

```mermaid
graph TD
    Person(("Person Node"))
    Phone(("Phone Node"))
    BankAccount(("BankAccount Node"))
    Vehicle(("Vehicle Node"))
    IPNode(("IP Address Node"))
    FIRNode(("FIR Document Node"))

    Person -->|USES (Conf: 0.95)| Phone
    Person -->|OWNS (Conf: 1.0)| BankAccount
    Person -->|DRIVES (Conf: 0.90)| Vehicle
    Person -->|MENTIONED_IN| FIRNode

    Phone -->|CALLS (Duration, Date, MAD Spike)| Phone
    BankAccount -->|TRANSFERRED_TO (Amount Paise, Ref)| BankAccount
    Phone -->|SEEN_ON_IP| IPNode
    BankAccount -->|LOGGED_FROM| IPNode
```

---

## 4. Cryptographic Section 63 BSA 2023 Audit Hash Chain

```mermaid
flowchart LR
    subgraph Block 0 - Genesis
        B0["Index: 0<br/>Action: system_init<br/>Prev Hash: '000...000'<br/>Curr Hash: 4a8b...1f"]
    end

    subgraph Block 1 - File Upload
        B1["Index: 1<br/>Action: upload_evidence<br/>User: investigator1<br/>Prev Hash: 4a8b...1f<br/>Curr Hash: 9e2c...88"]
    end

    subgraph Block 2 - Column Mapping
        B2["Index: 2<br/>Action: map_evidence<br/>User: investigator1<br/>Prev Hash: 9e2c...88<br/>Curr Hash: b17a...3d"]
    end

    subgraph Block 3 - Officer Merge
        B3["Index: 3<br/>Action: approve_merge<br/>User: investigator1<br/>Prev Hash: b17a...3d<br/>Curr Hash: f601...e4"]
    end

    B0 --> B1 --> B2 --> B3
```
