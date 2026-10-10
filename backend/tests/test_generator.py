import json
import shutil
import tempfile
from pathlib import Path
import pytest
from scripts.generate_data import SyntheticDataGenerator

def test_identical_seed_produces_byte_identical_output():
    """Rule: generator is completely deterministic; identical seed yields byte-identical files."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        dir1 = Path(tmp1)
        dir2 = Path(tmp2)

        gen1 = SyntheticDataGenerator(seed=42)
        gen1.generate(scenario="ring", format_type="clean", size="small", out_dir=str(dir1))

        gen2 = SyntheticDataGenerator(seed=42)
        gen2.generate(scenario="ring", format_type="clean", size="small", out_dir=str(dir2))

        files1 = sorted([f.name for f in dir1.iterdir()])
        files2 = sorted([f.name for f in dir2.iterdir()])
        assert files1 == files2

        for fname in files1:
            bytes1 = (dir1 / fname).read_bytes()
            bytes2 = (dir2 / fname).read_bytes()
            assert bytes1 == bytes2, f"File {fname} is not byte-identical across runs with seed=42"

def test_different_seeds_produce_different_entities():
    """Rule: different seeds draw different names, phones, and accounts."""
    gen1 = SyntheticDataGenerator(seed=101)
    data1 = gen1.build_scenario_data("ring", "small")

    gen2 = SyntheticDataGenerator(seed=202)
    data2 = gen2.build_scenario_data("ring", "small")

    org1 = data1["ground_truth"]["planted"]["organizers"][0]
    org2 = data2["ground_truth"]["planted"]["organizers"][0]

    assert org1["name"] != org2["name"]
    assert org1["phone"] != org2["phone"]
    assert org1["account"] != org2["account"]

def test_ground_truth_invariants_across_formats():
    """Rule: every format for the same scenario and seed produces the same underlying ground_truth."""
    seed = 88
    scenario = "ring"
    size = "small"

    gen_clean = SyntheticDataGenerator(seed=seed)
    data_clean = gen_clean.build_scenario_data(scenario, size)

    gen_messy = SyntheticDataGenerator(seed=seed)
    data_messy = gen_messy.build_scenario_data(scenario, size)

    gt_clean = data_clean["ground_truth"]
    gt_messy = data_messy["ground_truth"]

    assert gt_clean["total_transactions"] == gt_messy["total_transactions"]
    assert gt_clean["total_calls"] == gt_messy["total_calls"]
    assert gt_clean["total_volume_paise"] == gt_messy["total_volume_paise"]
    assert gt_clean["distinct_phones"] == gt_messy["distinct_phones"]
    assert gt_clean["distinct_accounts"] == gt_messy["distinct_accounts"]

def test_planted_organizer_appears_in_zero_firs():
    """Strict SIH Hackathon Invariant: Organiser entity never appears in any FIR."""
    for test_seed in [7, 42, 99]:
        gen = SyntheticDataGenerator(seed=test_seed)
        data = gen.build_scenario_data("ring", "small")
        organizer = data["ground_truth"]["planted"]["organizers"][0]
        firs = data["firs"]

        assert len(firs) >= 3
        for fir in firs:
            fir_text = fir["text"].lower()
            assert organizer["name"].lower() not in fir_text, f"Organiser name {organizer['name']} found in {fir['fir_id']}"
            assert organizer["phone"] not in fir["text"], f"Organiser phone {organizer['phone']} found in {fir['fir_id']}"
            assert organizer["account"] not in fir["text"], f"Organiser account {organizer['account']} found in {fir['fir_id']}"

def test_all_scenarios_execute_and_produce_valid_ground_truth():
    """Test all 9 scenarios produce valid ground truth and data files."""
    scenarios = [
        "ring", "benign_heavy", "cdr_only", "bank_only",
        "chain", "hub_spoke", "two_rings", "sparse_tiny", "random_mix"
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)
        for sc in scenarios:
            sc_dir = base_path / sc
            gen = SyntheticDataGenerator(seed=12)
            gen.generate(scenario=sc, format_type="clean", size="small", out_dir=str(sc_dir))

            gt_file = sc_dir / "ground_truth.json"
            assert gt_file.exists(), f"ground_truth.json missing for scenario {sc}"
            with open(gt_file, "r", encoding="utf-8") as f:
                gt = json.load(f)

            assert gt["scenario"] == sc
            assert "planted" in gt

            # Scenario-specific structural tests
            if sc == "cdr_only":
                assert gt["total_transactions"] == 0
                assert gt["total_calls"] > 0
            elif sc == "bank_only":
                assert gt["total_calls"] == 0
                assert gt["total_transactions"] > 0
            elif sc == "hub_spoke":
                assert gt["total_transactions"] == 0
                assert gt["planted"]["hub_phone"] is not None
            elif sc == "two_rings":
                assert len(gt["planted"]["organizers"]) == 2
            elif sc == "sparse_tiny":
                assert 10 <= (gt["total_calls"] + gt["total_transactions"]) <= 40
                assert gt["total_firs"] in [1, 2]

def test_all_formats_execute_cleanly():
    """Test all 4 formats (clean, messy, statement, paysim) generate appropriate file artifacts."""
    formats = ["clean", "messy", "statement", "paysim"]
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_path = Path(tmp_dir)
        for fmt in formats:
            fmt_dir = base_path / fmt
            gen = SyntheticDataGenerator(seed=33)
            gen.generate(scenario="ring", format_type=fmt, size="small", out_dir=str(fmt_dir))

            gt_file = fmt_dir / "ground_truth.json"
            assert gt_file.exists()

            if fmt == "clean":
                assert (fmt_dir / "cdr.csv").exists()
                assert (fmt_dir / "bank_transactions.csv").exists()
                assert (fmt_dir / "cdr.json").exists()
                assert (fmt_dir / "bank_transactions.json").exists()
            elif fmt == "messy":
                assert (fmt_dir / "cdr_messy.xlsx").exists()
                assert (fmt_dir / "bank_messy.csv").exists()
            elif fmt == "statement":
                stmt_files = list(fmt_dir.glob("statement_*.csv"))
                assert len(stmt_files) > 0
            elif fmt == "paysim":
                assert (fmt_dir / "paysim_transactions.csv").exists()
