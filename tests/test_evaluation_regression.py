import importlib.util
import shutil
from pathlib import Path

import pytest

from vmarket_ai.evaluation.regression import (
    input_digest,
    mapping_records,
    ratio,
    retrieval_records,
    summarize,
)


def test_git_text_hashes_normalize_line_endings_but_frozen_original_data_does_not():
    assert input_digest("evals/qa/config.json", b"one\r\ntwo\r\n") == input_digest(
        "evals/qa/config.json", b"one\ntwo\n"
    )
    assert input_digest("data/v1/csv/raw.csv", b"one\r\ntwo\r\n") != input_digest(
        "data/v1/csv/raw.csv", b"one\ntwo\n"
    )


def test_zero_relevance_is_excluded_and_forbidden_result_is_detected():
    gold = {
        "deny": {
            "partition": "test",
            "relevant": [],
            "forbidden_document_ids": ["private"],
            "expected_outcome": "deny_access",
        }
    }
    empty_metrics = {
        str(k): {"hit": None, "recall": None, "mrr": None, "ndcg": None} for k in (1, 3, 5)
    }
    record = {
        "partition": "test",
        "query_id": "deny",
        "method": "dense",
        "metrics": empty_metrics,
        "forbidden_hits": 0,
        "result": {"hits": [], "latency_ms": 1.0, "billed_embedding_usd": "0"},
    }
    parsed = retrieval_records([record], gold)
    metrics = summarize(parsed, [])
    recall = next(row for row in metrics if row["metric"] == "recall@5")
    assert recall["value"] is None and recall["n"] == 0
    record["result"]["hits"] = [{"citation": {"chunk_id": "x", "document_id": "private"}}]
    with pytest.raises(ValueError, match="metric mismatch"):
        retrieval_records([record], gold)


def test_unlabeled_mapping_is_not_counted_as_wrong_accuracy():
    gold = {
        "missing": {
            "partition": "regression",
            "target_to_source": None,
            "expected_suggestion": "input_error",
        }
    }
    prediction = {
        "case_id": "missing",
        "method": "rule",
        "partition": "regression",
        "exact_mapping": None,
        "has_assignments": True,
        "status": "needs_review",
        "model_output_rejected": False,
        "latency_ms": 1.0,
        "response": {"assignments": [{"target_field": "sku", "source_header": "SKU"}]},
    }
    parsed = mapping_records([prediction], gold, "fixture")
    assert parsed[0]["assignments"] == {"sku": "SKU"}
    metrics = summarize([], parsed)
    accuracy = next(row for row in metrics if row["metric"] == "exact_mapping_accuracy")
    assert accuracy["value"] is None and accuracy["n"] == 0
    assert (
        next(row for row in metrics if row["metric"] == "unlabeled_mapping_with_assignments")[
            "value"
        ]
        == 1
    )
    assert ratio(0, 0) is None


def test_mapping_test_rows_and_duplicate_cases_are_rejected():
    gold = {
        "x": {"partition": "test", "target_to_source": None, "expected_suggestion": "abstained"}
    }
    prediction = {"case_id": "x", "method": "rule", "partition": "test"}
    with pytest.raises(ValueError, match="not a held-out"):
        mapping_records([prediction], gold, "fixture")


def test_failed_and_skipped_qa_requests_do_not_become_wrong_answers():
    qa = [
        {
            "mode": "retrieval",
            "status": "http_response",
            "http_status": 503,
            "decision_correct": False,
        },
        {
            "mode": "retrieval",
            "status": "NOT_RUN_AFTER_PROVIDER_FAILURE",
            "http_status": None,
            "decision_correct": None,
        },
    ]
    summary = summarize([], [], qa)
    decision = next(
        item for item in summary if item["metric"] == "decision_accuracy_among_valid_responses"
    )
    coverage = next(item for item in summary if item["metric"] == "valid_response_coverage")
    assert decision["value"] is None and decision["n"] == 0
    assert coverage["value"] == 0 and coverage["n"] == 2


def test_retained_report_verifier_rejects_tampered_summary(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "evals/p13/verify.py"
    spec = importlib.util.spec_from_file_location("p13_verify", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    copied = tmp_path / "run"
    shutil.copytree(module.RUN, copied)
    with (copied / "summary.csv").open("a", encoding="utf-8") as output:
        output.write("tampered\n")
    with pytest.raises(ValueError, match="Report bytes changed"):
        module.verify(copied)


def test_regenerated_predictions_must_match_recorded_report(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "evals/p13/verify.py"
    spec = importlib.util.spec_from_file_location("p13_verify_comparison", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    copied = tmp_path / "run"
    shutil.copytree(module.RUN, copied)
    with (copied / "predictions.jsonl").open("a", encoding="utf-8") as output:
        output.write("{}\n")
    with pytest.raises(ValueError, match="Regenerated results differ"):
        module.verify(module.RUN, copied)
