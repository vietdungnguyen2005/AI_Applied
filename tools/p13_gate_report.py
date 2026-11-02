"""Summarize actual pytest JUnit gates; these are software regressions, not AI quality."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(raw: bytes) -> list[dict[str, str]]:
    cases = ET.fromstring(raw).findall(".//testcase")
    if not cases:
        raise ValueError("No observed test cases")
    rows = []
    seen = set()
    for case in cases:
        identity = (case.attrib["classname"], case.attrib["name"])
        if identity in seen:
            raise ValueError("Duplicate test identity")
        seen.add(identity)
        status = "passed"
        for tag in ("skipped", "failure", "error"):
            if case.find(tag) is not None:
                status = tag
        rows.append({"suite": identity[0], "case": identity[1], "status": status})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.junit.read_bytes()
    rows = summarize(raw)
    root = Path(__file__).resolve().parents[1]
    config = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "measurement": "existing deterministic security and workflow regression gates",
        "model_calls": 0,
        "independent_human_review": "not performed",
        "end_to_end_java_business_authorization": "not measured by these Python gates",
        "files_sha256_lf": {
            name: hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in (
                "tests/test_gateway.py",
                "tests/test_runs.py",
                "tests/test_signed_qa_postgres.py",
                "tools/p13_gate_report.py",
            )
        },
    }
    report = {
        "status": "PASS" if all(r["status"] == "passed" for r in rows) else "INCOMPLETE_OR_FAILED",
        "counts": {
            s: sum(r["status"] == s for r in rows)
            for s in ("passed", "skipped", "failure", "error")
        },
        "observed_test_cases": len(rows),
        "cases": rows,
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "raw.xml").write_bytes(raw)
    for name, value in (("config.json", config), ("report.json", report)):
        (args.output / name).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    sink = io.StringIO(newline="")
    writer = csv.DictWriter(sink, fieldnames=("suite", "case", "status"), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    (args.output / "summary.csv").write_text(sink.getvalue(), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}))


if __name__ == "__main__":
    main()
