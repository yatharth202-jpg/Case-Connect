# 25de1c7e-2a2c-451c-9d37-53109fe57782.pdf


> [!WARNING]
> **SUPERSEDED DOCUMENT**: This document contains deprecated claims (e.g. '100% admissible under Section 65B', 'Mastermind', 'auto-link'). Marked as SUPERSEDED as per docs/RULES.md and docs/reference/INDEX.md.


<!-- PAGE 1 -->
## Page 1

AI-POWERED CRIMINAL NETWORK ANALYSIS SYSTEM
BUILD WITH BHARAT 2.0 HACKATHON | ULTIMATE ALL-IN-ONE MASTER DOCUMENT
Problem Statement ID: SIH PS 26189
📌 Document Purpose (Sampurna Project Guide)
Is single document me project ki poori kahani, simple logic, visual diagrams, data pipelines, real vs dummy sources, UI layout, legal
compliance (Section 65B), aur judge Q&A defense included hai. Isko padhne ke baad kisi team member ya judge ko kuch aur
padhne ki zaroorat nahi padegi.
1. Simple Language Me Idea (Police Ki Problem & Hamara Solution)
Asal Problem: Ek sehar me 50 police stations hote hain [cite: 1, 2, 5]. Har station apni FIRs, Call Records (CDR), aur Bank Statements
alag-alag files me rakhta hai [cite: 1, 2, 5]. Agar Station-A ki FIR me likha hai ki robbery me "Black Pulsar" aur nickname "Kala" tha, aur
Station-B ki FIR me bhi "Black Pulsar" thi—to dono stations ko aapas me pata hi nahi chalta [cite: 1, 2]. In hazaron disconnected files se
dots connect karne me police ko 3 se 5 din lag jaate hain [cite: 1, 2, 5].
Hamara Solution: Yeh system ek Centralized AI Brain ki tarah kaam karta hai [cite: 1, 2, 5]. Yeh 50 stations ki saari Hindi/English FIRs,
Phone Call Logs, Bank Transfers, aur Crypto Wallets ko ek saath read karta hai aur screen par ek Visual Map (Network Graph) bana
deta hai [cite: 1, 2, 5]. Jo criminal sabse peeche chup kar sab control kar raha hota hai (Mastermind), system use RED PULSE ALERT ke
sath screen par highlight kar deta hai [cite: 1, 2, 5].
2. Visual Flow Diagrams (Data Se Mastermind Tak)
A. System Diagram (Step-by-Step Mechanism)
┌─────────────────────────┐ ┌──────────────────────────────────┐ ┌────────────────────────────────┐
│ RAW INPUT DATA FILES │ ──► │ STEP 1: KEY-POINT EXTRACTION │ ──► │ STEP 2: LOCATION GRID FILTER │
│ - FIR Copies (PDF/Text) │ │ - Extracted: Location, Time, │ │ - City Grid Map me Time Slot │
│ - Tower Dumps (CSV) │ │ Suspect Names, Vehicles, UPIs │ │ aur Location Wise Sorting │
│ - Bank Stmts (CSV) │ └──────────────────────────────────┘ └────────────────────────────────┘
└─────────────────────────┘ │
▼
┌─────────────────────────┐ ┌──────────────────────────────────┐ ┌────────────────────────────────┐
│ STEP 5: VISUAL OUTPUT │ ◄── │ STEP 4: AI GRAPH & CENTRALITY │ ◄── │ STEP 3: CLUSTER & TOWER MATCH │
│ - Mastermind = RED Node │ │ - Detects Hidden Kingpins │ │ - Common Phone Numbers & Tower │
│ - 65B Hash PDF Audit │ │ (Betweenness Centrality Engine)│ │ Overlaps Cross-Linking │
└─────────────────────────┘ └──────────────────────────────────┘ └────────────────────────────────┘
B. Visual Graph Network Map (Police Screen Par Kaisa Dikh-ega)
[ 🔴 MASTERMIND: PHONE X (Ramesh) ] ◄── (Main Target: Risk Score 96%)
│ │
┌──────────────────┘ └──────────────────┐
│ (Direct Call) │ (Fund Transfer)
▼ ▼
[ 🟡 HANDLER: PHONE Y ] [ 🔵 MULE ACCOUNT A ]
│ │ │
┌────────┘ └────────┐ ▼
▼ ▼ [ 🟢 CRYPTO WALLET HASH ]
[ FIR #452 (Mayur Vihar) ] [ FIR #762 (Preet Vihar) ] (Tornado Cash Mixer)
(Scene: Black Pulsar) (Scene: Black Pulsar)
3. Complete Features Breakdown (Kya Feature Hai & Kaise Kaam Karega)
Feature Name Kaise Kaam Karega (Working Principle)


<!-- PAGE 2 -->
## Page 2

Simple Words Me
Matalab
1. OCR & Multilingual Scanned FIR photo/PDF Hindi aur Hinglish FIR copies se OCR (Tesseract) text extract karta hai, aur NLP engine usme
FIR Parser se text padhna. se Location, Vehicle No, Suspect Alias alag nikal leta hai [cite: 1, 2, 5].
2. Cross-Station Alag-alag station ki FIRs Agar Mayur Vihar FIR aur Preet Vihar FIR me "Black Pulsar" + "Raat 11 PM" common hai, to
Cluster Engine ko jodna. dono ko ek single "Snatching Racket Cluster" me daal deta hai [cite: 1, 2].
3. Tower Dump & CDR Crime spot par active 10,000 call logs me se search karta hai ki kaun sa phone number exact crime time par multiple
Cross-Matcher phones dhoondhna. crime locations par active tha [cite: 2].
4. AI Mastermind Asli Leader ko parda-fash Betweenness Centrality Algorithm dekhta hai ki kis banday ne crime spot par na hote hue bhi
Detector karna. shooters ko call ki aur money distribute ki [cite: 1, 2, 5]. Use RED Node bana deta hai [cite: 2].
5. Hybrid Crypto-Fiat Bank + Crypto transfer
Bank Accounts se lekar Crypto Wallet Hashes tak paisse ke raste ko map karta hai [cite: 5].
Tracker track karna.
6. Section 65B Legal Court ke liye saboot Har uploaded file ka SHA-256 Hash generate karke immutable log banata hai, jisse evidence
Hash Logger pakka karna. tampered na ho [cite: 5].
7. Human-in-the-Loop Police ko full control Police officer galat link Reject kar sakta hai, suspect ki photo edit kar sakta hai, aur custom
Override dena. PDF report export kar sakta hai [cite: 2, 5].
4. Real World Vs Hackathon Data Strategy
Data Type Real Police System (Production) Hackathon Demo Strategy (Dummy Data)
Phone CDR & Tower Telecom Providers (Airtel, Jio) via Police Warrants & Python Faker script generating mock Delhi-NCR Cell Towers &
Logs CEIR Portal [cite: 1]. CDR CSVs [cite: 1, 5].
Bank Statements & Financial Intelligence Unit (FIU-IND) & 1930 Portal APIs Anonymized Kaggle PaySim Mobile Money Fraud Dataset [cite:
Fraud [cite: 1]. 1, 5].
CCTNS (Crime & Criminal Tracking Network) Synthetic Hindi/English FIR PDFs generated via OpenStreetMap
FIR Text Copies
Government Database [cite: 1]. coordinates [cite: 1, 5].
5. Market Comparison & USP (Pehle Se Kaise Alag Hai?)
• Palantir Gotham (US): High-end military tool [cite: 1, 5]. Very expensive hai aur Indian Hindi/Hinglish FIRs handle nahi kar sakta [cite:
1, 5]. Our system is open-source & Indian context ready [cite: 1, 5].
• IBM i2 Analyst's Notebook: Offline software [cite: 1, 5]. Isme har entry manually karni padti hai [cite: 1, 5]. Our system automatically
reads FIRs and auto-syncs across stations [cite: 1, 5].
• CCTNS (India): Sirf static file cabinet ki tarah data store karta hai [cite: 1, 2, 5]. Our system AI Analyst ki tarah dots connect karta hai
[cite: 1, 2, 5].
6. Highly Effective Team & Judge Q&A Defense Strategy
Q1: Hackathon me real police data nahi milta, to aapka system demo me kya dikhayega?
Ans: Humne real-world schema ko replicate karne wala Python Synthetic Generator banaya hai jo Delhi-NCR coordinates par mock CDRs aur
FIRs generate karta hai [cite: 1, 5]. Judges System Architecture, NLP Entity Extraction, aur Neo4j Graph Logic test karte hain, private real data nahi
[cite: 1, 5].
Q2: Criminal fake naam bata de (FIR-1 me 'Ramesh', FIR-2 me 'Kala'), to system use ek kaise samjhega?
Ans: System Multi-Factor Matching Score nikalta hai: (Name Match 50%) + (Phone/IMEI Overlap 100%) + (Tower Location
Overlap 90%) [cite: 1, 2, 5]. Naam alag hone par bhi agar phone number ya IMEI same hai, to system auto-link kar deta hai [cite: 1, 2, 5].
Q3: Cell tower dump me 10,000 aam janta (innocent citizens) hote hain, kya AI sabko criminal dikha dega?
Ans: Bilkul nahi! System me Frequency & Noise Filter hota hai [cite: 2, 5]. Jo banda 1 baar tower par tha, wo auto-drop ho jata hai [cite: 2]. Sirf
wahi numbers highlight hote hain jo multiple crime spots par common the aur jinki call history suspects se linked hai [cite: 2].
Q4: Scanned ya gandi handwriting wali PDF FIRs ko AI kaise padhega?
Ans: Hum OCR (Optical Character Recognition / Tesseract Engine) use karte hain jo image ko digital text me badalta hai, aur Multilingual
IndicBERT model usme se key details JSON format me extract karta hai [cite: 1, 2, 5].


<!-- PAGE 3 -->
## Page 3

Q5: Court me yeh evidence kaise valid hoga? Digital evidence me tampering ka risk rehta hai.
Ans: System har uploaded file ka instant SHA-256 Cryptographic Hash create karke log kar deta hai [cite: 5]. Court report me timestamped
certificate milta hai jo **Section 65B Indian Evidence Act** ke under 100% admissible hai [cite: 5].
Q6: On-the-spot Judge test scenario: Agar judge bole ki live 3-hop links filter karke dikhao, to kya karenge?
Ans: Humne backend me dynamic Neo4j Cypher Query integrate ki hai: MATCH (p:Person {id:'X'})-[r:TRANSFERRED*1..3]-
>(target) WHERE r.amount > 500000 RETURN p, r, target [cite: 5]. Yeh query 2 seconds me live graph update karke dikha deti hai
[cite: 5].

