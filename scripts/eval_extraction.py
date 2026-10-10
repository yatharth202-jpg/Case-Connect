#!/usr/bin/env python3
"""
Case Connect AI — Document NLP Extraction Evaluation Script (Phase 6)
Evaluates precision and recall across extracted entity types.
"""
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.extraction.text import read_document_text
from backend.app.services.extraction.rules import extract_rule_entities
from backend.app.services.extraction.ner import extract_ner_entities

def evaluate_sample_text(sample_text: str, ground_truth: dict) -> dict:
    """
    Evaluates rule and NER extraction against expected ground truth entities.
    Returns precision, recall, and F1 metrics per entity category.
    """
    rule_items = extract_rule_entities(sample_text, "Page 1")
    existing_spans = [(r["char_span_start"], r["char_span_end"]) for r in rule_items]
    ner_items = extract_ner_entities(sample_text, "Page 1", existing_spans=existing_spans)
    all_extracted = rule_items + ner_items

    extracted_by_type = {}
    for item in all_extracted:
        t = item["entity_type"]
        extracted_by_type.setdefault(t, set()).add(item["normalized_value"])

    results = {}
    for ent_type, expected_vals in ground_truth.items():
        expected_set = set(str(v).lower() for v in expected_vals)
        actual_set = set(str(v).lower() for v in extracted_by_type.get(ent_type, []))

        tp = len(actual_set.intersection(expected_set))
        fp = len(actual_set - expected_set)
        fn = len(expected_set - actual_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected_set else 0.0)
        recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if not expected_set else 0.0)
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        results[ent_type] = {
            "expected": len(expected_set),
            "extracted": len(actual_set),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3)
        }

    return results

def main():
    parser = argparse.ArgumentParser(description="Evaluate text extraction performance.")
    parser.add_argument("--file", type=str, help="Path to document file to test")
    args = parser.parse_args()

    print("==================================================")
    print("  CASE CONNECT AI — EXTRACTION EVALUATION BENCHMARK")
    print("==================================================")

    # Benchmark test fixture
    benchmark_text = """
    FIRST INFORMATION REPORT
    FIR No. 142/2024 dated 14/03/2024 at Police Station Cyber Crime, New Delhi.
    Complainant Shri Rajesh Sharma reported that an unknown caller using mobile +91 9876543210
    induced him to transfer an amount of Rs 2,50,000 into Bank Account 112233445566 at State Bank of India.
    The accused person named Vikram Verma fled in vehicle DL01AB1234.
    A partial account ending 4321 was also mentioned in SMS logs.
    """

    ground_truth = {
        "PHONE": ["98765" + "43210"],
        "BANK_ACCOUNT": ["112233" + "445566"],
        "VEHICLE": ["DL01AB1234"],
        "AMOUNT": ["25000000"],
        "PERSON": ["rajesh sharma", "vikram verma"],
        "FIR": ["142/2024"],
        "ACCOUNT_SUFFIX": ["ending_4321"]
    }

    test_text = benchmark_text
    if args.file and Path(args.file).exists():
        doc = read_document_text(args.file)
        if doc.get("full_text"):
            test_text = doc["full_text"]

    metrics = evaluate_sample_text(test_text, ground_truth)

    print(f"{'ENTITY TYPE':<18} | {'EXP':<5} | {'ACT':<5} | {'TP':<4} | {'PRECISION':<10} | {'RECALL':<8} | {'F1':<6}")
    print("-" * 70)
    for etype, m in metrics.items():
        print(f"{etype:<18} | {m['expected']:<5} | {m['extracted']:<5} | {m['tp']:<4} | {m['precision']:<10.3f} | {m['recall']:<8.3f} | {m['f1']:<6.3f}")
    print("==================================================")

if __name__ == "__main__":
    main()
