# SIH26189_Sample_Demo_Data.pdf


<!-- PAGE 1 -->
## Page 1

SIH26189
AI-Powered Criminal Network Analysis System
Synthetic Sample Data for Project Demo
Important: All records in this document are fictional/synthetic and intended only for software development, testing and SIH
demonstration.
1. Sample FIR — fir_001.txt
FIRST INFORMATION REPORT
FIR ID: FIR-2026-001
Date: 12-08-2026
Police Station: Central Cyber Cell
The complainant reported suspicious financial activity involving
Rahul Sharma and Amit Kumar.
During preliminary investigation, Rahul Sharma was found associated
with mobile number 9876543210. The number communicated with
9123456789 on multiple occasions.
A bank account ending in 7890 was allegedly used for receiving
n5,00,000 from another account.
Amit Kumar was identified as a person associated with mobile
number 9123456789.
Vehicle UP32AB1234 was also found associated with Rahul Sharma.
Investigation is ongoing.
Expected extracted entities
PERSON: Rahul Sharma, Amit Kumar
PHONE: 9876543210, 9123456789
BANK ACCOUNT: XXXXXX7890
AMOUNT: n5,00,000
VEHICLE: UP32AB1234
FIR: FIR-2026-001
2. CDR — cdr.csv
call_id,caller,receiver,date,time,duration_seconds
C001,9876543210,9123456789,2026-08-05,10:32,120
C002,9123456789,9988776655,2026-08-05,11:15,245
C003,9876543210,9988776655,2026-08-06,09:42,180
C004,9988776655,8877665544,2026-08-06,14:20,95
C005,9123456789,8877665544,2026-08-07,16:45,310
C006,8877665544,7766554433,2026-08-08,18:10,150
C007,9876543210,9123456789,2026-08-09,12:05,420
C008,7766554433,9988776655,2026-08-09,13:22,75
C009,9123456789,9988776655,2026-08-10,15:30,280
C010,9988776655,8877665544,2026-08-11,17:55,360
3. Bank Transactions — bank_transactions.csv
transaction_id,from_account,to_account,amount,date,time,reference
T001,ACC1001,ACC2002,500000,2026-08-05,12:10,TXN-A001
T002,ACC2002,ACC3003,300000,2026-08-06,14:35,TXN-A002
T003,ACC3003,ACC4004,180000,2026-08-07,16:20,TXN-A003
T004,ACC4004,ACC5005,120000,2026-08-08,18:45,TXN-A004
T005,ACC2002,ACC6006,75000,2026-08-09,11:15,TXN-A005
T006,ACC6006,ACC7007,50000,2026-08-10,13:40,TXN-A006
T007,ACC3003,ACC8008,90000,2026-08-11,15:10,TXN-A007
T008,ACC1001,ACC9009,25000,2026-08-12,10:30,TXN-A008
4. Person–Entity Mapping — persons.csv
person_id,name,phone,bank_account,vehicle,email
P001,Rahul Sharma,9876543210,ACC1001,UP32AB1234,rahul.demo@example.com
P002,Amit Kumar,9123456789,ACC2002,UP32CD5678,amit.demo@example.com
P003,Rohit Verma,9988776655,ACC3003,UP32EF9012,rohit.demo@example.com


<!-- PAGE 2 -->
## Page 2

P004,Vikas Singh,8877665544,ACC4004,UP32GH3456,vikas.demo@example.com
P005,Neeraj Gupta,7766554433,ACC5005,UP32JK7890,neeraj.demo@example.com
5. IP Logs — ip_logs.csv
log_id,phone,ip_address,date,time
IP001,9876543210,203.0.113.10,2026-08-05,10:30
IP002,9123456789,203.0.113.11,2026-08-05,11:12
IP003,9988776655,203.0.113.12,2026-08-06,09:40
IP004,8877665544,203.0.113.13,2026-08-07,16:40
IP005,7766554433,203.0.113.14,2026-08-08,18:05
6. Vehicle Records — vehicles.csv
vehicle_id,registration,owner,location,date
V001,UP32AB1234,Rahul Sharma,Lucknow,2026-08-05
V002,UP32CD5678,Amit Kumar,Lucknow,2026-08-06
V003,UP32EF9012,Rohit Verma,Kanpur,2026-08-07
V004,UP32GH3456,Vikas Singh,Kanpur,2026-08-08
V005,UP32JK7890,Neeraj Gupta,Lucknow,2026-08-09


<!-- PAGE 3 -->
## Page 3

7. Expected Graph Relationships
Rahul Sharma
nnn USES nn> 9876543210
nnn OWNS nn> ACC1001
nnn DRIVES nn> UP32AB1234
9876543210
nnn CALLS nn> 9123456789
nnn USED BY nn> Amit Kumar
nnn OWNS nn> ACC2002
nnn TRANSFERRED TO
fl
ACC3003
fl
ACC4004
fl
ACC5005
8. Demo Investigation Flow
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
INVESTIGATOR REVIEW
fl
UPLOAD CDR CSV
fl
UPLOAD BANK CSV
fl
ENTITY RESOLUTION
fl
BUILD NEO4J GRAPH
fl
SEARCH: Rahul Sharma
fl
3-HOP / 4-HOP GRAPH
fl
MONEY TRAIL
fl
CENTRALITY / NETWORK ANALYSIS
fl
TIMELINE
fl
GENERATE REPORT
9. Expected Demo Queries
1. Find all entities connected to Rahul Sharma.
2. Show Rahul Sharma's phone numbers.
3. Show all calls from 9876543210.
4. Find a 3-hop path from Rahul to Amit.
5. Show the money trail starting from ACC1001.
6. Find accounts receiving more than n1,00,000.
7. Calculate high-degree communication nodes.
8. Show all entities mentioned in FIR-2026-001.
9. Display events in chronological order.
10. Generate an investigation summary report.
10. Suggested Neo4j Node Types
Person
Phone
BankAccount
Transaction
IP
Vehicle
FIR
Location
CryptoWallet
Email
Organization


<!-- PAGE 4 -->
## Page 4

11. Suggested Neo4j Relationships
(:Person)-[:USES]->(:Phone)
(:Person)-[:OWNS]->(:BankAccount)
(:Person)-[:DRIVES]->(:Vehicle)
(:Person)-[:USES]->(:IP)
(:Person)-[:OWNS]->(:CryptoWallet)
(:Phone)-[:CALLED]->(:Phone)
(:BankAccount)-[:TRANSFERRED_TO]->(:BankAccount)
(:Person)-[:MENTIONED_IN]->(:FIR)
(:Person)-[:LOCATED_AT]->(:Location)
Safety / interpretation note: This dataset is fictional. Graph centrality, anomaly scores or AI outputs should be presented as
investigative leads requiring human verification, not as proof of criminal activity.

