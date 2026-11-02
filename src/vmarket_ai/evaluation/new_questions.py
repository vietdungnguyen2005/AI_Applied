"""Frozen P13 question inputs and provisional, separately stored scoring labels."""

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "evals/p13/new-questions-v1"


def text_hash(path: Path) -> str:
    content = path.read_bytes()
    if path.is_relative_to(ROOT / "evals") or path.is_relative_to(ROOT / "data/releases"):
        content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def normalize(question: str) -> str:
    return " ".join(unicodedata.normalize("NFC", question).casefold().split())


def verify_inputs(directory: Path = DATASET) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lock = json.loads((directory / "lock.json").read_text(encoding="utf-8"))
    for name, expected in lock["files_sha256"].items():
        if (
            name not in {"inputs.jsonl", "labels.jsonl", "protocol.json"}
            or text_hash(directory / name) != expected
        ):
            raise ValueError("Frozen dataset bytes changed")
    if set(lock["files_sha256"]) != {"inputs.jsonl", "labels.jsonl", "protocol.json"}:
        raise ValueError("Incomplete frozen dataset")
    for path, key in [
        (ROOT / "data/releases/v1.lock.json", "corpus_release_lock_sha256"),
        (ROOT / "evals/qa/cases.jsonl", "prior_qa_cases_sha256"),
        (ROOT / "data/v1/queries.jsonl", "prior_queries_sha256"),
    ]:
        if text_hash(path) != lock[key]:
            raise ValueError("Frozen corpus or prior case bytes changed")
    inputs = read_rows(directory / "inputs.jsonl")
    if len(inputs) != lock["case_count"] or len({r["id"] for r in inputs}) != len(inputs):
        raise ValueError("Invalid input count or duplicate IDs")
    old_questions = {
        normalize(r["question"])
        for p in (ROOT / "data/v1/queries.jsonl", ROOT / "evals/qa/cases.jsonl")
        for r in read_rows(p)
    }
    questions = []
    for row in inputs:
        if (
            set(row) != {"id", "split", "collection", "language", "question"}
            or row["split"] != "test"
            or row["collection"] not in {"a", "b"}
            or row["language"] not in {"en", "ja"}
        ):
            raise ValueError("Invalid input shape")
        question = normalize(row["question"])
        if not question or question in old_questions or question in questions:
            raise ValueError("Duplicate exact normalized question")
        questions.append(question)
    return inputs, lock


def scoring_labels(
    inputs: list[dict[str, Any]], directory: Path = DATASET
) -> dict[str, dict[str, Any]]:
    # Call only after all inference inputs and raw predictions have been recorded.
    labels = read_rows(directory / "labels.jsonl")
    result = {row["id"]: row for row in labels}
    if len(result) != len(labels) or set(result) != {row["id"] for row in inputs}:
        raise ValueError("Label ID mismatch")
    corpus = read_rows(ROOT / "data/v1/corpus.jsonl")
    for row in labels:
        if (
            row["label_status"] != "provisional_agent_authored"
            or row["independent_review"] != "pending"
        ):
            raise ValueError("Label provenance must remain explicit")
        if row["expected_status"] not in {"answered", "abstained"}:
            raise ValueError("Invalid expected status")
        for ref in row["relevant"]:
            if not any(
                item["document_id"] == ref["document_id"]
                and ref["section"] in item["sections"]
                and item["status"] == "current"
                for item in corpus
            ):
                raise ValueError("Unknown source reference")
    return result


if __name__ == "__main__":
    inputs, _ = verify_inputs()
    print(
        json.dumps(
            {
                "status": "PASS",
                "inputs": len(inputs),
                "labels": len(scoring_labels(inputs)),
                "review": "provisional_agent_authored; independent review pending",
            }
        )
    )
