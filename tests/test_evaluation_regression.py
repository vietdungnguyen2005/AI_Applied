import pytest

from vmarket_ai.evaluation.regression import mapping_records, ratio, retrieval_records, summarize


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
