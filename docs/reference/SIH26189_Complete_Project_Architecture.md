# SIH26189_Complete_Project_Architecture.pdf


<!-- PAGE 1 -->
## Page 1

SIH26189
AI-Powered Criminal Network Analysis System
Complete Project Architecture — Every Major
Module
1. High-Level Architecture
INVESTIGATOR
fl
WEB DASHBOARD / UI
fl
API GATEWAY
fl
Auth/RBAC | Case Management | Data Ingestion | Investigation
fl
Document Processing
nnn Text PDF fi PyMuPDF
nnn Scanned PDF fi OCR
fl
NLP / Entity Extraction
fl
Entity Resolution
fl
Human Review
fl
Graph Builder
fl
NEO4J
fl
Network Analysis | Money Trail | Path Analysis
fl
Investigation UI fi Graph | Timeline | Alerts | Reports
2. Authentication & User Management
Roles: Admin, Senior Investigator, Investigator, Analyst.
Features: login, session management, RBAC, case-level permissions, security controls and audit logging.
3. Case Management
Every investigation is organized inside a Case.
Case: ID, title, description, creator, assigned officers, status, priority, date, evidence and notes.
Features: create, assign, update, close/archive, evidence management, notes and case timeline.
4. Data Ingestion
Inputs:
(cid:127) FIR: PDF / DOCX / TXT / scanned PDF
(cid:127) CDR: CSV / Excel / JSON
(cid:127) Bank: CSV / Excel / JSON
(cid:127) Other legally available data: IP, vehicle, crypto-wallet and email records.
Pipeline: Upload fi Validate fi Parse fi Normalize fi Process.
5. Document Processing
PDF fi type detection.
Text PDF fi PyMuPDF/pdfplumber fi text.
Scanned PDF fi OCR (e.g. Tesseract) fi text.
Then clean and normalize the text.


<!-- PAGE 2 -->
## Page 2

6. AI / NLP Entity Extraction
Example FIR: “Rahul Sharma used mobile 9876543210 and transferred Rs 5 lakh to account 1234567890.”
Output:
PERSON fi Rahul Sharma
PHONE fi 9876543210
AMOUNT fi 500000 INR
BANK_ACCOUNT fi 1234567890
Entities: Person, Phone, Bank Account, UPI ID, Email, IP, Vehicle, Crypto Wallet, Location, Organization, Date, Money, FIR.
7. Rule-Based Extraction
Use deterministic rules alongside NLP for obvious structured fields:
Phone numbers, IP addresses, bank-account patterns, amounts and dates.
Combined output = NLP + Regex/rules.
8. Entity Resolution & Deduplication
Different sources may contain: Rahul Sharma, Rahul S., R. Sharma, Rahul Kumar Sharma.
System suggests a possible same entity with confidence and supporting signals.
Matching signals: name similarity, phone/email, address/DOB where available, bank account, vehicle and known
associations.
Investigator approves or rejects the merge.
9. Data Cleaning & Normalization
Standardize formats before graph creation.
Example: +91-9876543210 / 9876543210 fi canonical phone.
n5,00,000 / Rs 500000 / 500000 INR fi canonical monetary value.
10. Graph Construction
Nodes:
Person, Phone, BankAccount, Transaction, IP, Vehicle, CryptoWallet, FIR, Location, Organization, Email.
Relationships:
Person USES Phone
Person OWNS BankAccount
Person DRIVES Vehicle
Person USES IP
Person OWNS CryptoWallet
Phone CALLED Phone
Account TRANSFERRED_TO Account
Person MENTIONED_IN FIR
Person LOCATED_AT Location
11. Graph Database Layer
Recommended: Neo4j.
Example:
Rahul fi USES fi Phone A fi CALLED fi Phone B fi USED BY fi Amit fi OWNS fi Bank A fi TRANSFERRED fi Bank
B.
12. Investigation Search
Search by person, phone, bank account, vehicle, IP, crypto wallet or FIR.
Result: selected entity fi direct links fi related entities fi paths fi source evidence.
13. Multi-Hop Investigation


<!-- PAGE 3 -->
## Page 3

Allow 1–4 hop expansion.
Example: Rahul fi Phone A fi Phone B fi Amit fi Bank A.
Controls: 1 Hop | 2 Hop | 3 Hop | 4 Hop.
14. Money Trail Analysis
Account A fi n5L fi Account B fi n3L fi Account C fi n2L fi Account D.
Show total transferred, transaction count, dates, transaction IDs, source/destination and full money-flow path.
15. Communication Network Analysis
CDR analysis: A fi B fi C fi D.
Metrics: call count, duration, frequency, first/last contact and communication clusters.
16. Network / Graph Analytics
Degree Centrality fi many connections.
Betweenness Centrality fi structural bridges.
PageRank fi structurally important nodes.
Community Detection fi connected clusters.
Important: high centrality does NOT prove criminality. Use “high-centrality entity requiring further investigation.”
17. AI Investigation Assistant
AI assists investigators with graph queries and summaries.
Example: “Show connections between Rahul Sharma and Account 1234.”
AI returns the relevant path, hop count, entities and evidence references.
It should support—not replace—the investigator’s decision.
18. Anomaly / Pattern Detection
Flag patterns for review:
(cid:127) Rapid fund movement
(cid:127) Many accounts fi one account
(cid:127) One phone fi many persons
(cid:127) Sudden unusual transaction amount
(cid:127) Unusual communication patterns
Use “Potential anomaly”, not “Confirmed criminal activity.”
19. Timeline Module
Chronological events:
01 Aug fi FIR registered
05 Aug fi Phone A calls Phone B
07 Aug fi n5L transferred
09 Aug fi Vehicle event
12 Aug fi Account B transfers n3L
Support filtering and links back to evidence.
20. Geographic Analysis
Where legally available:
Person fi Phone fi Location.
Possible views: locations, movement history, common locations and transaction locations.
21. Evidence Management


<!-- PAGE 4 -->
## Page 4

Every extracted fact should retain provenance.
Example:
Rahul Sharma fi FIR_1023.pdf fi Page 4.
9876543210 fi CDR_August.csv fi Row 1832.
This allows graph facts to be traced back to source evidence.
22. Evidence Integrity
Evidence file fi SHA-256 hash fi stored integrity value.
If the file changes: old hash „ new hash fi evidence integrity mismatch.
23. Audit Log
Record user, timestamp, action, case and relevant object/evidence.
Example: Officer A opened case fi uploaded FIR fi Officer B approved entity match fi report generated.
24. Automated Investigation Report
PDF sections:
Case information
Investigator/date/status
Entity summary
Network summary
Major clusters
Money trails
Timeline
Evidence references
Investigation notes.
25. Frontend Architecture
React
nnn Login
nnn Dashboard
nnn Cases
n nnn Case List
n nnn Case Details
n nnn Evidence
nnn Data Upload
nnn Entity Review
nnn Investigation
n nnn Search
n nnn Graph
n nnn Timeline
n nnn Money Trail
n nnn Network Analysis
nnn Alerts
nnn Reports
nnn Admin
Graph visualization: Cytoscape.js recommended.
26. Backend Architecture
React fi Node.js/Express fi REST API fi services.
Services:
Auth, Case, Upload, Document, Entity, Graph, Investigation, Analytics, Report, Audit.
AI layer: Node.js « FastAPI « Python NLP/AI services.
27. AI Service Architecture
FastAPI
nnn OCR
nnn NER
nnn Rule/Regex Extraction
nnn Entity Resolution
nnn Anomaly Detection


<!-- PAGE 5 -->
## Page 5

fl
Structured JSON
fl
Node.js API
fl
Neo4j / PostgreSQL
28. Database & Storage
Neo4j fi graph relationships, paths, networks and transactions.
PostgreSQL fi users, cases, permissions, metadata, audit logs and report metadata.
Object storage fi FIR PDFs, images, CSVs, evidence and generated reports.
29. Complete End-to-End Data Flow
FIR / CDR / BANK
fl
DATA INGESTION
fl
FILE VALIDATION
fl
DOCUMENT PROCESSING
fl
TEXT / OCR
fl
ENTITY EXTRACTION
nnn NER
nnn REGEX
fl
ENTITY RESOLUTION
fl
HUMAN REVIEW
fl
GRAPH BUILDER
fl
NEO4J
fl
Network | Money Trail | Path Analysis
fl
INVESTIGATION UI
fl
Graph | Timeline | Alerts | Reports
30. SIH Demo Flow
LOGIN
fl
CREATE CASE
fl
UPLOAD FIR PDF
fl
PDF fi TEXT
fl
ENTITY EXTRACTION
fl
SHOW ENTITIES
fl
INVESTIGATOR APPROVES
fl
UPLOAD CDR CSV
fl
UPLOAD BANK CSV
fl
ENTITY RESOLUTION
fl
BUILD NEO4J GRAPH
fl
SEARCH “Rahul Sharma”
fl
3-HOP GRAPH
fl
MONEY TRAIL
fl
CENTRALITY ANALYSIS
fl
TIMELINE


<!-- PAGE 6 -->
## Page 6

fl
GENERATE PDF REPORT
31. MVP Priority
Must-have:
1. Login/RBAC
2. Case management
3. PDF upload
4. PDF fi text
5. Entity extraction
6. Entity review
7. CDR CSV upload
8. Bank CSV upload
9. Entity resolution
10. Neo4j graph
11. Graph visualization
12. 1–4 hop search
13. Money trail
14. Centrality
15. Timeline
16. Evidence provenance
17. PDF report
18. Audit log
Phase 2:
OCR, AI assistant, anomaly detection, community detection, geographic visualization, crypto analysis.
32. Core Project Principle
Heterogeneous Data
fi Entity Extraction
fi Entity Resolution
fi Knowledge Graph
fi Graph Analytics
fi Investigator Decision
The system organizes and connects evidence; it should not automatically declare a person criminal based on graph position,
centrality or an AI-generated score.

