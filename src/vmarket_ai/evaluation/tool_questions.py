"""Preregistered local planner-selection inputs and provisional scoring."""

import hashlib
import json
from pathlib import Path
from typing import Any

from vmarket_ai.qa.backend import DEMO_COLLECTIONS
from vmarket_ai.retrieval.metrics import latency

ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "evals/p13/tool-questions-v1"
ALLOWED = {
    "get_imports",
    "get_integration_profiles",
    "inspect_import_job",
    "get_reconciliation_report",
    "search_supplier_knowledge",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def verify_inputs(directory: Path = DATASET) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lock = json.loads((directory / "lock.json").read_text(encoding="utf-8"))
    if set(lock["files_sha256"]) != {"inputs.jsonl", "labels.jsonl", "protocol.json"}:
        raise ValueError("Incomplete tool dataset")
    for name, expected in lock["files_sha256"].items():
        if sha(directory / name) != expected:
            raise ValueError("Frozen tool dataset changed")
    if (
        sha(ROOT / "src/vmarket_ai/gateway/agent.py") != lock["agent_sha256_lf"]
        or sha(ROOT / "src/vmarket_ai/gateway/wire.json") != lock["wire_sha256_lf"]
    ):
        raise ValueError("Planner implementation differs from preregistration")
    inputs = read_rows(directory / "inputs.jsonl")
    if len(inputs) != lock["count"] or len({r["id"] for r in inputs}) != len(inputs):
        raise ValueError("Invalid tool input count or duplicate IDs")
    for row in inputs:
        if (
            set(row) != {"id", "question", "scope", "split"}
            or row["split"] != "test"
            or row["scope"] != "b"
            or not isinstance(row["question"], str)
            or not row["question"].strip()
        ):
            raise ValueError("Invalid tool input shape")
    if len({row["question"].strip().casefold() for row in inputs}) != len(inputs):
        raise ValueError("Duplicate tool questions")
    return inputs, lock


def scoring_labels(
    inputs: list[dict[str, Any]], directory: Path = DATASET
) -> dict[str, dict[str, Any]]:
    # Only call after all planner outputs have been recorded.
    rows = read_rows(directory / "labels.jsonl")
    labels = {row["id"]: row for row in rows}
    if len(rows) != len(labels) or set(labels) != {row["id"] for row in inputs}:
        raise ValueError("Tool label IDs differ")
    for row in rows:
        if (
            row["label_status"] != "provisional_agent_authored"
            or row["independent_review"] != "pending"
        ):
            raise ValueError("Independent review status must remain explicit")
        if row["expected_kind"] == "tool_intent":
            if row["expected_tool"] not in ALLOWED:
                raise ValueError("Invalid expected tool")
        elif row["expected_kind"] != "handoff" or row["expected_tool"] is not None:
            raise ValueError("Invalid expected handoff")
    return labels


def score(prediction: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    response = prediction.get("response")
    if not isinstance(response, dict) or response.get("kind") not in {
        "tool_intent",
        "handoff",
        "final",
    }:
        return {
            "valid": False,
            "kind_correct": None,
            "tool_correct": None,
            "arguments_correct": None,
            "all_correct": None,
            "forbidden_public_intent": None,
        }
    kind = response["kind"]
    intent = response.get("intent", {}) if kind == "tool_intent" else {}
    tool = intent.get("tool_name")
    args = intent.get("arguments", {})
    kind_correct = kind == label["expected_kind"]
    tool_correct = (
        tool == label["expected_tool"] if label["expected_kind"] == "tool_intent" else None
    )
    if label["expected_kind"] == "handoff":
        arguments_correct = kind == "handoff"
    elif not kind_correct or not tool_correct:
        arguments_correct = False
    elif tool == "search_supplier_knowledge":
        arguments_correct = (
            set(args) == {"query", "collection_ids", "top_k"}
            and isinstance(args.get("query"), str)
            and bool(args["query"].strip())
            and args.get("collection_ids") == [str(DEMO_COLLECTIONS[1])]
            and args.get("top_k") == 5
        )
    else:
        arguments_correct = args == label["expected_arguments"]
    return {
        "valid": True,
        "kind_correct": kind_correct,
        "tool_correct": tool_correct,
        "arguments_correct": arguments_correct,
        "all_correct": bool(kind_correct and (tool_correct is not False) and arguments_correct),
        "forbidden_public_intent": kind == "tool_intent" and tool not in ALLOWED,
    }


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metrics = []
    for method in sorted({row["method"] for row in rows}):
        group = [row for row in rows if row["method"] == method]
        valid = [row for row in group if row["score"]["valid"]]
        local = [row for row in group if row["model_calls"] > 0]
        for name, value, count in (
            ("valid_coverage", len(valid) / len(group), len(group)),
            (
                "correct_over_all_cases",
                sum(row["score"]["all_correct"] is True for row in group) / len(group),
                len(group),
            ),
            (
                "correct_among_valid",
                sum(row["score"]["all_correct"] is True for row in valid) / len(valid)
                if valid
                else None,
                len(valid),
            ),
            (
                "forbidden_public_intents",
                sum(row["score"]["forbidden_public_intent"] is True for row in valid),
                len(valid),
            ),
            (
                "handoff_without_model",
                sum(
                    row["response"] is not None
                    and row["response"].get("kind") == "handoff"
                    and row["model_calls"] == 0
                    for row in group
                ),
                len(group),
            ),
            ("model_call_cases", len(local), len(group)),
        ):
            metrics.append({"method": method, "metric": name, "value": value, "n": count})
        for name, value in latency([row["latency_ms"] for row in group]).items():
            metrics.append({"method": method, "metric": name, "value": value, "n": len(group)})
    return metrics


if __name__ == "__main__":
    inputs, _ = verify_inputs()
    print(
        json.dumps(
            {
                "status": "PASS",
                "inputs": len(inputs),
                "labels": len(scoring_labels(inputs)),
                "review": "pending",
            }
        )
    )
