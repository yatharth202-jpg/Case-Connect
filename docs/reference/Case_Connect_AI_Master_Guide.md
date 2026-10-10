# Case_Connect_AI_Master_Guide (1).pdf


<!-- PAGE 1 -->
## Page 1

SMART INDIA HACKATHON 2026 | PS SIH26189 | TEAM UNITx
Case Connect AI
AI-Powered Criminal Network Analysis System
The complete master guide: problem, solution, every feature,
how it is built, why each choice was made, and how it is different.
Written in plain English, so anyone can understand it,
even with zero technical or police background.
FIR Call records Bank data Graph AI Human decides
All people, accounts and numbers in this document are fictional examples created for explanation.
Draft prepared October 2026.


<!-- PAGE 2 -->
## Page 2

Contents
Where to find everything
The Project in 60 Seconds . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
1 The Problem . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
2 Our Solution . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
3 A Day with Inspector Meera . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
4 Features in Detail . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
F1 Secure login and roles . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
F2 Case workspace . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
F3 Evidence upload and fingerprint . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
F4 AI evidence extraction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 11
F5 Entity matching and review . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12
F6 Cross-FIR Master Profile . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 13
F7 Knowledge graph and multi-hop search . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 14
F8 Money Trail Explorer . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 15
F9 Communication pattern detection . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 16
F10 Lead Advisor: 'Why is this person important?' . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 17
F11 Timeline . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18
F12 'Why this link?' evidence button . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 18
F13 Audit log with tamper check . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
F14 Report generator . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
F15 Five small extras . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 19
5 How It Is Built . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 20
6 What Makes It Unique . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 23
7 What to Build First . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 24
8 Build Plan . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 25
9 Demo and Judging . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 29
10 Risks, Ethics and Law . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 31
11 Future Roadmap . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 32
12 Glossary . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 33
13 Final Checklist and Sources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 34
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 2


<!-- PAGE 3 -->
## Page 3

How to read this guide
If you are... Read these parts Why
A complete beginner Quick Summary, Part 1, 2 and 3 Understand the problem and the idea through a
simple story.
A developer on the team Parts 4, 5, 7 and 8 Features, tools, build order and what to learn.
The presenter / pitch Parts 3, 6, 9 and 10 Story, uniqueness, demo script, judge questions and
lead honest limits.
Anyone unsure about a Part 12 (Glossary) Every technical word explained in one line.
word
Colour tags used in this guide
HERO FEATURE FOUNDATION SUPPORT EXTRA ROADMAP
● Hero feature: the 3 features that make the project stand out. Build these best.
● Foundation: must exist for everything else to work (login, cases, upload, graph).
● Support: makes the product complete and trustworthy (timeline, report, audit log).
● Extra: small additions we suggest that cost little but add value.
● Roadmap: good ideas for later; do not build them first.
FICTIONAL EXAMPLES
Every name, number and account in this document is fictional. The example case (Case #101) is used
again and again, so you can follow one story from the start to the end.
After reading this guide you will be able to...
● explain the problem and the idea to anyone in two minutes;
● name every feature, say why it exists and how it works;
● say which tool is used for what, and why it beat the alternatives;
● explain how we are different from existing products, honestly;
● follow a step-by-step build plan and know what to learn first;
● run the demo and answer the judges' questions with confidence.
The whole system in seven steps (explained in Part 2).
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 3


<!-- PAGE 4 -->
## Page 4

The Project in 60 Seconds
If you read only one page, read this one
Case Connect AI is a website for police investigators. An officer uploads the evidence of a
case: FIR reports, phone call records and bank statements. The system reads the files by itself,
joins everything into one connected map (called a graph) and shows who is connected to
whom, where the money went, and which people deserve a closer look and why. Every
fact links back to its source file. The officer, not the AI, makes the final decision.
THE PROBLEM THE SOLUTION THE RESULT
Evidence is scattered across files AI reads documents and files. One connected picture per case
and police stations. Criminals hide Duplicate identities are matched and across cases. Hidden people
behind layers of middlemen. (officer approves). Everything and money paths become visible.
Officers join the dots by hand in goes into a graph database. The Every claim is traceable to its
Excel. That is slow, and it gets system analyses money and calls source. A ready-made PDF report
harder with every extra step. and explains every flag with for seniors and courts.
evidence.
Our 3 hero features
1 Master Profile 2 Money Trail Explorer 3 Lead Advisor
Same person in many FIRs (even Pick an account, set an amount Click a person and see why the
different police stations)? The filter (for example ₹5 lakh and system flagged them: the
system suggests the link; the above) and a hop limit. See where connections, transactions,
officer approves; one profile shows the money came from and where it evidence, what data is still missing
everything together. moved. and what to do next.
Our 4 golden rules
AI suggests, the human decides. Merges, flags and leads are always shown as suggestions with a
1
confidence level.
2 Every fact has a source. Click any link and see the file, page or row it came from.
3 Every flag is explained. No black box: scores come from simple, visible calculations.
4 Start small and real. A smooth demo on synthetic data beats 20 half-working features.
The example case used throughout this guide (Case #101, fictional)
4 ₹12 lakh 3 6 1
hidden organiser
victims lost in total FIRs, 3 stations people in the network
found
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 4


<!-- PAGE 5 -->
## Page 5

The Problem
1
Why investigators struggle today
A simple way to picture it
Imagine a jigsaw puzzle whose pieces are kept in five different rooms, in five different formats. Some
pieces belong to the same picture but have different names written on them. Nobody can see the whole
picture. That is how evidence in organised-crime cases looks today.
Figure 1: Today the officer joins separate files by hand. With the system, all evidence feeds one connected picture.
What kinds of crime are we talking about?
● Cyber fraud and online investment scams, where money is split across many bank accounts.
● Money laundering and hawala-style networks, where cash moves through middlemen and shell
companies.
● Trafficking and drug networks, where members talk through burner phones and keep their distance
from the leader.
The 3 root causes
1 Scattered evidence 2 Hidden middlemen 3 Same person, many
names
FIRs sit in PDFs at police stations. The real organiser stays several "Rahul Sharma", "R. Sharma" and
Call records (CDRs) come as Excel steps away from the crime, "Rahul K. Sharma" may be one
or CSV files from telecom working through proxy accounts person. In a large city, the same
companies. Bank statements and shell companies. Each step is person can appear in FIRs at many
arrive in different formats. There called a hop. By hand, tracking police stations, and each file holds
is no common format, so nothing stops being practical after about 2 only a small piece.
connects automatically. to 3 hops.
What this costs
Officers clean call records and bank statements in Excel by hand. This can take days or even weeks for one
gang (this is an estimate from the problem statement analysis, not a measured number). Meanwhile,
criminals move the money out and change phones. Speed matters: the longer it takes, the less
money can be frozen.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 5


<!-- PAGE 6 -->
## Page 6

Who is affected?
Who Their pain today
Investigating officers (IOs) Hours of manual cleaning and cross-checking before real investigation even
starts.
Cyber crime cells and state police Many cases, many phones and accounts, little time; hard to see links between
intelligence wings cases.
Central agencies (CBI, ED, NIA) Need links across states and across agencies; evidence arrives in different
formats.
Prosecutors and courts Need evidence whose origin can be proven and shown step by step.
Victims Wait longer; stolen money has often moved on before action is taken.
WHERE WE FIT (CCTNS)
India already has CCTNS (Crime and Criminal Tracking Network and Systems), a national network that
connects police stations for FIR and crime-record management. The Ministry of Home Affairs told
Parliament that all 17,762 police stations were using it as of 1 June 2026. Case Connect AI does not
replace CCTNS. It is an analysis layer: it reads call and bank evidence, connects it with FIR data and
shows hidden links. Real integration with official systems would need formal approval and authorised
access.
Our Solution
2
One connected picture, built with AI, controlled by humans
In one sentence: we turn scattered evidence into one connected map, and we explain what
stands out on it. The pipeline below is what happens every time an officer uploads files.
Figure 2: The 7-step pipeline. Two points need a human: reviewing matches (step 4) and the final decision.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 6


<!-- PAGE 7 -->
## Page 7

Our 5 promises
See everything in one place
1
Upload FIRs, call records and bank statements into one case workspace.
Find hidden links
2
A graph shows connections 1 to 4 hops away, and links the same person across different FIRs.
Follow the money
3
An interactive money trail with amount and hop filters shows where money came from and moved.
Explain every flag
4
"Why is this person important?" lists the connections, transactions and evidence behind a flag.
Keep humans in charge and evidence safe
5
Officer approvals, SHA-256 file fingerprints, roles and an audit log protect the process.
Today versus with Case Connect AI
Task Today (manual) With our system
Read FIRs Officer reads and types names and AI extracts names, phones, accounts,
numbers into Excel. amounts. Officer only checks.
Combine FIR + call + bank Copy-paste and lookups across many Automatic: everything becomes one graph.
data sheets.
Find the hidden Follow a few links by eye; gets hard Expand 1 to 4 hops in one click; path
middleman after 2 to 3 hops. highlighted.
Spot the same person in Depends on memory or phone calls System suggests the match with confidence;
other FIRs between police stations. officer approves.
Trace money Scroll through long bank statements. Money Trail Explorer with amount and hop
filters.
Explain to a senior or Write notes by hand. One-click PDF report with evidence
court references and file fingerprints.
WHAT THE SYSTEM WILL NEVER DO
● Declare anyone a criminal. It only shows leads for review.
● Merge two identities without an officer's approval.
● Hide where a fact came from.
● Take any legal or enforcement action.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 7


<!-- PAGE 8 -->
## Page 8

A Day with Inspector Meera
3
One fictional case, told step by step
Case #101 (fictional): an online investment fraud. Four victims were tricked into paying ₹3 lakh each,
₹12 lakh in total. Three police stations received three separate FIRs. Inspector Meera Rao has the FIR PDFs,
a call-records file and a bank-statement file. Here is how she works with Case Connect AI.
# What Meera does What the website does
1 Logs in as an Investigator. Checks her role and records the login in the audit log.
2 Creates "Case #101 - Online Investment Makes a private workspace. Only assigned officers can open it.
Fraud".
3 Uploads 3 FIR PDFs, a call-records CSV Checks file type and columns. Creates a SHA-256 fingerprint for
and a bank CSV. every file. Keeps originals untouched.
4 Waits a few seconds. AI reads the files and extracts names, phones, accounts, amounts,
vehicles and dates, each with a confidence level and source page.
5 Sees a suggestion: "Rahul Sharma" and Merges them into one Master Profile. Logs who approved and
"R. Sharma" may be the same person when.
(HIGH: same phone). She clicks
Approve.
6 Opens the Investigation page. Draws the graph: people, phones, accounts, vehicles and the calls
and transfers between them.
7 Searches "Rahul Sharma" and chooses 3 Shows the chain Rahul to Amit to Vikas to Shree Trade Links. A
hops. new name appears: Vikas Yadav.
8 Opens the Money Trail: Account A, filter Shows ₹12 lakh entering Account A, splitting into B, C and D,
₹3 lakh and above, 3 hops. joining again in Account E (Vikas), and ₹10 lakh leaving to a shell
company.
9 Clicks Vikas Yadav. Lead Advisor panel: priority 83/100, the reasons, evidence links,
missing data and suggested next steps.
10 Clicks Generate report. Creates a PDF with entities, graph picture, money trail, timeline,
evidence references and file fingerprints.
Figure 3: A simple sketch of the Investigation screen: search and filters on top, graph in the middle, the 'Why is this person
important?' panel on the right, timeline at the bottom.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 8


<!-- PAGE 9 -->
## Page 9

Figure 4: What really happened in Case #101, in time order. The system sees the pattern before any FIR is filed.
Figure 5: Who called whom. Vikas Yadav is the only person who links both groups.
THE KEY INSIGHT
Vikas Yadav is not named in any of the three FIRs. He is found only because the system connects the
call records and the bank data. This is the 'aha moment' of the whole project, and the moment to show first
in a demo.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 9


<!-- PAGE 10 -->
## Page 10

Features in Detail
4
What each feature does, why it exists, how it works and why we chose it
There are 14 core features plus 5 small extras. Each feature has a card with four rows: What it does (in
plain words), Why it exists, How it works and Why this choice (including the alternatives we rejected).
# Feature Type One-line summary
F1 Secure login and roles FOUNDATION Right people see the right things
F2 Case workspace FOUNDATION Each investigation in its own protected space
F3 Evidence upload and fingerprint FOUNDATION Upload files; prove they were not changed
Reads files and finds people, phones,
F4 AI evidence extraction FOUNDATION
accounts, amounts
F5 Entity matching and review FOUNDATION Finds duplicate identities; officer approves
F6 Cross-FIR Master Profile HERO One profile from many FIRs and stations
F7 Knowledge graph and multi-hop search FOUNDATION See who is connected, 1 to 4 hops away
F8 Money Trail Explorer HERO Follow money with amount and hop filters
F9 Communication pattern detection SUPPORT Spikes, bridges, sudden new links
Lead Advisor: 'Why is this person
F10 HERO Explained leads, missing data, next steps
important?'
F11 Timeline SUPPORT Everything in time order
F12 'Why this link?' evidence button SUPPORT Every link shows its source
F13 Audit log with tamper check SUPPORT Who did what, protected from edits
F14 Report generator SUPPORT One-click PDF with evidence references
Cross-case alert, data check, decision log,
F15 Five small extras EXTRA
saved views, summaries
F1 Secure login and roles FOUNDATION
What it does Officers sign in with a user name and password. Each role sees and does only what it should:
Admin, Investigator or Viewer.
Why it exists Case data is highly sensitive. Roles stop the wrong person from seeing or changing evidence.
How it works Passwords are stored as hashes (bcrypt), never as plain text. After login the server gives a
signed token (JWT). Every request is checked against the user's role.
Why this Standard, well tested and quick to build. Alternatives: single sign-on with government identity
choice systems (roadmap), or writing your own security code (never do that).
Action Admin Investigator Viewer
Upload evidence Yes Yes No
Approve or reject entity matches Yes Yes No
View graph, money trail, timeline Yes Yes Yes
Generate report Yes Yes No
Manage users and view the audit log Yes No No
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 10


<!-- PAGE 11 -->
## Page 11

F2 Case workspace FOUNDATION
What it does Every investigation lives inside a Case: title, description, priority, status, assigned officers,
notes and the list of evidence.
Why it exists Keeps investigations separate and gives each officer access only to the cases assigned to them.
How it works Cases are stored in PostgreSQL. Every graph item in Neo4j carries its case number. Links
between cases are shown only to officers who can open both cases.
Why this One big shared pool would be simpler, but it risks leaking data between cases and officers.
choice
F3 Evidence upload and fingerprint FOUNDATION
What it does Upload FIRs (PDF or text), call records (CSV or Excel) and bank statements (CSV or Excel). The
system checks, fingerprints and stores each file.
Why it exists In court you must show that evidence was not changed. A SHA-256 fingerprint changes
completely if even one character in the file changes.
How it works Check type, size and columns, then compute SHA-256 (Python hashlib), save the original file
read-only, and store the hash, uploader and time. Anyone can re-check the fingerprint later.
Why this SHA-256 is standard, free and fast. Storing every file on a blockchain would be slow and
choice unnecessary.
LEGAL NOTE
India's rules for electronic evidence moved from Section 65B of the Indian Evidence Act to Section 63 of
the Bharatiya Sakshya Adhiniyam, 2023, which asks for a certificate for electronic records. Our
fingerprints and audit log help prepare that paperwork. Whether evidence is admissible is decided by the
court and lawyers, not by software.
F4 AI evidence extraction FOUNDATION
What it does Reads text and finds people, phone numbers, bank accounts, UPI IDs, vehicles, IP
addresses, amounts, dates, places and organisations.
Why it exists Typing these by hand is slow and error-prone, and it is the first thing that eats an officer's time.
How it works 1. PDF to text with PyMuPDF or pdfplumber.
2. Rules (regex) for things that always look the same: phone, account, amount,
date, vehicle number, IP.
3. AI (spaCy NER) for names, places and organisations.
4. Clean-up: +91-98765 43210 and 9876543210 become one standard phone; "Rs 5
lakh", "₹5,00,000" and "500000 INR" all become 500000.
5. Every entity gets a confidence level and its source (file and page).
Call-record and bank CSV files need no AI: they are read directly with pandas.
Why this Rules plus NER are fast, free, run offline and are easy to explain. Alternatives: an LLM can
choice read anything, but it may invent facts and may need a paid service. Training your own model
needs thousands of labelled examples. A later option: use an LLM only as a helper, with every
output checked against the source text. Scanned PDFs need OCR (Tesseract); this is phase 2.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 11


<!-- PAGE 12 -->
## Page 12

Figure 6: From a sentence in an FIR to clean, structured records (confidence values are illustrative).
F5 Entity matching and review FOUNDATION
What it does Finds records that may be the same person, account or phone and suggests merging them.
The officer approves or rejects. Any merge can be undone.
Why it exists One person appears under many spellings. A wrong merge sends an investigation in the wrong
direction, so the system must be careful.
How it works 1. Exact match on strong IDs: bank account, phone, vehicle number, e-mail.
2. Name similarity with the Jaro-Winkler method (Python library rapidfuzz).
3. Shared details such as address and date of birth.
4. Combine into a confidence level: HIGH = a strong ID plus a similar name; MEDIUM
= two medium clues; LOW = name only (shown as 'possible', never as a merge
suggestion).
5. Families and offices: if one phone or address belongs to several different names,
flag it as 'shared device/address' instead of merging.
Why this Clear rules can be explained in one sentence to a judge or a court. A machine-learning matcher
choice needs labelled data we do not have. We never auto-merge: this matches our promise of human
control.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 12


<!-- PAGE 13 -->
## Page 13

Figure 7: Some clues are strong (an account number) and some are weak (a common name or a shared Wi-Fi). Strengths are
illustrative and can be tuned.
F6 Cross-FIR Master Profile HERO FEATURE
What it does Builds one page per real-world person with everything known from all FIRs and files: other
names, phones, accounts, vehicles, cases, connections and timeline.
Why it exists In a big city like Delhi the same person can appear in many FIRs at different police stations.
Each FIR holds a small piece: a phone here, an account there. Joining the pieces reveals the real
pattern.
How it works When a new FIR is uploaded, the system looks for matching strong IDs in existing records,
suggests links, and asks the officer. After approval the pieces join one Master Profile. Every fact
keeps its FIR number and page.
Why this Today officers search other stations manually or by phone. Safety rules: suggest links only for
choice cases the officer may open, and always offer 'Undo merge'.
Figure 8: Three FIRs from three police stations become one Master Profile after the officer approves. The bank record, which
lists 9876543210 as the registered mobile of the account, connects FIR 2 to the others.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 13


<!-- PAGE 14 -->
## Page 14

F7 Knowledge graph and multi-hop search FOUNDATION
What it does Stores all entities and links as a graph. Search by name, phone, account, vehicle, IP or FIR.
Expand 1 to 4 hops. Filter by type, date and amount.
Why it exists The question an investigator asks is: who is connected to whom, and through whom? A graph
database answers this directly.
How it works Neo4j stores nodes (Person, Phone, BankAccount, Vehicle, IP, FIR) and relationships (USES,
OWNS, CALLED, TRANSFERRED_TO). The website draws them with Cytoscape.js. Results are
capped (for example 200 nodes) and the hop limit is 4, so the picture stays readable.
Why this In SQL a 3-hop question needs a chain of table joins; in Neo4j it is one short query.
choice Alternatives: Memgraph (similar, in-memory), PostgreSQL recursive queries (harder to read),
NetworkX in memory (nothing is saved when it stops). For drawing: D3.js needs much more
code; vis-network is simpler but gives less control.
MATCH path = (p:Person {name: 'Rahul Sharma'})-[*1..3]-(x)
RETURN path LIMIT 200
Figure 9: Hop buttons in the website. Three hops from Rahul reach the hidden person and the shell company.
HONEST WARNING
Showing too many nodes creates a 'hairball' that nobody can read. Always limit results, filter by type and
amount, and let the officer expand step by step.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 14


<!-- PAGE 15 -->
## Page 15

F8 Money Trail Explorer HERO FEATURE
What it does Pick an account, set an amount filter (for example ₹5 lakh and above) and a hop limit, and
choose a direction: money in, money out or both. See the paths, totals, dates and transaction
IDs.
Why it exists Freezing money quickly is the most valuable action in a fraud case. Officers need to see the
flow, not scroll through rows.
How it works A Neo4j path query follows TRANSFERRED_TO links and checks the amount on every step.
Pandas calculates totals and the time gap between money arriving and leaving. Patterns
flagged for review: many accounts into one (fan-in), one into many (fan-out), money
leaving soon after arriving (rapid pass-through), and many amounts just below a limit
(splitting).
Why this This was a teammate's idea and it makes the trail interactive. A static Sankey chart looks pretty
choice but cannot be filtered. Crypto wallets are stored as nodes only; we do not claim crypto tracing
in the first version.
MATCH path = (a:Account {number: '1234567890'})-[:TRANSFERRED_TO*1..3]->(b:Account)
WHERE ALL(r IN relationships(path) WHERE r.amount >= 300000)
RETURN path
TECHNICAL NOTE
In Neo4j a variable-length relationship returns a list of relationships, so a condition on every step must use
ALL(...). Writing r.amount directly on such a path is a common mistake and will not work.
Figure 10: Money Trail Explorer for Case #101 with a filter of ₹3 lakh and above. Setting the filter to ₹5 lakh leaves only A to
B and E to the shell company.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 15


<!-- PAGE 16 -->
## Page 16

F9 Communication pattern detection SUPPORT
What it does Looks beyond who called whom to how they called: sudden spikes, very frequent contacts,
bridge persons and suddenly new links.
Why it exists Patterns give an early warning. In Case #101 the first alert appears on 03 Aug, six days before
the first FIR.
How it works Pandas counts calls per number per day. NetworkX measures bridges. Thresholds can be
adjusted by the officer.
Why this Simple rules can be explained in one sentence. Machine-learning anomaly detection (for
choice example Isolation Forest) is a roadmap item.
Pattern Plain meaning How it is found
Sudden spike A number's calls jump far above its Compare each day with the number's normal
own normal. (average plus 3 times the spread).
Very frequent Two entities talk far more than Rank pairs by calls per day and flag the outliers.
contact typical pairs.
Bridge person One person connects two otherwise Betweenness centrality plus group detection.
separate groups.
Sudden new A new link appears and quickly First-contact date plus call volume in the first days.
connection becomes busy.
Figure 11: A new number's calls per day. The red line is the alert threshold.
HONEST TRUTH
A call centre or a shopkeeper also makes many calls. The system labels results 'Potential anomaly',
shows the context and never says 'criminal'. Thresholds should be tuned on realistic data.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 16


<!-- PAGE 17 -->
## Page 17

F10 Lead Advisor: 'Why is this person important?' HERO FEATURE
What it does A button on every person plus a list called Suggested leads. For each lead: priority score,
reasons, evidence, matched patterns, missing data, suggested next steps and a confidence
level. The officer chooses Accept, Reject or Need more data.
Why it exists A picture is not enough. With thousands of nodes, officers need to know where to look first and
why.
How it works 1. Collect signals from the graph: money, calls, network position, timing, links to
several FIRs.
2. Score each signal with simple, visible maths. Weights are stored in a settings file.
3. Compare with known crime patterns (a small rule library, for example
mule-account network).
4. List missing data that each pattern normally needs.
5. Officer decides; the decision is saved in the audit log.
Why this A graph neural network or an ML classifier needs lots of labelled criminal data (we have none)
choice and is a black box. Centrality alone does not explain anything. Rules plus scores are
explainable and adjustable. An LLM may only rewrite computed facts into plain language; it
must never add new facts.
Figure 12: How a lead is produced and who has the last word.
Figure 13: The score is a sum of visible parts. Weights are illustrative and can be tuned.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 17


<!-- PAGE 18 -->
## Page 18

SAMPLE LEAD CARD: Case #101
Lead 1: Vikas Yadav | Priority: HIGH (83/100) | Confidence: Medium (two data sources are
missing)
Why flagged: only person who links both groups; ₹10 lakh moved from his account to a shell
company; a new SIM made 38 calls on the day the money moved; the money from all 4 victims reaches
his account (indirectly linked to all 3 FIRs).
Evidence: call-record rows (new SIM), bank transactions A to B to E to shell company, Master Profile
links.
Pattern match: mule-account network (money collected from several accounts, then quickly passed
on).
Missing data: KYC record for Account E; 15 more days of Account E statements; tower-location data
for the new SIM; SIM purchase and verification details.
Suggested next steps: request KYC and SIM details; request tower data; consider asking the bank to
review the account, following legal procedure. Final decision: investigating officer.
BIAS WARNING
Past criminal records: in the demo they are synthetic. In real life, access needs official authorisation. A
past record must only be a small, clearly labelled signal, and it must never raise a score on its own,
because that would be unfair bias against people who were already in the system.
F11 Timeline SUPPORT
What it does Shows events from all files in time order: FIR dates, calls, transfers and system alerts. Filter by
person, type or date. Click an event to open its evidence.
Why it exists Investigators and courts think in sequences. Order often shows cause and effect, for example a
call spike right before a transfer.
How it works Every source row becomes an event with a timestamp, type, linked entities and source. A
timeline component draws them.
Why this A calendar view is poor for dense events; a vertical or horizontal timeline reads naturally.
choice
F12 'Why this link?' evidence button SUPPORT
What it does Click any line or circle in the graph and a small card shows what it connects, the source file
and page or row, how it was found (rule, AI or officer), the confidence and who approved it.
Why it exists Trust. In court and in front of judges the first question is always: how do you know?
How it works Every node and relationship stores source_file, location, method, confidence and approved_by.
Why this Cheap to build and very strong in a demo. It turns the graph from 'a nice picture' into 'evidence
choice you can check'.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 18


<!-- PAGE 19 -->
## Page 19

F13 Audit log with tamper check SUPPORT
What it does Records who did what, when and on which case or object: login, upload, approve, export and
more.
Why it exists Accountability. Seniors and courts can see exactly how the analysis was done.
How it works Each entry stores user, time, action, object and a hash that includes the previous entry's hash.
A 'Verify log' button re-checks the whole chain.
Why this Our theme includes blockchain. A hash chain gives blockchain's key benefit (tamper evidence)
choice without the complexity. A full Hyperledger or Ethereum network is heavy; a roadmap option is
to anchor a daily summary hash on a permissioned blockchain.
Figure 14: Each log entry carries the previous entry's hash. Editing one entry breaks every later one.
F14 Report generator SUPPORT
What it does One click creates a PDF: case details, entity summary, network summary with a graph picture,
money trails, timeline, evidence references with file fingerprints, notes and lead decisions.
Why it exists Officers must show their work to seniors and courts. This saves hours of typing and screenshots.
How it works Python (ReportLab or WeasyPrint) fills a template with data from Neo4j and PostgreSQL. Every
AI-generated item is labelled 'Lead for review'.
Why this The alternative is pasting screenshots into Word by hand.
choice
F15 Five small extras we suggest adding EXTRA
Extra What it does Why it helps Effort
Cross-case alert When a new file arrives and a phone Catches repeat offenders instantly and Low
or account already exists in other solves the 'many FIRs' problem.
cases, show an alert.
Data quality check After upload, list broken rows, invalid Real data is messy; this shows Low
phone numbers and duplicates. robustness.
Lead decision log Accept or Reject notes are saved and Shows human-in-the-loop in action. Low
shown in reports.
Saved views Save a graph state (for example Saves repeated work; great in a demo. Medium
Account A, ₹3 lakh and above, 3 hops)
and reopen or share it.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 19


<!-- PAGE 20 -->
## Page 20

Extra What it does Why it helps Effort
Plain-English A few sentences at the top of each Beginners understand a profile in 10 Low
summary profile, written from computed facts seconds.
using templates.
How It Is Built
5
Architecture, data model, tools and why each tool was chosen
The system has five layers. Each layer has one job, so team members can work in parallel. The website
talks to a small API layer; the API layer talks to a Python AI service and to two databases.
Figure 15: The five layers of Case Connect AI.
The graph data model
A graph has nodes (things: a person, a phone, an account) and relationships (links: uses, owns, called,
transferred money). Every node and relationship also remembers where it came from.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 20


<!-- PAGE 21 -->
## Page 21

Figure 16: The graph model. Phones link to phones by calls; accounts link to accounts by transfers.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 21


<!-- PAGE 22 -->
## Page 22

Tools we will use, and why
Layer Tool What it does here Why chosen Alternatives
Website React + Tailwind Pages, forms, tables Huge community; AI Vue, Angular
CSS coding tools write it well
Graph Cytoscape.js Interactive network, Built for network graphs D3.js (more code),
drawing layouts, click events vis-network (less
control)
API layer Node.js + Login, cases, uploads; JavaScript, so the web FastAPI only (fewest
Express talks to AI service team can build it parts; best fallback)
AI service Python + FastAPI PDF reading, extraction, Python has the best data Flask
matching, analytics and NLP libraries
Graph Neo4j (Cypher) Stores entities and links; Most popular graph DB; Memgraph, PostgreSQL
database multi-hop queries free options; lots of recursive queries
learning material
Normal PostgreSQL Users, cases, Reliable, free, standard MongoDB or SQLite for
database permissions, audit log a quick prototype
PDF reading PyMuPDF / Text from PDFs Fast and free Tesseract OCR for
pdfplumber scans (phase 2)
Extraction spaCy + regex Names, places; fixed Free, offline, explainable LLM (flexible but may
patterns invent facts)
Matching rapidfuzz Name similarity Fast and simple Machine-learning
(Jaro-Winkler) matchers
Data work pandas Read CSV or Excel; The standard tool -
group by day; time gaps
Graph NetworkX Centrality, bridges, Easy Python; no plugin Neo4j Graph Data
maths groups setup Science
Security bcrypt, JWT, Passwords, tokens, Standard and proven Never write your own
SHA-256, HTTPS fingerprints
Reports ReportLab / Creates the PDF report Python-based Word export
WeasyPrint
Test data Python Faker Fake Indian names, Realistic, safe, free Writing by hand
(en_IN) phones, addresses
Team tools Git + GitHub, VS Code history, editing, Standard; commits prove -
Code, .env files secrets your work
Key decisions: why this and not that
Decision We chose We rejected Reason
Merging identities Officer approval Automatic merge above a A wrong merge misleads the whole
score investigation.
Explaining flags Rules and visible scores Graph neural network or No labelled criminal data; every flag
black box must be explainable to a court.
Evidence integrity SHA-256 + hash-chained Full blockchain network Same tamper-evidence, far less
audit log complexity and delay.
Reading Regex + spaCy LLM only LLMs can invent facts, cost money
documents and may send data outside.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 22


<!-- PAGE 23 -->
## Page 23

Decision We chose We rejected Reason
Graph scores NetworkX in Python Neo4j Graph Data Science Much easier to set up; enough for a
plugin prototype.
Data for demo Synthetic data Real or scraped data Real investigation data is restricted;
privacy and legal risk.
Hop limit Maximum 4, results Unlimited Keeps the picture readable and the
capped queries fast.
Wording 'Lead for review', 'Suspect', 'Criminal' Fairness and legal safety; the system
'Potential anomaly' is not a judge.
IF TIME IS SHORT
The team presentation lists Node.js, FastAPI, Neo4j and PostgreSQL. If time is short, the safest
simplification is to let FastAPI do both jobs (API and AI) and skip Node.js. Fewer moving parts means fewer
bugs. If you do change the stack, update the slides so the demo matches what you present.
What Makes It Unique
6
How we compare with what already exists in the world
Several strong products already exist. The honest question is: what is our place next to them? We are
not trying to beat them in every way. We are focused on one gap: Indian multi-station evidence (FIR +
call records + bank data), explained clearly, with a human in control, at low cost.
Existing option What it is Where it is strong The gap we target
IBM i2 Analyst's Long-established Powerful charting for Commercial enterprise licence; reading
Notebook link-analysis software trained analysts Indian FIR text and explaining leads is
used in investigations not its focus (from public descriptions).
Palantir Gotham Large intelligence and Integrates huge data Enterprise scale and cost; closed
defence data platform sources at scale system; out of reach for a small unit or a
student prototype.
Chainalysis / Cryptocurrency tracing World-class crypto flow Crypto only; do not read FIRs or Indian
Elliptic tools tracing call and bank records.
Maltego Link-analysis tool, often Gathering and charting Focus is online information, not case
used for online online data files like FIRs and CDRs.
information
CCTNS National network of Connects every police Mainly record keeping and sharing; not
police stations for FIR station; record keeping an analysis tool for call and bank
and crime records and sharing evidence (from public descriptions).
Excel and manual What many units use Free and familiar Slow; breaks down after 2 to 3 hops; no
work today proof of where facts came from.
Based on public descriptions of these products. They are mature and have many features not listed here. Our claim is
focus, not superiority.
Our 8 differentiators
# Differentiator Why it matters
1 Cross-FIR Master Profile Built for the real Indian situation: the same person appears in FIRs
at many police stations.
2 FIR + call records + bank data in No hopping between tools; connections appear automatically.
one graph
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 23


<!-- PAGE 24 -->
## Page 24

# Differentiator Why it matters
3 Explainable 'Why is this person Gives leads with reasons, evidence, missing data and next steps,
important?' not verdicts.
4 Human-in-the-loop by design Every merge and lead is approved by an officer, which lowers the
risk of AI mistakes.
5 Interactive money trail Amount and hop filters turn a static chart into an investigation tool.
6 Provenance on every link Source file, page and row for each fact; trust and court-readiness.
7 Tamper-evident audit log Blockchain-style protection without blockchain-style cost.
8 Open-source, low-cost stack Runs on a normal laptop or an office server; suitable for state units.
HONEST TRUTH
Do not claim 'better than IBM i2 or Palantir'. Judges will not believe it. Say: 'Those tools are excellent but
expensive and general. We focus on Indian FIR, call and bank evidence, explainable leads and human
control, and we can run on open-source tools.' Also do not claim regional-language support until Hindi OCR
is really built.
What to Build First
7
Priorities, so the team does not get lost
A smooth demo of a smaller product beats a half-working demo of a huge one. The chart below ranks every
feature by impact (how much it helps investigators and judges) and effort (how hard it is to build).
Figure 17: Build the red and blue items first, add the green ones next, and keep the purple ones for the roadmap.
Stage What to build Done when...
Stage 1: Login and roles; cases; upload with SHA-256; You can load Case #101 data and see
Foundation graph in Neo4j; search with 1 to 4 hops the graph live.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 24


<!-- PAGE 25 -->
## Page 25

Stage What to build Done when...
Stage 2: Extraction (regex + spaCy); entity review; Master A new FIR upload links to an existing
Intelligence Profile person after approval.
Stage 3: Hero Money Trail Explorer; communication patterns; You can answer 'who is important and
features Lead Advisor why' with evidence.
Stage 4: Trust and 'Why this link?'; timeline; audit log; PDF report; The full demo runs without a single
polish extras manual workaround.
Stage 5: Roadmap OCR, geo map, community detection, Only after everything above is stable.
natural-language questions
DO NOT BUILD (YET)
● Crypto tracing: big, specialised and easy to overclaim.
● Kafka, Hyperledger, distributed clusters: a judge can ask hard questions about them, and they
add nothing to a live demo.
● Graph neural networks: no labelled data, hard to explain.
● Real criminal data: not available and not legal to use without authorisation.
● Perfect Hindi OCR: keep for later; start with text PDFs.
Build Plan
8
What to learn, how to vibecode safely, timeline, team and test data
8.1 What you need to learn
AI can write most of the code, but you must understand the key parts. Otherwise you cannot fix bugs or
answer judges. Learn these in this order:
Orde Skill How deep Free way to learn
r
1 Neo4j + Cypher Basic to intermediate: nodes, Neo4j GraphAcademy courses; Neo4j
relationships, MATCH, WHERE, paths documentation
2 Graph ideas Hops, centrality, bridges (the idea, not NetworkX documentation; short
the maths) videos
3 Cytoscape.js Basic: add nodes and edges, style, click Cytoscape.js documentation demos
events
4 API basics (Node or What a request and response are; Official tutorials of Express or FastAPI
FastAPI) routes
5 Python + pandas Read CSV, filter, group by pandas documentation, free tutorials
6 NLP basics Use ready-made spaCy models and spaCy free online course
regex; no training
7 Matching and Name similarity, simple rules, money Learn while building F5 and F8
transactions flow
8 Login and audit Hashing passwords, tokens, roles Library docs (bcrypt, JWT)
9 Git and GitHub Commit, branch, pull request GitHub documentation
10 Debugging Read the error, test small parts Practice; ask AI to explain errors
You do not need to learn deep learning, neural-network maths, training large models, computer vision or
advanced blockchain development.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 25


<!-- PAGE 26 -->
## Page 26

8.2 Ten rules for safe vibecoding
1. One small task at a time. Not 'build the whole app'. Start with 'upload a CSV and create nodes in
Neo4j'.
2. Write the data format first (the JSON each part sends and receives), then ask AI for code.
3. Run and test every step before asking for the next one.
4. Commit to Git after every working step. The commit history is proof that you built it.
5. Ask AI to explain every important piece in plain words. If you cannot explain it, you cannot defend it.
6. Own the key logic: matching rules, Cypher queries, score calculation. Let AI do the boring parts
(layouts, boilerplate).
7. Keep one source of truth for settings (weights, thresholds) in a config file.
8. Never put passwords or keys on GitHub. Use a .env file and a .gitignore.
9. Test with messy data (typos, missing values), not only perfect data.
10. Freeze features one week before the event and only fix bugs after that.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 26


<!-- PAGE 27 -->
## Page 27

8.3 Example 8-week timeline
Figure 18: Adjust the weeks to your real deadline. Learning and data creation start together.
8.4 Team roles (for a team of six)
Role Main job Skills
Frontend Pages, graph view, filters, Lead Advisor panel React, Tailwind, Cytoscape.js
Backend Login, roles, cases, uploads, audit log, API Node.js + Express (or FastAPI),
PostgreSQL
AI / NLP PDF to text, extraction, entity matching Python, regex, spaCy, rapidfuzz
Graph Graph schema, Cypher queries, hop search, Neo4j, Cypher
money trail
Data / Analytics Synthetic data, communication patterns, scores Python, pandas, NetworkX, Faker
Integration and Connect everything, testing, slides, demo Git, Figma or slides, storytelling
pitch script, README
8.5 The synthetic data plan (the most important early task)
Judges cannot see real police data, so a good story in the data is what makes the demo convincing. Build
Case #101 first, then add noise.
Item Starting size Notes
People About 15 6 in the core story, 9 as noise
Phone numbers About 20 Includes Vikas's new SIM (activated 25 Jul)
Bank accounts About 25 Accounts A to F as in Figure 10, plus noise
Call records About 800 rows Includes the call counts and the 38-call spike on 07 Aug
Bank rows About 300 Includes the ₹12 lakh in, ₹10 lakh out, and the 2.5 lakh
transfer below the filter
FIR text files 6 3 in the story (Rohini, Dwarka, Saket) plus 3 noise FIRs
Performance test About 10,000 nodes and Use a generator to show the system stays fast
later 50,000 links
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 27


<!-- PAGE 28 -->
## Page 28

Hidden 'needles' to plant: Vikas Yadav as the bridge; a shell company; one person in 3 FIRs with name
variants; two relatives sharing one phone (to test false merges); some typos, missing fields and duplicate
rows (to test data checks).
8.6 Folder structure and main API endpoints
case-connect-ai/
frontend/ React website
backend/ Node.js API (login, cases, uploads, audit)
ai-service/ Python FastAPI (extraction, matching, analytics)
data/ synthetic data generator + sample files
docs/ README, slides, demo script
.env.example settings template (never commit real .env)
Method Endpoint Purpose
POST /auth/login Sign in; returns a token
POST /cases Create a case
POST /cases/:id/evidence Upload a file; returns its SHA-256
GET /cases/:id/entities List extracted entities and match suggestions
POST /matches/:id/approve Approve (or reject, or undo) a merge
GET /graph/search?q=&hops;= Search and expand the graph
GET /money-trail?account=&min;=&hops;=& Money Trail Explorer
dir;=
GET /leads/:caseId Suggested leads with scores
GET /entities/:id/why 'Why is this person important?'
GET /audit/verify Check the audit hash chain
POST /cases/:id/report Generate the PDF report
8.7 Cypher cheat sheet (the 5 queries to know by heart)
// 1. Create two people and a call link
CREATE (a:Person {name:'Rahul Sharma'})-[:USES]->(p:Phone {number:'9876543210'})
// 2. Everything within 3 hops of Rahul
MATCH path = (:Person {name:'Rahul Sharma'})-[*1..3]-(x) RETURN path LIMIT 200
// 3. Money trail with an amount filter
MATCH path = (a:Account {number:'1234567890'})-[:TRANSFERRED_TO*1..3]->(b:Account)
WHERE ALL(r IN relationships(path) WHERE r.amount >= 500000)
RETURN path
// 4. Shortest connection between two people
MATCH p = shortestPath((a:Person {name:'Rahul Sharma'})-[*..6]-(b:Person {name:'Vikas Yadav'}))
RETURN p
// 5. Most connected people
MATCH (p:Person)-[r]-() RETURN p.name, count(r) AS links ORDER BY links DESC LIMIT 10
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 28


<!-- PAGE 29 -->
## Page 29

Demo and Judging
9
An 8-minute demo script, likely judge questions and live tests
9.1 The 8-minute demo script
Time Screen What to say
0:00 - 0:45 Problem slide "Evidence sits in five rooms. Officers join it by hand. We built one
connected picture."
0:45 - 1:30 Login, Case #101 "This is a private case workspace. Roles control who can see it."
pre-loaded
1:30 - 2:30 Upload a new FIR live "AI reads the FIR. Every item has a confidence and a source page."
2:30 - 3:30 Entity review, then Master "The same person appears in three police stations. I approve, and
Profile one profile appears."
3:30 - 4:30 Graph search, 3 hops "A name that is in no FIR appears: Vikas Yadav."
4:30 - 5:30 Money Trail, ₹3 lakh and "₹12 lakh comes in, splits, merges again, and ₹10 lakh leaves to a
above shell company."
5:30 - 6:30 Lead Advisor on Vikas "Here is why. Click any link to see its source. Here is what data we
still need."
6:30 - 7:15 Call-spike alert, timeline "The alert fired six days before the first FIR."
7:15 - 7:45 PDF report, verify audit log "One click for the report; the log proves nothing was edited."
7:45 - 8:00 Closing slide "The system suggests. The officer decides."
Tip: pre-load Case #101 and cache any outside data. Never depend on live internet during the demo.
9.2 Questions judges may ask, with answers
Question Short, honest answer
How do you handle aliases and Strong IDs (phone, account, vehicle) plus name similarity give a confidence level.
many phone numbers? The officer approves every merge, and merges can be undone.
What if relatives share a phone Shared phone or address alone is flagged as 'shared device or address', not
or address? merged. A similar name is also required, and the officer decides.
Does the AI decide who is No. It produces leads for review with visible reasons, evidence and missing data.
guilty? The officer decides.
Will this evidence stand in We help with integrity: SHA-256 fingerprints, an audit log and source tracking for
court? the certificate under Section 63 of the Bharatiya Sakshya Adhiniyam, 2023.
Admissibility is for the court.
Why Neo4j and not a normal Multi-hop questions are short in Cypher and long in SQL. Normal data (users,
database? cases, audit) still lives in PostgreSQL.
How does it scale to millions of The prototype is tested on thousands to tens of thousands of nodes. For scale we
call records? would add batch ingestion, indexes and a bigger graph setup. We do not claim
more than we tested.
Where does your data come Synthetic data for the demo. Real use needs authorised access and legal review.
from?
How do you avoid bias and false Scores are visible sums of simple parts, weights are adjustable, past records
flags? have low weight, and wording is 'lead' or 'potential anomaly'.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 29


<!-- PAGE 30 -->
## Page 30

Question Short, honest answer
How are you different from IBM They are excellent and general. We focus on Indian FIR, call and bank evidence,
i2 or Palantir? cross-FIR profiles, explainable leads and human control, using open-source tools.
Why not use an LLM for LLMs can invent facts. We use rules and NER for extraction and use an LLM, if at
everything? all, only to reword facts we already computed.
How is data protected? Roles, hashed passwords, HTTPS, audit log and fingerprints. A real deployment
would be on a secure office server or government cloud with a security audit.
What if OCR or NER misses Everything has a confidence level and goes to a review queue. Officers can add
something? or fix entities by hand.
How would this work with As an analysis layer, through authorised import and export adapters. That needs
CCTNS? official approval and is on the roadmap.
Where is the blockchain? In a hash-chained audit log: editing any entry breaks the chain. A roadmap step
is to anchor a daily hash on a permissioned blockchain.
9.3 Live tests judges may try
Judge says What you do
"Show entities within 3 hops of Suspect X Open Money Trail, pick the account, set ₹5 lakh and 3 hops. Show
with transfers above ₹5 lakh." the Cypher with ALL(...) if asked.
"How exactly are these two people Use the shortest-path search; the path highlights and each link
connected?" opens 'Why this link?'.
"Why was this person flagged?" Open the Lead Advisor: score parts, evidence, missing data.
"What if you merged the wrong people?" Click 'Undo merge'; show the audit log entry.
"Prove the file was not changed." Re-run the SHA-256 check and the 'Verify log' button.
RED FLAGS TO AVOID
● Hard-coded graph results or screenshots instead of a live graph.
● Not being able to explain your matching rules.
● A demo that needs live internet or a slow first load.
● Starting the demo with scanned-PDF OCR, which is the flakiest part.
● Calling anyone a 'criminal' on screen.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 30


<!-- PAGE 31 -->
## Page 31

Risks, Ethics and Law
10
The honest part: what can go wrong and how we handle it
# Risk What could happen Our answer
1 Wrong merge of two Investigation goes in the Officer approval, confidence levels, 'Undo merge',
people wrong direction audit log
2 False flag or bias Unfair suspicion on an 'Lead for review' wording, visible scores, low weight
innocent person for past records, adjustable thresholds
3 Synthetic data looks Judges doubt the demo Add typos, missing fields, duplicates and decoy people
too perfect
4 Too many features Nothing is finished or 3 hero features, a feature freeze one week before the
smooth event
5 OCR or NER mistakes Entities missed or wrong Confidence, review queue, manual edit; demo with
text PDFs
6 Unreadable or slow A messy, slow demo Result caps, filters, indexes, pre-loaded data
graph
7 Learning curve (Neo4j, Delays Learn Neo4j first; small steps; pair up
APIs)
8 Hackathon rules about Disqualification Read each rulebook; keep the Git history; declare
prior work reused parts honestly
9 Privacy and law Loss of trust, legal Roles, audit log, synthetic data; real use needs
problems authorised access and legal review
1 AI-written code nobody Cannot answer judges or Ask AI to explain; own the key logic; test every step
0 understands fix bugs
Ethical principles we follow
● Human decides. The system never takes legal or enforcement action.
● Leads, not verdicts. High importance in a graph does not prove wrongdoing.
● Transparency. Every flag shows its reasons and sources.
● Fairness. Past records are a small, labelled signal; scores are reviewed for bias.
● Minimum data and strict access. Only authorised officers see case data.
LEGAL NOTES
Legal notes (not legal advice). Electronic evidence in India is now handled under the Bharatiya
Sakshya Adhiniyam, 2023 (Section 63 covers electronic records and their certificate), which replaced the
older Section 65B of the Indian Evidence Act. India's data-protection law (the Digital Personal Data
Protection Act, 2023) and police data rules would also matter for a real deployment. Before any real use,
get advice from a lawyer who knows these laws.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 31


<!-- PAGE 32 -->
## Page 32

Future Roadmap
11
Where the project can grow after the hackathon
Stage What we add Notes
Now: prototype The MVP in Part 7, on synthetic data Smooth, honest demo
Next: pilot-ready Hindi and regional OCR, scanned documents, per-case roles, Needs real, authorised
saved views, community detection, geo map from tower sample data
locations
Then: scale Batch ingestion queue, indexes, bigger graph setup, Add Kafka or clusters only if
performance tests on millions of rows tests show a need
Then: intelligence Bigger pattern library, natural-language questions that show Keep explanations visible
the generated Cypher, ML anomaly detection, learning from
officer decisions (with care)
Then: trust Anchor the audit hash on a permissioned blockchain, single Required for real deployment
sign-on, on-premise or government cloud, a security audit
Then: integration Authorised import and export with CCTNS-style systems Needs formal approval
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 32


<!-- PAGE 33 -->
## Page 33

Glossary
12
Every technical word, in one plain line
Term Meaning
FIR First Information Report: the first written record of a crime made at a police station.
CDR Call Detail Record: a telecom file listing who called whom, when and for how long.
KYC Know Your Customer: identity records a bank keeps for an account holder.
Graph A map of things (nodes) joined by links (relationships).
Node One thing in the graph: a person, phone, account, vehicle.
Relationship (edge) A link between two nodes, such as CALLED or TRANSFERRED_TO.
Hop One step along a link. Two hops means a contact of a contact.
Entity Any real-world thing the system tracks: person, phone, account, vehicle, place.
Entity resolution Deciding whether two records describe the same real-world thing.
NER Named Entity Recognition: AI that finds names, places and organisations in text.
Regex A pattern rule for text, such as ten digits for a phone number.
OCR Optical Character Recognition: turns a scanned picture of text into real text.
Centrality A score for how connected or important a node is in the network.
Betweenness How often a node sits on the shortest path between others: a 'bridge' score.
Community Finding groups of nodes that are tightly connected.
detection
Mule account A bank account used to pass on money for someone else.
Shell company A company that exists mainly on paper, often used to hide money.
Fan-in / fan-out Many accounts sending to one account, or one account sending to many.
SHA-256 A fingerprint of a file; changes completely if the file changes.
Hash chain Log entries that each include the previous entry's fingerprint.
RBAC Role-Based Access Control: what you can do depends on your role.
JWT A signed token the server gives after login to prove who you are.
Audit log A record of who did what and when.
Provenance The origin of a fact: which file, page and row it came from.
Cypher The query language of Neo4j.
API A set of web addresses that programs use to talk to each other.
Synthetic data Fake but realistic data created for testing and demos.
Human-in-the-loop A person must check or approve important AI results.
MVP Minimum Viable Product: the smallest version that shows the idea working.
Vibecoding Building software by describing what you want to an AI tool and guiding it step by step.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 33


<!-- PAGE 34 -->
## Page 34

Final Checklist and Sources
13
Before you build, before you present
Before you start building
● Read the rulebook of SIH and of each other hackathon, especially the rule about prior or pre-built work.
● Write the Case #101 story and generate the synthetic data first.
● Install Neo4j, load Case #101 and run the 5 Cypher queries.
● Create a GitHub repository; commit after every working step.
● Agree on the JSON formats between modules before writing code.
Before you present
● The demo runs end to end on a freshly started laptop, without internet.
● You can explain the matching rules, the score parts and the Cypher query in your own words.
● Every screen uses 'lead' and 'potential anomaly', never 'criminal'.
● Slides match the real stack and the real features.
● The README, a 2-minute demo video and a backup of the data are ready.
The whole project in one line
Matching
Knowledge Officer's
Scattered data Extraction (officer Analytics
graph decision
approves)
Sources and notes
● Team documents: SIH26189 skills guide, project architecture notes, the SIH problem analysis and the
UNITx idea presentation.
● Ministry of Home Affairs, status of CCTNS implementation as on 01.02.2026 (Press Information Bureau
document).
● Ministry of Home Affairs reply in the Rajya Sabha on 5 August 2026, reporting that all 17,762 police
stations use CCTNS as of 1 June 2026 (as reported in the news).
● Bharatiya Sakshya Adhiniyam, 2023, Section 63 (electronic records).
● Product descriptions of IBM i2, Palantir Gotham, Chainalysis, Elliptic and Maltego are from public
information and are summarised briefly. Check their current websites before quoting them.
● Tool documentation: Neo4j, Cytoscape.js, spaCy, FastAPI, pandas, NetworkX.
IMPORTANT NOTE
All scores, weights, confidence values and example numbers in this guide are illustrative design choices
for a prototype on synthetic data. They are meant to be tuned and tested, not quoted as measured results.
Case Connect AI | Master Guide | Smart India Hackathon 2026, PS SIH26189 | Team UNITx Page 34

