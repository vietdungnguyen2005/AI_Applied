import importlib.util
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
