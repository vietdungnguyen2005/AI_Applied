import json
import shutil

import pytest

from vmarket_ai.evaluation.new_questions import DATASET, scoring_labels, verify_inputs
from vmarket_ai.evaluation.new_score import score_qa, score_retrieval


def test_dataset_has_separate_provisional_labels_and_no_exact_prior_duplicates():
    inputs, lock = verify_inputs()
    assert len(inputs) == len(scoring_labels(inputs)) == lock["case_count"] == 8
    assert all(set(row) == {"id", "split", "collection", "language", "question"} for row in inputs)
    assert all("expected" not in json.dumps(row) for row in inputs)


def test_dataset_hash_rejects_modified_labels(tmp_path):
    copy = tmp_path / "dataset"
    shutil.copytree(DATASET, copy)
    with (copy / "labels.jsonl").open("a", encoding="utf-8") as output:
        output.write("{}\n")
    with pytest.raises(ValueError, match="Frozen dataset bytes changed"):
        verify_inputs(copy)


def test_provider_failure_is_not_counted_as_wrong_decision():
    assert score_qa({"http_status": 503}, {})["decision_correct"] is None


def test_abstention_cannot_receive_credit_for_an_answer_citation():
    label = {
        "expected_status": "answered",
        "required_answer_anchors": ["UTF-8"],
        "relevant": [{"document_id": "one", "section": "encoding"}],
    }
    prediction = {
        "http_status": 200,
        "response": {
            "status": "abstained",
            "answer": None,
            "citations": [
                {"document_id": "one", "locator": {"kind": "section", "value": "encoding"}}
            ],
        },
    }
    score = score_qa(prediction, label)
    assert score["decision_correct"] is False
    assert score["anchor_proxy"] is False and score["citation_proxy"] is False


def test_duplicate_chunks_do_not_inflate_section_recall():
    label = {
        "relevant": [
            {"document_id": "one", "section": "mapping"},
            {"document_id": "two", "section": "mapping"},
        ]
    }
    prediction = {
        "status": "ok",
        "hits": [
            {"document_id": "one", "section": "mapping"},
            {"document_id": "one", "section": "mapping"},
        ],
    }
    assert score_retrieval(prediction, label)["metrics"]["recall"] == 0.5
