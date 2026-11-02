import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from vmarket_ai.evaluation.tool_questions import aggregate, score, scoring_labels, verify_inputs
from vmarket_ai.qa.backend import DEMO_COLLECTIONS


def test_tool_questions_have_separate_provisional_labels():
    inputs, lock = verify_inputs()
    assert len(inputs) == len(scoring_labels(inputs)) == lock["count"] == 11
    assert all(set(item) == {"id", "question", "scope", "split"} for item in inputs)


def test_wrong_job_id_fails_argument_correctness():
    label = {
        "expected_kind": "tool_intent",
        "expected_tool": "inspect_import_job",
        "expected_arguments": {"job_id": "expected"},
    }
    prediction = {
        "response": {
            "kind": "tool_intent",
            "intent": {"tool_name": "inspect_import_job", "arguments": {"job_id": "invented"}},
        }
    }
    scored = score(prediction, label)
    assert scored["tool_correct"] is True and scored["arguments_correct"] is False
    assert scored["all_correct"] is False


def test_knowledge_scope_is_checked_and_query_semantics_are_not_claimed():
    label = {
        "expected_kind": "tool_intent",
        "expected_tool": "search_supplier_knowledge",
        "expected_arguments": {},
    }
    prediction = {
        "response": {
            "kind": "tool_intent",
            "intent": {
                "tool_name": "search_supplier_knowledge",
                "arguments": {
                    "query": "some text",
                    "collection_ids": [str(DEMO_COLLECTIONS[1])],
                    "top_k": 5,
                },
            },
        }
    }
    assert score(prediction, label)["arguments_correct"] is True
    prediction["response"]["intent"]["arguments"]["collection_ids"] = [str(DEMO_COLLECTIONS[0])]
    assert score(prediction, label)["arguments_correct"] is False


def test_guard_handoff_and_provider_failure_have_distinct_denominators():
    good = {
        "method": "local_qwen_router",
        "response": {"kind": "handoff"},
        "model_calls": 0,
        "latency_ms": 1,
        "score": score(
            {"response": {"kind": "handoff"}}, {"expected_kind": "handoff", "expected_tool": None}
        ),
    }
    failed = {
        "method": "local_qwen_router",
        "response": None,
        "model_calls": 1,
        "latency_ms": 2,
        "score": score({"response": None}, {}),
    }
    result = {row["metric"]: row for row in aggregate([good, failed])}
    assert result["valid_coverage"]["value"] == 0.5
    assert result["correct_among_valid"]["value"] == 1.0
    assert result["correct_over_all_cases"]["value"] == 0.5
    assert result["handoff_without_model"]["value"] == 1


def test_archived_planner_review_template_is_blind_and_pending():
    artifact = Path(__file__).resolve().parents[1] / "evals/p13/runs/tool-questions-v1"
    review = [
        json.loads(line)
        for line in (artifact / "review-template.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(review) == 11
    assert all(
        row["review_status"] == "PENDING_INDEPENDENT_REVIEW" and row["reviewer"] is None
        for row in review
    )
    assert all("expected_kind" not in row and "response" not in row for row in review)


def test_archived_planner_verifier_rejects_missing_case_after_hash_rewrite(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "evals/p13/runs/tool-questions-v1"
    copied = tmp_path / "run"
    shutil.copytree(source, copied)
    raw = copied / "raw.jsonl"
    raw.write_bytes(b"".join(raw.read_bytes().splitlines(keepends=True)[:-1]))
    manifest = json.loads((copied / "manifest.json").read_text(encoding="utf-8"))
    manifest["files_sha256"]["raw.jsonl"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    (copied / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "p13_tool_verify_test", root / "tools/p13_tool_verify.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="missing, repeated"):
        module.verify(copied)


def test_planner_blind_review_rejects_prefilled_answer_after_hash_rewrite(tmp_path):
    root = Path(__file__).resolve().parents[1]
    copied = tmp_path / "run"
    shutil.copytree(root / "evals/p13/runs/tool-questions-v1", copied)
    template = copied / "review-template.jsonl"
    records = [json.loads(line) for line in template.read_text(encoding="utf-8").splitlines()]
    records[0]["independent_expected_tool"] = "get_imports"
    template.write_text(
        "".join(json.dumps(row) + "\n" for row in records), encoding="utf-8", newline="\n"
    )
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files_sha256"]["review-template.jsonl"] = hashlib.sha256(
        template.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "p13_blind_tool_verify", root / "tools/p13_tool_verify.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="not blind and pending"):
        module.verify(copied)
