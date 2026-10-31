"""Descriptive post-run analysis only; does not alter configs, predictions or selection."""

import json

from vmarket_ai.retrieval.evaluate import (
    BASE,
    code_hash,
    input_hashes,
    json_bytes,
    sha,
    summarize,
    write_new,
)
from vmarket_ai.retrieval.metrics import ranked_metrics


def main():
    lock = json.loads((BASE / "gold/v1.lock.json").read_text(encoding="utf-8"))
    assert lock["implementation_sha256"] == code_hash()
    assert lock["input_hashes"] == input_hashes()
    assert lock["gold_sha256"] == sha(BASE / "gold/v1.jsonl")
    gold = {
        g["query_id"]: g
        for g in [
            json.loads(line)
            for line in (BASE / "gold/v1.jsonl").read_text(encoding="utf-8").splitlines()
        ]
    }
    rows = []
    splits = {}
    by_language = {}
    for split in ("train", "dev", "test"):
        folder = BASE / "runs" / (split + "-v1")
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "completed"
        assert manifest["predictions_sha256"] == sha(folder / "predictions.jsonl")
        assert manifest["metrics_sha256"] == sha(folder / "metrics.json")
        assert manifest["gold_sha256"] == lock["gold_sha256"]
        assert manifest["implementation_sha256"] == lock["implementation_sha256"]
        assert manifest["config_sha256"] == sha(BASE / "config.json")
        assert manifest["protocol_sha256"] == sha(BASE / "protocol.json")
        current = [
            json.loads(line)
            for line in (folder / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        for row in current:
            ranked = [h["citation"]["chunk_id"] for h in row["result"]["hits"]]
            relevant = {g["chunk_id"]: g["grade"] for g in gold[row["query_id"]]["relevant"]}
            assert row["metrics"] == {
                str(k): ranked_metrics(ranked, relevant, k) for k in (1, 3, 5)
            }
        assert summarize(current) == json.loads(
            (folder / "metrics.json").read_text(encoding="utf-8")
        )
        splits[split] = summarize(current)
        by_language[split] = {
            language: summarize([r for r in current if r["language"] == language])
            for language in ("ja", "en")
        }
        rows.extend(current)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["query_id"], {})[row["method"]] = row
    wins = {"lexical": [], "dense": []}
    identical = 0
    for query, methods in grouped.items():
        assert len({r["result"]["eligible_corpus_sha256"] for r in methods.values()}) == 1
        identical += 1
        left, right = (methods[m]["metrics"]["5"]["mrr"] for m in ("lexical", "dense"))
        if left is not None and left != right:
            winner = "lexical" if left > right else "dense"
            wins[winner].append(
                {
                    "query_id": query,
                    "partition": methods["dense"]["partition"],
                    "question": methods["dense"]["question"],
                    "lexical_mrr_at_5": left,
                    "dense_mrr_at_5": right,
                    "lexical_result_chunk_ids": [
                        h["citation"]["chunk_id"] for h in methods["lexical"]["result"]["hits"]
                    ],
                    "dense_result_chunk_ids": [
                        h["citation"]["chunk_id"] for h in methods["dense"]["result"]["hits"]
                    ],
                }
            )
    summary = {
        "status": "descriptive_only; provisional agent-authored labels",
        "splits": splits,
        "by_query_language": by_language,
        "observed_mrr_at_5_wins": wins,
        "queries_with_identical_authorized_corpus": identical,
        "predictions": len(rows),
        "forbidden_hits": sum(r["forbidden_hits"] for r in rows),
        "measured_query_embedding_calls": sum(r["result"]["embedding_calls"] for r in rows),
        "measured_query_input_tokens": sum(r["result"]["input_tokens"] for r in rows),
        "billed_embedding_usd": sum(float(r["result"]["billed_embedding_usd"]) for r in rows),
        "provider_inference_requests": 0,
        "cpu_energy_hosting_cost": "NOT_MEASURED",
        "selected_method": json.loads((BASE / "selection.json").read_text())["selected_method"],
        "test_used_for_selection": False,
        "independent_human_review": "pending",
    }
    write_new(BASE / "comparison.json", json_bytes(summary))
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "predictions",
                    "queries_with_identical_authorized_corpus",
                    "forbidden_hits",
                    "measured_query_embedding_calls",
                    "measured_query_input_tokens",
                    "billed_embedding_usd",
                    "selected_method",
                )
            }
        )
    )
    print("Observed lexical MRR@5 wins:", len(wins["lexical"]))
    print("Observed dense MRR@5 wins:", len(wins["dense"]))


if __name__ == "__main__":
    main()
