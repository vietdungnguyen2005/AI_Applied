import importlib.util
import json
import sys
from pathlib import Path

import pytest


def reporter():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "tools"))
    try:
        spec = importlib.util.spec_from_file_location(
            "p13_completion", root / "tools/p13_completion.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_final_scoring_rejects_missing_measurements():
    with pytest.raises(ValueError, match="Missing, repeated"):
        reporter().score_all([])


def test_saved_dense_candidates_have_exact_source_text():
    module = reporter()
    root = Path(__file__).resolve().parents[1]
    source_ids = {
        h["citation"]["chunk_id"]
        for part in ("train", "dev", "test")
        for row in module.rows(root / f"evals/retrieval/runs/{part}-v1/predictions.jsonl")
        for h in row["result"]["hits"]
    }
    for row in module.rows(root / "evals/p13/runs/new-questions-v1/raw.jsonl"):
        if row["domain"] == "retrieval" and row["method"] == "dense":
            assert all(h["chunk_id"] in source_ids for h in row["hits"])


def test_completed_artifact_recomputes_and_preserves_failures():
    module = reporter()
    root = Path(__file__).resolve().parents[1]
    artifact = root / "evals/p13/runs/completion-v1"
    module.verify(artifact)
    report = json.loads((artifact / "report.json").read_text(encoding="utf-8"))
    config = json.loads((artifact / "config.json").read_text(encoding="utf-8"))
    protocol = json.loads((root / "evals/p13/tool-questions-v1/protocol.json").read_text())
    assert config["model"]["digest"] == protocol["model_digest"]
    assert config["qa_max_tokens"] == 512 and config["context"] == 4096
    assert len(report["predictions"]) == 40
    grounded = [r for r in report["predictions"] if r["method"] == "with_sources"]
    assert sum(not r["score"]["valid"] for r in grounded) == 2
    assert all(r["model_outputs"] for r in grounded)


def test_final_scorer_rejects_duplicate_even_with_original_row_count():
    module = reporter()
    root = Path(__file__).resolve().parents[1]
    raw = module.rows(root / "evals/p13/runs/completion-v1/raw.jsonl")
    raw[-1] = raw[0]
    with pytest.raises(ValueError, match="Missing, repeated"):
        module.score_all(raw)


def test_receipt_failure_replays_through_fixed_quote_validator_without_new_inference():
    from vmarket_ai.qa.service import supported_quote
    from vmarket_ai.qa.spec import Proposal

    module = reporter()
    root = Path(__file__).resolve().parents[1]
    raw = module.rows(root / "evals/p13/runs/completion-v1/raw.jsonl")
    row = next(r for r in raw if r["case_id"] == "q13-01" and r["method"] == "with_sources")
    proposal = Proposal.model_validate_json(row["model_outputs"][0]["text"])
    sources = {
        h["citation"]["chunk_id"]: h["citation"]["text"]
        for part in ("train", "dev", "test")
        for observed in module.rows(root / f"evals/retrieval/runs/{part}-v1/predictions.jsonl")
        for h in observed["result"]["hits"]
    }
    assert row["http_status"] == 502  # Preserve the original failed outcome.
    assert all(supported_quote(sources[str(c.chunk_id)], c.quote) for c in proposal.claims)
