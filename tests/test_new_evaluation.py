import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

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


def test_independent_label_review_template_does_not_show_existing_labels_or_predictions():
    path = (
        Path(__file__).resolve().parents[1]
        / "evals/p13/runs/new-questions-v1/review-template.jsonl"
    )
    review = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(review) == 8
    for row in review:
        assert row["review_status"] == "PENDING_INDEPENDENT_REVIEW"
        assert row["reviewer"] is None and row["independent_expected_status"] is None
        assert "provisional_label" not in row and "observed_response" not in row


def test_verifier_rejects_missing_observation_even_if_journal_hash_is_rewritten(tmp_path):
    root = Path(__file__).resolve().parents[1]
    artifact = root / "evals/p13/runs/new-questions-v1"
    spec = importlib.util.spec_from_file_location(
        "p13_new_verify_test", root / "tools/p13_new_verify.py"
    )
    assert spec is not None and spec.loader is not None
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    report = json.loads((artifact / "report.json").read_text(encoding="utf-8"))
    raw = (artifact / "raw.jsonl").read_bytes().splitlines(keepends=True)[:-1]
    journal = tmp_path / "raw.jsonl"
    journal.write_bytes(b"".join(raw))
    report["journal_sha256"] = hashlib.sha256(journal.read_bytes()).hexdigest()
    revised_report = tmp_path / "report.json"
    revised_report.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="missing, repeated"):
        verifier.verify(revised_report, journal, artifact / "summary.csv")
