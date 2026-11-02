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
