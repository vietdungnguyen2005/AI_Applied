"""Recompute an archived P13 tool-selection measurement without model inference."""

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from vmarket_ai.evaluation.tool_questions import (
    DATASET,
    ROOT,
    aggregate,
    score,
    scoring_labels,
    verify_inputs,
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def verify(directory: Path) -> None:
    inputs, lock = verify_inputs(require_original_planner=False)
    labels = scoring_labels(inputs)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    expected_files = {
        "config.json",
        "raw.jsonl",
        "report.json",
        "summary.csv",
        "review-template.jsonl",
    }
    if set(manifest["files_sha256"]) != expected_files:
        raise ValueError("Unexpected tool artifact inventory")
    for name, expected in manifest["files_sha256"].items():
        if digest((directory / name).read_bytes()) != expected:
            raise ValueError("Tool artifact bytes changed: " + name)
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    commit = config["source_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or manifest["source_commit"] != commit:
        raise ValueError("Invalid source revision")
    if (
        config["dataset_lock_sha256"] != digest((DATASET / "lock.json").read_bytes())
        or config["dataset_file_hashes"] != lock["files_sha256"]
    ):
        raise ValueError("Tool dataset lock mismatch")
    for name in ("inputs.jsonl", "labels.jsonl", "protocol.json", "lock.json"):
        historical = subprocess.check_output(
            ["git", "show", commit + ":evals/p13/tool-questions-v1/" + name], cwd=ROOT
        )
        if historical != (DATASET / name).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("Tool dataset differs from preregistration commit")
    for name, key in (
        ("src/vmarket_ai/gateway/agent.py", "agent_sha256_lf"),
        ("src/vmarket_ai/gateway/wire.json", "wire_sha256_lf"),
    ):
        historical = subprocess.check_output(["git", "show", commit + ":" + name], cwd=ROOT)
        if digest(historical) != lock[key]:
            raise ValueError("Historical planner differs from preregistration lock")
    scorer_name = "src/vmarket_ai/evaluation/tool_questions.py"
    historical_scorer = subprocess.check_output(
        ["git", "show", commit + ":" + scorer_name], cwd=ROOT
    )

    def scoring_nodes(source: bytes) -> list[str]:
        nodes = ast.parse(source).body
        return [
            ast.dump(node, include_attributes=False)
            for node in nodes
            if not (isinstance(node, ast.FunctionDef) and node.name == "verify_inputs")
            and not isinstance(node, ast.If)
        ]

    if scoring_nodes(historical_scorer) != scoring_nodes((ROOT / scorer_name).read_bytes()):
        raise ValueError("Scorer differs from preregistration commit")
    source = subprocess.check_output(
        ["git", "show", commit + ":src/vmarket_ai/gateway/agent.py"], cwd=ROOT
    )
    prompts = [
        ast.literal_eval(node.value)
        for node in ast.parse(source).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SYSTEM" for target in node.targets)
    ]
    if (
        len(prompts) != 1
        or digest(prompts[0].encode("utf-8")) != config["parameters"]["system_prompt_sha256"]
    ):
        raise ValueError("Planner prompt provenance mismatch")
    protocol = json.loads((DATASET / "protocol.json").read_text(encoding="utf-8"))
    if config["model"]["digest"] != protocol["model_digest"]:
        raise ValueError("Model digest differs from protocol")
    raw = [
        json.loads(line)
        for line in (directory / "raw.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    expected = {
        (case["id"], method)
        for case in inputs
        for method in ("deterministic_fake_router", "local_qwen_router")
    }
    identities = [(row["case_id"], row["method"]) for row in raw]
    if (
        len(identities) != len(expected)
        or set(identities) != expected
        or len(report["predictions"]) != len(raw)
        or manifest["records"] != len(raw)
    ):
        raise ValueError("Planner results missing, repeated, or not preregistered")
    scored = []
    for raw_row, recorded in zip(raw, report["predictions"], strict=True):
        if raw_row != {key: value for key, value in recorded.items() if key != "score"}:
            raise ValueError("Raw and scored planner output differ")
        computed = score(raw_row, labels[raw_row["case_id"]])
        if computed != recorded["score"]:
            raise ValueError("Planner score differs")
        scored.append({**raw_row, "score": computed})
    metrics = aggregate(scored)
    if metrics != report["metrics"]:
        raise ValueError("Planner aggregate differs")
    with (directory / "summary.csv").open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    if csv_rows != [
        {key: "" if value is None else str(value) for key, value in row.items()} for row in metrics
    ]:
        raise ValueError("Planner summary differs")
    review = [
        json.loads(line)
        for line in (directory / "review-template.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    cases = {item["id"]: item for item in inputs}
    fields = {
        "case_id",
        "question",
        "scope",
        "review_status",
        "reviewer",
        "reviewed_at",
        "independent_expected_kind",
        "independent_expected_tool",
        "independent_expected_arguments",
        "notes",
    }
    if len(review) != len(cases) or {row.get("case_id") for row in review} != set(cases):
        raise ValueError("Planner review template case inventory mismatch")
    for row in review:
        case = cases[row["case_id"]]
        if (
            set(row) != fields
            or row["question"] != case["question"]
            or row["scope"] != case["scope"]
            or row["review_status"] != "PENDING_INDEPENDENT_REVIEW"
            or any(
                row[name] is not None
                for name in fields - {"case_id", "question", "scope", "review_status"}
            )
        ):
            raise ValueError("Planner review template is not blind and pending")
    print(
        json.dumps(
            {
                "status": "PASS",
                "cases": len(inputs),
                "predictions": len(raw),
                "source_commit": commit,
                "independent_review": "pending",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    verify(parser.parse_args().artifact)
