"""Add a blank blind-review template to a complete preregistered planner run."""

import argparse
import hashlib
import json
from pathlib import Path

from p13_tool_verify import verify

from vmarket_ai.evaluation.tool_questions import verify_inputs


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(run: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Output must be a fresh directory")
    original = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    names = {"config.json", "raw.jsonl", "report.json", "summary.csv"}
    if set(original["files_sha256"]) != names:
        raise ValueError("Unexpected source run inventory")
    for name, expected in original["files_sha256"].items():
        if digest(run / name) != expected:
            raise ValueError("Source run bytes changed: " + name)
    inputs, _ = verify_inputs()
    output.mkdir(parents=True)
    for name in sorted(names):
        (output / name).write_bytes((run / name).read_bytes())
    with (output / "review-template.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for case in inputs:
            row = {
                "case_id": case["id"],
                "question": case["question"],
                "scope": case["scope"],
                "review_status": "PENDING_INDEPENDENT_REVIEW",
                "reviewer": None,
                "reviewed_at": None,
                "independent_expected_kind": None,
                "independent_expected_tool": None,
                "independent_expected_arguments": None,
                "notes": None,
            }
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    original["files_sha256"]["review-template.jsonl"] = digest(output / "review-template.jsonl")
    (output / "manifest.json").write_text(
        json.dumps(original, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    verify(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.run, args.output)
