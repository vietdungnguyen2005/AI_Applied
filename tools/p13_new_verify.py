"""Verify a recorded P13 new-question run without inference or network access."""

import argparse
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

from vmarket_ai.evaluation.new_questions import DATASET, ROOT, scoring_labels, verify_inputs
from vmarket_ai.evaluation.new_score import aggregate, score_qa, score_retrieval


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(report_path: Path, journal_path: Path, summary_path: Path) -> None:
    inputs, _ = verify_inputs()
    labels = scoring_labels(inputs)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report["dataset_lock_sha256"] != digest(DATASET / "lock.json"):
        raise ValueError("Dataset lock mismatch")
    commit = report["source_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid preregistration revision")
    for name in ("inputs.jsonl", "labels.jsonl", "protocol.json", "lock.json"):
        historical = subprocess.check_output(
            ["git", "show", commit + ":evals/p13/new-questions-v1/" + name], cwd=ROOT
        )
        if historical != (DATASET / name).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("Inputs or labels differ from preregistration commit")
    source = subprocess.check_output(
        ["git", "show", commit + ":src/vmarket_ai/evaluation/new_score.py"], cwd=ROOT
    )
    current = (ROOT / "src/vmarket_ai/evaluation/new_score.py").read_bytes().replace(b"\r\n", b"\n")
    if source != current:
        raise ValueError("Scoring implementation changed after preregistration")
    if digest(journal_path) != report["journal_sha256"]:
        raise ValueError("Raw prediction journal hash mismatch")
    raw = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    predictions = report["predictions"]
    expected = {
        (case["id"], domain, method)
        for case in inputs
        for domain, methods in (
            ("qa", ("signed_dense_local", "empty_evidence_guard")),
            ("retrieval", ("lexical", "dense", "hybrid")),
        )
        for method in methods
    }
    identities = [(r["case_id"], r["domain"], r["method"]) for r in raw]
    if (
        len(identities) != len(expected)
        or set(identities) != expected
        or len(predictions) != len(raw)
    ):
        raise ValueError("Predictions are missing, repeated, or not preregistered")
    scored = []
    for source_row, recorded in zip(raw, predictions, strict=True):
        if source_row != {k: v for k, v in recorded.items() if k != "score"}:
            raise ValueError("Raw and scored prediction differ")
        score = (
            score_qa(source_row, labels[source_row["case_id"]])
            if source_row["domain"] == "qa"
            else score_retrieval(source_row, labels[source_row["case_id"]])
        )
        if score != recorded["score"]:
            raise ValueError("Recorded per-case score differs")
        scored.append({**source_row, "score": score})
    metrics = aggregate(
        [r for r in scored if r["domain"] == "qa"],
        [r for r in scored if r["domain"] == "retrieval"],
    )
    if metrics != report["metrics"]:
        raise ValueError("Aggregate score differs")
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        summary = list(csv.DictReader(handle))
    expected_summary = [
        {key: "" if value is None else str(value) for key, value in row.items()} for row in metrics
    ]
    if summary != expected_summary:
        raise ValueError("Summary CSV differs")
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


def verify_manifest(directory: Path) -> None:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    names = {"config.json", "report.json", "raw.jsonl", "summary.csv", "review-template.jsonl"}
    if set(manifest["files_sha256"]) != names:
        raise ValueError("Unexpected artifact file set")
    for name, expected in manifest["files_sha256"].items():
        if digest(directory / name) != expected:
            raise ValueError("Artifact bytes changed: " + name)
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    if (
        manifest["source_commit"] != report["source_commit"]
        or config["source_commit"] != report["source_commit"]
        or config["model"] != report["model"]
        or config["parameters"] != report["parameters"]
        or config["input_hashes"] != report["input_hashes"]
        or config["dataset_lock_sha256"] != report["dataset_lock_sha256"]
        or manifest["records"] != len(report["predictions"])
    ):
        raise ValueError("Artifact provenance mismatch")
    inputs, _ = verify_inputs()
    expected_inputs = {item["id"]: item for item in inputs}
    review = [
        json.loads(line)
        for line in (directory / "review-template.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    fields = {
        "case_id",
        "question",
        "collection",
        "language",
        "review_status",
        "reviewer",
        "reviewed_at",
        "independent_expected_status",
        "independent_relevant_sources",
        "independent_answer_reference",
        "notes",
    }
    if len(review) != len(expected_inputs) or {r.get("case_id") for r in review} != set(
        expected_inputs
    ):
        raise ValueError("Review template case inventory mismatch")
    for row in review:
        source = expected_inputs[row["case_id"]]
        if (
            set(row) != fields
            or row["question"] != source["question"]
            or row["collection"] != source["collection"]
            or row["language"] != source["language"]
            or row["review_status"] != "PENDING_INDEPENDENT_REVIEW"
            or any(
                row[name] is not None
                for name in fields
                - {"case_id", "question", "collection", "language", "review_status"}
            )
        ):
            raise ValueError("Review template is not blind and pending")
    sources = {
        "src/vmarket_ai/ingestion/spec.py",
        "src/vmarket_ai/providers/local_e5.py",
        "src/vmarket_ai/providers/ollama.py",
        "src/vmarket_ai/qa/backend.py",
        "src/vmarket_ai/qa/service.py",
        "src/vmarket_ai/retrieval/spec.py",
        "src/vmarket_ai/evaluation/new_score.py",
    }
    if set(config["source_files_sha256_lf"]) != sources:
        raise ValueError("Unexpected source implementation set")
    for name, expected in config["source_files_sha256_lf"].items():
        code = subprocess.check_output(
            ["git", "show", report["source_commit"] + ":" + name], cwd=ROOT
        )
        if hashlib.sha256(code).hexdigest() != expected:
            raise ValueError("Source provenance mismatch")
    code = subprocess.check_output(
        ["git", "show", report["source_commit"] + ":src/vmarket_ai/qa/service.py"], cwd=ROOT
    )
    tree = ast.parse(code)
    prompts = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SYSTEM" for target in node.targets)
    ]
    if (
        len(prompts) != 1
        or hashlib.sha256(prompts[0].encode("utf-8")).hexdigest()
        != report["parameters"]["qa_system_prompt_sha256"]
    ):
        raise ValueError("QA prompt provenance mismatch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--artifact", type=Path, help="Packaged run to verify")
    args = parser.parse_args()
    if args.artifact:
        verify_manifest(args.artifact)
        verify(
            args.artifact / "report.json",
            args.artifact / "raw.jsonl",
            args.artifact / "summary.csv",
        )
    elif args.report and args.journal and args.summary:
        verify(args.report, args.journal, args.summary)
    else:
        parser.error("Provide --artifact, or all of --report, --journal, and --summary")
