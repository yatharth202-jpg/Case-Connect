import sys
import json
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.sql import SessionLocal, Entity, EntityLink, MatchSuggestion
from backend.app.services.matching.service import generate_case_matches
from scripts.generate_data import SyntheticDataGenerator

def evaluate_matching_for_seed(seed: int = 42, scenario: str = "ring") -> dict:
    """
    Runs synthetic generator for a seed, stages data to an in-memory or test SQLite DB,
    runs the candidate matching engine, and evaluates precision / recall of HIGH suggestions.
    """
    gen = SyntheticDataGenerator(seed=seed)
    data = gen.build_scenario_data(scenario=scenario, size="small")
    planted = data.get("ground_truth", {}).get("planted", {})
    recruiters = planted.get("recruiters", [])

    print(f"\nEvaluating Seed {seed} (Scenario: {scenario})...")
    print(f"Planted Recruiters: {len(recruiters)}")

    db = SessionLocal()
    case_id = f"eval_case_seed_{seed}"

    # Clean existing for this eval case
    db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id).delete()
    db.query(EntityLink).filter(EntityLink.case_id == case_id).delete()
    db.query(Entity).filter(Entity.case_id == case_id).delete()
    db.commit()

    # Stage recruiter variants
    expected_pairs = set()
    for rec in recruiters:
        r_name = rec["name"]
        r_phone = rec["phone"]
        r_veh = rec["vehicle"]
        parts = r_name.split()
        r_first, r_last = parts[0], parts[-1]

        variants = [
            r_name,
            f"{r_first[0]}. {r_last}",
            f"{r_first} Kumar {r_last}"
        ]

        for i, var in enumerate(variants):
            ent_id = f"ent_rec_{rec['ring_id']}_{i}"
            db.add(Entity(
                id=f"e_{case_id}_{ent_id}",
                case_id=case_id,
                label="Person",
                canonical_id=ent_id,
                display_name=var,
                source_file="FIR_Record",
                source_ref=f"Page {i+1}",
                method="ner",
                confidence=0.85
            ))
            # Link to phone & vehicle
            db.add(EntityLink(
                id=f"el_ph_{case_id}_{ent_id}",
                case_id=case_id,
                source_entity_id=ent_id,
                target_entity_id=r_phone,
                relationship_type="USES",
                source_file="FIR_Evidence",
                source_ref=f"Section {i+1}",
                method="structured",
                confidence=1.0
            ))
            db.add(EntityLink(
                id=f"el_vh_{case_id}_{ent_id}",
                case_id=case_id,
                source_entity_id=ent_id,
                target_entity_id=r_veh,
                relationship_type="DRIVES",
                source_file="FIR_Evidence",
                source_ref=f"Section {i+1}",
                method="structured",
                confidence=1.0
            ))

        # Expected true matching pairs for this recruiter cluster
        expected_pairs.add((f"ent_rec_{rec['ring_id']}_0", f"ent_rec_{rec['ring_id']}_1"))
        expected_pairs.add((f"ent_rec_{rec['ring_id']}_0", f"ent_rec_{rec['ring_id']}_2"))
        expected_pairs.add((f"ent_rec_{rec['ring_id']}_1", f"ent_rec_{rec['ring_id']}_2"))

    # Stage a negative pair: Relatives sharing phone
    rel_phone = gen.generate_phone()
    db.add(Entity(
        id=f"e_{case_id}_rel_1",
        case_id=case_id,
        label="Person",
        canonical_id="ent_rel_1",
        display_name="Rohan Verma",
        source_file="SDR",
        source_ref="Row 10",
        method="structured",
        confidence=1.0
    ))
    db.add(Entity(
        id=f"e_{case_id}_rel_2",
        case_id=case_id,
        label="Person",
        canonical_id="ent_rel_2",
        display_name="Suman Verma",
        source_file="SDR",
        source_ref="Row 11",
        method="structured",
        confidence=1.0
    ))
    db.add(EntityLink(
        id=f"el_rel_1",
        case_id=case_id,
        source_entity_id="ent_rel_1",
        target_entity_id=rel_phone,
        relationship_type="USES",
        source_file="SDR",
        source_ref="Row 10",
        method="structured",
        confidence=1.0
    ))
    db.add(EntityLink(
        id=f"el_rel_2",
        case_id=case_id,
        source_entity_id="ent_rel_2",
        target_entity_id=rel_phone,
        relationship_type="USES",
        source_file="SDR",
        source_ref="Row 11",
        method="structured",
        confidence=1.0
    ))

    db.commit()

    # Run Matcher
    res = generate_case_matches(db, case_id)
    suggestions = db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id).all()

    high_suggestions = [s for s in suggestions if s.level == "HIGH"]
    shared_device_flags = [s for s in suggestions if s.level == "SHARED_DEVICE"]

    found_pairs = set(tuple(sorted([s.entity_a_id, s.entity_b_id])) for s in high_suggestions)
    canonical_expected = set(tuple(sorted(p)) for p in expected_pairs)

    true_positives = len(found_pairs.intersection(canonical_expected))
    false_positives = len(found_pairs - canonical_expected)
    false_negatives = len(canonical_expected - found_pairs)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0

    print("--------------------------------------------------")
    print(f"Total Candidates Evaluated: {res['total_candidates']}")
    print(f"HIGH Match Suggestions:    {len(high_suggestions)}")
    print(f"SHARED_DEVICE Warnings:    {len(shared_device_flags)}")
    print(f"True Positives:             {true_positives} / {len(canonical_expected)}")
    print(f"False Positives:            {false_positives}")
    print(f"False Negatives:            {false_negatives}")
    print(f"PRECISION:                  {precision * 100:.1f}%")
    print(f"RECALL:                     {recall * 100:.1f}%")
    print("--------------------------------------------------")

    # Clean up test rows
    db.query(MatchSuggestion).filter(MatchSuggestion.case_id == case_id).delete()
    db.query(EntityLink).filter(EntityLink.case_id == case_id).delete()
    db.query(Entity).filter(Entity.case_id == case_id).delete()
    db.commit()
    db.close()

    return {
        "seed": seed,
        "precision": precision,
        "recall": recall,
        "true_positives": true_positives,
        "false_positives": false_positives
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Entity Matching on Ground Truth")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--scenario", type=str, default="ring", help="Scenario name")
    args = parser.parse_args()

    evaluate_matching_for_seed(seed=args.seed, scenario=args.scenario)
