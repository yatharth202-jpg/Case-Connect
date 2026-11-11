# Extraction Module V2 — Accuracy & Forensic Evaluation Report

**Date:** 2026-11-11T17:15:43.643460+00:00  
**Extractor Version:** `v2.0.0+cfg.ddd0d5ac.fitz.2.1.pn.9.0.43.pyd.2.14.3.sa.2.1.8`  
**Legal Standard:** Bharatiya Sakshya Adhiniyam, 2023 (BSA Section 63)  
**Benchmark Source:** Automated Synthetic Truth Set + High-Resolution Reference Corpus  

---

## 1. Entity Extraction Precision, Recall & F1 Scores

| Entity Identifier Type | Expected | Extracted | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1 Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AADHAAR** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **BANK_ACCOUNT** | 20 | 20 | 20 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **IFSC** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **IMEI** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **PAN** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **PHONE** | 25 | 25 | 25 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **UPI** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **VEHICLE** | 10 | 10 | 10 | 0 | 0 | 100.0% | 100.0% | **1.000** |
| **OVERALL COMPOSITE** | — | — | **105** | **0** | **0** | **100.0%** | **100.0%** | **1.000** |

---

## 2. Ingestion & Tabular Parsing Performance

- **Total Rows Evaluated:** 500
- **Successfully Parsed Rows:** 492 (**98.40%**)
- **Rejected Rows (Header / Corrupted / Non-Forensic):** 8 (**1.60%**)
- **Monetary Arithmetic:** 100% Integer Paise (`amount_paise`), zero floating point drift.
- **Natural Key Deduplication:** Exact SHA-256 fingerprinting on tuple `(case_id, record_type, natural_key, occurrence_idx)`.

---

## 3. Optical Character Recognition (OCR) Confidence Quality Gate

- **Mean Word Confidence:** **88.4%**
- **High-Confidence Words (Conf >= 0.70):** 92.4% (Auto-accepted with page provenance)
- **Low-Confidence Word Flagging (Conf < 0.70):** 7.6% (Queued for officer visual review)
- **Handwriting Review Capping:** Confidences strictly capped at `handwritten_conf_cap` (0.50) to prevent unreviewed automated merges.

---

## 4. Statutory Compliance Verification

1. **Zero Prejudicial Terminology:** Verified across 100% of generated labels, error messages, and review queues. Only objective mathematical labels (`Format valid — ownership unverified`, `Potential Anomaly`) are surfaced.
2. **Audited PII Unmasking:** 100% of unmasking requests strictly require statutory justification under Section 63 BSA 2023 and record immutable SHA-256 genesis-chained audit entries.
3. **Air-Gap Guarantee:** No external network endpoints contacted during parsing, validation, OCR, or NLP entity recognition.

