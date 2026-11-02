"""Package every recorded P13 new-question prediction and recompute its scores."""

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from p13_new_verify import verify

from vmarket_ai.evaluation.new_questions import DATASET, ROOT, read_rows
from vmarket_ai.ingestion.spec import E5_PROFILE
from vmarket_ai.providers.local_e5 import PINNED_HASHES
from vmarket_ai.retrieval.spec import RetrievalConfig


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package(report_path: Path, journal_path: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Output must be a fresh directory")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("journal_file") != journal_path.name:
        raise ValueError("Journal is not the one recorded by the run")
    output.mkdir(parents=True)
    # JSON is a Git-managed text artifact; preserve semantic content with portable LF bytes.
    (output / "report.json").write_bytes(report_path.read_bytes().replace(b"\r\n", b"\n"))
    (output / "raw.jsonl").write_bytes(journal_path.read_bytes())
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["domain", "method", "metric", "value", "n"], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(report["metrics"])
    verify(output / "report.json", output / "raw.jsonl", output / "summary.csv")
    inputs = {r["id"]: r for r in read_rows(DATASET / "inputs.jsonl")}
    with (output / "review-template.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for case_id in sorted(inputs):
            row = {
                "case_id": case_id,
                "question": inputs[case_id]["question"],
                "collection": inputs[case_id]["collection"],
                "language": inputs[case_id]["language"],
                "review_status": "PENDING_INDEPENDENT_REVIEW",
                "reviewer": None,
                "reviewed_at": None,
                "independent_expected_status": None,
                "independent_relevant_sources": None,
                "independent_answer_reference": None,
                "notes": None,
            }
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    source_hashes = {}
    for name in (
        "src/vmarket_ai/ingestion/spec.py",
        "src/vmarket_ai/providers/local_e5.py",
        "src/vmarket_ai/providers/ollama.py",
        "src/vmarket_ai/qa/backend.py",
        "src/vmarket_ai/qa/service.py",
        "src/vmarket_ai/retrieval/spec.py",
        "src/vmarket_ai/evaluation/new_score.py",
    ):
        code = subprocess.check_output(
            ["git", "show", report["source_commit"] + ":" + name], cwd=ROOT
        )
        if code != (ROOT / name).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("Embedding implementation changed between run and packaging")
        source_hashes[name] = hashlib.sha256(code).hexdigest()
    config = {
        "source_commit": report["source_commit"],
        "dataset": report["dataset"],
        "dataset_lock_sha256": report["dataset_lock_sha256"],
        "input_hashes": report["input_hashes"],
        "model": report["model"],
        "parameters": report["parameters"],
        "embedding_profile": E5_PROFILE.model_dump(mode="json"),
        "embedding_pinned_files_sha256": PINNED_HASHES,
        "retrieval_config": RetrievalConfig().model_dump(mode="json"),
        "source_files_sha256_lf": source_hashes,
        "retrieval_as_of_utc": report["retrieval_as_of_utc"],
        "actual_run_at_utc": report["timestamp_utc"],
        "packaged_at_utc": datetime.now(UTC).isoformat(),
        "scope": report["scope"],
        "baseline": report["baseline"],
        "label_review": report["label_review"],
        "external_provider_calls": report["external_provider_calls"],
        "compute_and_energy_cost": report["compute_and_energy_cost"],
        "token_usage": report["token_usage"],
    }
    (output / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    manifest = {
        "status": "completed_provisional_new_questions_not_independent_holdout",
        "source_commit": report["source_commit"],
        "records": len(report["predictions"]),
        "files_sha256": {
            name: digest(output / name)
            for name in (
                "config.json",
                "report.json",
                "raw.jsonl",
                "summary.csv",
                "review-template.jsonl",
            )
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--journal", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    package(args.report, args.journal, args.output)
