# Case Connect AI — Reference Documents Index & Authority Hierarchy

This index catalogues all project reference documents and specifies the strict hierarchy of authority when interpreting requirements, architecture, legal standards, and scoring logic.

---

## 1. Hierarchy of Authority

1. **Top Authority (Level 1)**: User Instructions in active chat & [`docs/RULES.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/RULES.md).
   - Non-negotiable principles (no hardcoded data, no mock paths, human-in-the-loop, SQLite as source of truth, explainable scoring).
   - If any lower-level document contradicts Level 1, **Level 1 wins unconditionally**.
2. **System Specification (Level 2)**: [`Case_Connect_AI_Master_Guide.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/reference/Case_Connect_AI_Master_Guide.md).
   - Core product definition (3 Hero Features, 14 Core Features, 7-step pipeline, court Section 63 BSA 2023 compliance).
3. **Architecture Specification (Level 3)**: [`SIH26189_Complete_Project_Architecture.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/reference/SIH26189_Complete_Project_Architecture.md).
   - Technical service layer, Neo4j graph model, RBAC and module breakdown.
4. **Skills Matrix (Level 4)**: [`SIH26189_Skills_Required.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/reference/SIH26189_Skills_Required.md).
   - Learning order, tools division, and tech stack focus.
5. **Format Reference Only (Level 5)**: [`SIH26189_Sample_Demo_Data.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/reference/SIH26189_Sample_Demo_Data.md).
   - **CRITICAL NOTE**: Strictly a format reference for test generators (`scripts/generate_data.py`). Its names, phone numbers, account IDs, and dates must **NEVER** be copied into application code, UI components, or seeded database records.

---

## 2. Superseded / Deprecated Documents

* **[`docs/reference/25de1c7e_superseded_master_document.md`](file:///c:/Users/Anshuman%20Singh/AI-Crime-Analyser-%28v1.0%29/docs/reference/25de1c7e_superseded_master_document.md)** (`25de1c7e-2a2c-451c-9d37-53109fe57782.pdf`)
  - **Status**: **SUPERSEDED / DEPRECATED**.
  - **Reason**: Contains disallowed terms and claims conflicting with `RULES.md` and Indian legal standards, including:
    - Prejudicial labels such as *"Mastermind"* and *"Criminal"* (Replaced with *"Lead for review"* and *"Potential anomaly"*).
    - Unrealistic legal claims such as *"100% admissible under Section 65B"* (Section 65B has been replaced by Section 63 of the Bharatiya Sakshya Adhiniyam, 2023; admissibility is determined by the court).
    - Automatic merges without officer consent (*"auto-link"* without human review).
    - Hardcoded risk percentages (*"Risk Score 96%"*).
  - This document is retained for historical traceability only and is **NOT** used for architectural or investigative logic decisions.

---

## 3. Reference Files Catalog

| Original File | Markdown Conversion | Status | Pages |
|---|---|:---:|:---:|
| `Case_Connect_AI_Master_Guide (1).pdf` | `Case_Connect_AI_Master_Guide.md` | Active (Level 2) | 34 |
| `SIH26189_Complete_Project_Architecture.pdf` | `SIH26189_Complete_Project_Architecture.md` | Active (Level 3) | 6 |
| `SIH26189_Sample_Demo_Data.pdf` | `SIH26189_Sample_Demo_Data.md` | Active (Format only) | 4 |
| `SIH26189_Skills_Required.pdf` | `SIH26189_Skills_Required.md` | Active (Level 4) | 3 |
| `25de1c7e-2a2c-451c-9d37-53109fe57782.pdf` | `25de1c7e_superseded_master_document.md` | **SUPERSEDED** | 3 |
