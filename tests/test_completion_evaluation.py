import importlib.util
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
