# SIH26189_Skills_Required.pdf


<!-- PAGE 1 -->
## Page 1

SIH26189 – Skills Required
AI-Powered Criminal Network Analysis System
You do not need expert-level knowledge of every technology. Divide the project across the team. The
main focus is Web Development + Graph Database + NLP + Graph Analytics.
Skill Importance Level
React / Frontend HHHH Good
Node.js / Backend APIs HHHH Good
Database HHHH Good
Neo4j / Graph DB HHHHH Basic–Intermediate
Python HHHH Basic–Intermediate
NLP / AI HHHH Basic
Graph Algorithms HHHH Basic
PDF/CSV Processing HHH Basic
Authentication HHH Basic
Git/GitHub HHH Good
1. Frontend – React
Know API integration, forms, tables, charts, search/filter, authentication UI and graph visualization.
Cytoscape.js is a good choice for the investigation graph.
2. Backend
Node.js/Express is sufficient. Understand REST APIs and how the backend connects the frontend with
Neo4j and other services.
3. Neo4j – Most Important New Skill
Learn nodes, relationships, properties and basic Cypher. Example: Person USES Phone, Person OWNS
BankAccount, BankAccount TRANSFERRED_TO BankAccount. Multi-hop queries are central.
4. Python
One member should know Python basics, JSON/file handling, pandas and simple data processing for the
NLP/data pipeline.
5. NLP / AI
Learn Named Entity Recognition (NER) to extract PERSON, PHONE, MONEY, BANK ACCOUNT and
similar entities from FIR text. No need to train an AI model from scratch.
6. Entity Resolution
Understand name similarity, fuzzy matching, shared identifiers and confidence scores. Possible matches
should preferably require investigator approval.


<!-- PAGE 2 -->
## Page 2

7. Graph Algorithms
Know Degree Centrality, Betweenness Centrality and PageRank at a basic level. These identify highly
connected/central entities, not proof of criminality.
8. Transaction Analysis
Process CSV transactions and trace money flows such as Bank A fi Bank B fi Bank C fi Crypto Wallet.
Basic pandas and Neo4j knowledge is enough.
9. PDF Processing
Pipeline: PDF fi text fi NLP fi entities fi Neo4j. Useful Python libraries include PyMuPDF/pdfplumber
and spaCy.
10. Security
Know authentication, role-based access, password hashing, HTTPS, audit logs, input/file validation and
SHA-256. Suggested roles: Admin, Investigator, Viewer.
11. Data Structures
Be comfortable with JSON, lists/dictionaries and the graph model: Nodes + Edges + Properties.
12. Git/GitHub
Use branches, pull requests, merges and basic team collaboration.
13. Recommended Team Division
Member Responsibility Skills
1 Frontend React, Tailwind, Cytoscape.js
2 Backend Node.js, Express, APIs, Auth
3 AI/NLP Python, NER, Entity Resolution
4 Graph Neo4j, Cypher, Graph Algorithms
5 Data/Analytics Pandas, Transactions, Centrality, Synthetic Data
6 Integration Integration, testing, PPT, demo, documentation
14. What You Do NOT Need to Learn Deeply
(cid:127) Deep Learning from scratch
(cid:127) Neural-network mathematics
(cid:127) Advanced TensorFlow/PyTorch
(cid:127) Advanced statistics
(cid:127) Blockchain development
(cid:127) Advanced cybersecurity
(cid:127) Training a huge LLM from scratch
(cid:127) Computer vision


<!-- PAGE 3 -->
## Page 3

15. Personal Learning Order
1. Neo4j + Cypher
2. Graph concepts
3. Cytoscape.js
4. Node.js API
5. Python basics
6. NLP / NER
7. Entity Resolution
8. Transaction analysis
9. Authentication + audit
10. Full integration
Key Takeaway
If you already know React + Node.js, focus first on Neo4j, Cypher, Cytoscape.js, NLP/NER, entity
resolution and graph algorithms.

