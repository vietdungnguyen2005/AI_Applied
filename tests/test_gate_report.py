import importlib.util
import json
from pathlib import Path

import pytest


def load_reporter():
    path = Path(__file__).resolve().parents[1] / "tools/p13_gate_report.py"
    spec = importlib.util.spec_from_file_location("gate_report", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_skipped_and_failed_gates_never_count_as_passed():
    rows = load_reporter().summarize(
        b'<testsuites><testsuite><testcase classname="a" name="pass"/>'
        b'<testcase classname="a" name="skip"><skipped/></testcase>'
        b'<testcase classname="a" name="fail"><failure/></testcase>'
        b"</testsuite></testsuites>"
    )
    assert [row["status"] for row in rows] == ["passed", "skipped", "failure"]


def test_duplicate_gate_identity_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        load_reporter().summarize(
            b'<testsuites><testsuite><testcase classname="a" name="x"/>'
            b'<testcase classname="a" name="x"/></testsuite></testsuites>'
        )


def test_committed_gate_report_matches_observed_junit():
    root = Path(__file__).resolve().parents[1] / "evals/p13/runs/security-workflow-v1"
    rows = load_reporter().summarize((root / "raw.xml").read_bytes())
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    assert report["cases"] == rows
    assert report["observed_test_cases"] == len(rows) == 33
    assert report["counts"] == {"passed": 33, "skipped": 0, "failure": 0, "error": 0}
    assert report["status"] == "PASS" and all(r["status"] == "passed" for r in rows)
