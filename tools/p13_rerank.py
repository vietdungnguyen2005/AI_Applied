"""Exploratory fixed bigram reranking of retained P06 top-five candidates."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import unicodedata
from pathlib import Path
from statistics import mean

from vmarket_ai.retrieval.metrics import ranked_metrics

ROOT = Path(__file__).resolve().parents[1]


def grams(text: str) -> set[str]:
    value = "".join(c for c in unicodedata.normalize("NFC", text).casefold() if c.isalnum())
    return {value[i : i + 2] for i in range(len(value) - 1)}


def rerank(question: str, hits: list[dict]) -> list[dict]:
    query = grams(question)

    def overlap(hit: dict) -> float:
        candidate = grams(hit["citation"]["text"])
        union = query | candidate
        return len(query & candidate) / len(union) if union else 0.0

    # Python's stable sort preserves original order for ties; never add candidates.
    return sorted(hits, key=overlap, reverse=True)


def evaluate(predictions: list[dict], gold: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    observations = []
    seen = set()
    for row in predictions:
        identity = (row["partition"], row["query_id"], row["method"])
        if identity in seen:
            raise ValueError("Duplicate retrieval observation")
        seen.add(identity)
        label = gold[row["query_id"]]
        if label["partition"] != row["partition"]:
            raise ValueError("Partition mismatch")
        hits = row["result"]["hits"]
        if len(hits) > 5:
            raise ValueError("Expected retained top-five pool")
        relevance = {item["chunk_id"]: item["grade"] for item in label["relevant"]}
        for variant, selected in (
            ("none", hits),
            ("bigram_jaccard", rerank(row["question"], hits)),
        ):
            ranked = [h["citation"]["chunk_id"] for h in selected]
            observations.append(
                {
                    "partition": row["partition"],
                    "query_id": row["query_id"],
                    "method": row["method"],
                    "reranker": variant,
                    "ranked": ranked,
                    "metrics": {str(k): ranked_metrics(ranked, relevance, k) for k in (1, 3, 5)},
                }
            )
    summary = []
    for partition, method, variant in sorted(
        {(r["partition"], r["method"], r["reranker"]) for r in observations}
    ):
        group = [
            r
            for r in observations
            if (r["partition"], r["method"], r["reranker"]) == (partition, method, variant)
        ]
        for k in (1, 3, 5):
            for metric in ("recall", "mrr", "ndcg"):
                values = [
                    r["metrics"][str(k)][metric]
                    for r in group
                    if r["metrics"][str(k)][metric] is not None
                ]
                summary.append(
                    {
                        "partition": partition,
                        "method": method,
                        "reranker": variant,
                        "k": k,
                        "metric": metric,
                        "value": mean(values) if values else None,
                        "scored_cases": len(values),
                        "all_cases": len(group),
                    }
                )
    return observations, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = [ROOT / f"evals/retrieval/runs/{part}-v1/predictions.jsonl" for part in ("dev", "test")]
    gold_path = ROOT / "evals/retrieval/gold/v1.jsonl"
    paths.append(gold_path)

    def read(path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    predictions = [row for path in paths[:-1] for row in read(path)]
    observations, summary = evaluate(predictions, {r["query_id"]: r for r in read(gold_path)})
    config = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "design": (
            "post-hoc exploratory regression; previously inspected P06 data and provisional labels"
        ),
        "algorithm": (
            "NFC casefold alphanumeric character bigram set Jaccard; "
            "stable descending; top-five pool only"
        ),
        "model_calls": 0,
        "new_retrieval_calls": 0,
        "independent_review": "pending",
        "input_sha256_lf": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(
                p.read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
            for p in paths
        },
    }
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in (
        ("config.json", config),
        ("report.json", {"observations": observations, "summary": summary}),
    ):
        (args.output / name).write_text(
            json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    sink = io.StringIO(newline="")
    writer = csv.DictWriter(sink, fieldnames=list(summary[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(summary)
    (args.output / "summary.csv").write_text(sink.getvalue(), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "source_records": len(predictions),
                "rankings": len(observations),
                "design": config["design"],
            }
        )
    )


if __name__ == "__main__":
    main()
