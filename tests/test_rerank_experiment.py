import importlib.util
from pathlib import Path


def reporter():
    spec = importlib.util.spec_from_file_location(
        "rerank_experiment", Path(__file__).resolve().parents[1] / "tools/p13_rerank.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rerank_preserves_candidates_and_ties_and_handles_japanese():
    module = reporter()
    hits = [
        {"citation": {"chunk_id": key, "text": text}}
        for key, text in (("x", "unrelated"), ("y", "数量"), ("z", "数量"))
    ]
    assert [h["citation"]["chunk_id"] for h in module.rerank("数量", hits)] == ["y", "z", "x"]
    assert [h["citation"]["chunk_id"] for h in hits] == ["x", "y", "z"]


def test_reranking_changes_mrr_but_not_full_pool_recall():
    module = reporter()
    row = {
        "partition": "test",
        "query_id": "q",
        "method": "dense",
        "question": "receipt",
        "result": {
            "hits": [
                {"citation": {"chunk_id": key, "text": text}}
                for key, text in (("x", "unrelated"), ("y", "receipt"))
            ]
        },
    }
    gold = {"q": {"partition": "test", "relevant": [{"chunk_id": "y", "grade": 1}]}}
    observations, _ = module.evaluate([row], gold)
    assert [r["metrics"]["5"]["recall"] for r in observations] == [1.0, 1.0]
    assert [r["metrics"]["5"]["mrr"] for r in observations] == [0.5, 1.0]
