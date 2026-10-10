import tempfile
from pathlib import Path
from scripts.audit_hardcode import scan_file, run_audit

def test_audit_passes_on_clean_code():
    assert run_audit() is True

def test_audit_catches_planted_mobile_literal():
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tf:
        tf.write('def check():\n    phone = "9876543210"\n')
        tf_path = Path(tf.name)
    try:
        findings = scan_file(tf_path, set())
        assert len(findings) > 0
        assert any("Hardcoded mobile number" in f[2] for f in findings)
    finally:
        tf_path.unlink()

def test_audit_catches_planted_prejudicial_term():
    with tempfile.NamedTemporaryFile("w+", suffix=".js", delete=False) as tf:
        tf.write('const label = "suspect profile";\n')
        tf_path = Path(tf.name)
    try:
        findings = scan_file(tf_path, set())
        assert len(findings) > 0
        assert any("Forbidden prejudicial terminology" in f[2] for f in findings)
    finally:
        tf_path.unlink()

def test_audit_catches_planted_mock_data_file():
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
        tf.write('{"sample": "data"}')
        tf_path = Path(tf.name)
    try:
        findings = scan_file(tf_path, set())
        assert len(findings) > 0
        assert any("Mock data file detected" in f[2] for f in findings)
    finally:
        tf_path.unlink()
