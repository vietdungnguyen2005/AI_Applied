"""Re-score retained synthetic runs; this never performs inference or creates gold labels."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from vmarket_ai.retrieval.metrics import latency, ranked_metrics

ROOT = Path(__file__).resolve().parents[3]
RETRIEVAL_GOLD = ROOT / "evals/retrieval/gold/v1.jsonl"
MAPPING_GOLD = ROOT / "data/v1/labels/mapping.jsonl"
QA_CASES = ROOT / "evals/qa/cases.jsonl"


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ratio(numerator: float, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def retrieval_records(
    predictions: list[dict[str, Any]], gold: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for row in predictions:
        key = (row["partition"], row["query_id"], row["method"])
        if key in seen or row["query_id"] not in gold:
            raise ValueError("Duplicate or unknown retrieval case")
        seen.add(key)
        label = gold[row["query_id"]]
        if label["partition"] != row["partition"]:
            raise ValueError("Retrieval partition mismatch")
        hits = row["result"]["hits"]
        rank = [h["citation"]["chunk_id"] for h in hits]
        relevance = {x["chunk_id"]: x["grade"] for x in label["relevant"]}
        scored = {str(k): ranked_metrics(rank, relevance, k) for k in (1, 3, 5)}
        forbidden = sum(
            h["citation"]["document_id"] in label["forbidden_document_ids"] for h in hits
        )
        if scored != row["metrics"] or forbidden != row["forbidden_hits"]:
            raise ValueError("Retrieval prediction/metric mismatch")
        result.append(
            {
                "case_id": row["query_id"],
                "split": row["partition"],
                "method": row["method"],
                "expected_outcome": label["expected_outcome"],
                "ranked_chunk_ids": rank,
                "metrics": scored,
                "forbidden_hits": forbidden,
                "latency_ms": row["result"]["latency_ms"],
                "provider_billed_usd": float(row["result"]["billed_embedding_usd"]),
            }
        )
    return result


def mapping_records(
    predictions: list[dict[str, Any]], gold: dict[str, dict[str, Any]], run: str
) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for row in predictions:
        key = (row["case_id"], row["method"])
        if key in seen or row["case_id"] not in gold:
            raise ValueError("Duplicate or unknown mapping case")
        seen.add(key)
        label = gold[row["case_id"]]
        if row["partition"] == "test" or row["partition"] != label["partition"]:
            raise ValueError("Mapping is not a held-out test run")
        output = {
            a["target_field"]: a["source_header"]
            for a in row.get("response", {}).get("assignments", [])
        }
        expected = label["target_to_source"]
        exact = output == expected if expected is not None else None
        if row["exact_mapping"] != exact or row["has_assignments"] != bool(output):
            raise ValueError("Mapping prediction/metric mismatch")
        result.append(
            {
                "case_id": row["case_id"],
                "split": row["partition"],
                "run": run,
                "method": row["method"],
                "status": row["status"],
                "assignments": output,
                "expected_status": label["expected_suggestion"],
                "mapping_labeled": expected is not None,
                "exact_mapping": exact,
                "has_assignments": bool(output),
                "model_output_rejected": row["model_output_rejected"],
                "latency_ms": row["latency_ms"],
            }
        )
    return result


def summarize(
    retrieval: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    qa: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    def add(group: str, variant: str, metric: str, value: Any, n: int) -> None:
        output.append(
            {"group": group, "variant": variant, "metric": metric, "value": value, "n": n}
        )

    for split, method in sorted({(r["split"], r["method"]) for r in retrieval}):
        group = [r for r in retrieval if r["split"] == split and r["method"] == method]
        positive = [r for r in group if r["metrics"]["5"]["recall"] is not None]
        for metric in ("recall", "mrr"):
            add(
                "retrieval_" + split,
                method,
                metric + "@5",
                ratio(sum(r["metrics"]["5"][metric] for r in positive), len(positive)),
                len(positive),
            )
        add(
            "retrieval_" + split,
            method,
            "forbidden_hits",
            sum(r["forbidden_hits"] for r in group),
            len(group),
        )
        for name, value in latency([r["latency_ms"] for r in group]).items():
            add("retrieval_" + split, method, name, value, len(group))
        add(
            "retrieval_" + split,
            method,
            "provider_billed_usd_per_request",
            sum(r["provider_billed_usd"] for r in group) / len(group),
            len(group),
        )
    for run, method in sorted({(r["run"], r["method"]) for r in mapping}):
        group = [r for r in mapping if r["run"] == run and r["method"] == method]
        labeled = [r for r in group if r["mapping_labeled"]]
        add(
            "mapping_known_cases",
            run + "/" + method,
            "exact_mapping_accuracy",
            ratio(sum(r["exact_mapping"] is True for r in labeled), len(labeled)),
            len(labeled),
        )
        add(
            "mapping_known_cases",
            run + "/" + method,
            "model_output_rejection_rate_per_case",
            ratio(sum(r["model_output_rejected"] is True for r in group), len(group)),
            len(group),
        )
        add(
            "mapping_known_cases",
            run + "/" + method,
            "unlabeled_mapping_with_assignments",
            sum(not r["mapping_labeled"] and r["has_assignments"] for r in group),
            len(group),
        )
        for name, value in latency([r["latency_ms"] for r in group]).items():
            add("mapping_known_cases", run + "/" + method, name, value, len(group))
    for mode in sorted({r["mode"] for r in qa or []}):
        group = [r for r in qa or [] if r["mode"] == mode]
        valid = [r for r in group if r["status"] == "completed" or r["http_status"] == 200]
        assessed = [r for r in valid if isinstance(r["decision_correct"], bool)]
        add(
            "qa_development_partial",
            mode,
            "valid_response_coverage",
            ratio(len(valid), len(group)),
            len(group),
        )
        add(
            "qa_development_partial",
            mode,
            "decision_accuracy_among_valid_responses",
            ratio(sum(r["decision_correct"] is True for r in assessed), len(assessed)),
            len(assessed),
        )
        add(
            "qa_development_partial",
            mode,
            "http_or_provider_failures",
            sum(r["http_status"] in (502, 503, 504) for r in group),
            len(group),
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Fresh output directory; default creates one under .local"
    )
    args = parser.parse_args()
    if args.output is None:
        args.output = ROOT / ".local" / ("p13-regression-" + uuid4().hex)
    if args.output.exists():
        raise SystemExit("Output must be a fresh directory")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise SystemExit("Commit the working tree before recording experiment provenance")
    # These historical verifiers check release hashes, source revisions and real saved outputs.
    for script in ("evals/retrieval/analyze.py", "evals/mapping/analyze.py"):
        subprocess.run([sys.executable, script], cwd=ROOT, check=True, capture_output=True)
    input_paths = [
        RETRIEVAL_GOLD,
        MAPPING_GOLD,
        QA_CASES,
        ROOT / "data/releases/v1.lock.json",
        ROOT / "evals/retrieval/gold/v1.lock.json",
        ROOT / "evals/retrieval/config.json",
        ROOT / "evals/retrieval/protocol.json",
        ROOT / "evals/qa/protocol.json",
        ROOT / "evals/qa/runs/live-v1/summary.json",
    ]
    retrieval = []
    for split in ("train", "dev", "test"):
        path = ROOT / f"evals/retrieval/runs/{split}-v1/predictions.jsonl"
        input_paths.extend([path, path.with_name("manifest.json"), path.with_name("metrics.json")])
        retrieval.extend(rows(path))
    mapping = []
    mapping_paths = []
    for run in ("local-v1", "local-v2", "local-9b-v1"):
        path = ROOT / f"evals/mapping/runs/{run}/predictions.jsonl"
        mapping_paths.append((run, path))
        input_paths.extend([path, path.with_name("config.json"), path.with_name("summary.json")])
    qa_path = ROOT / "evals/qa/runs/live-v1/predictions.jsonl"
    input_paths.append(qa_path)
    scored_retrieval = retrieval_records(
        retrieval, {r["query_id"]: r for r in rows(RETRIEVAL_GOLD)}
    )
    labels = {r["case_id"]: r for r in rows(MAPPING_GOLD)}
    for run, path in mapping_paths:
        mapping.extend(mapping_records(rows(path), labels, run))
    qa = [
        {
            "case_id": r["case_id"],
            "mode": r["mode"],
            "status": r.get("status", "http_response"),
            "http_status": r.get("http_status"),
            "decision_correct": r.get("decision_correct"),
            "citation_verified": r.get("citation_verified"),
            "factual_anchor_proxy": r.get("factual_anchor_proxy"),
        }
        for r in rows(qa_path)
    ]
    metrics = summarize(scored_retrieval, mapping, qa)
    config = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
        .decode()
        .strip(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "implementation_sha256": sha(Path(__file__)),
        "input_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in input_paths},
        "label_status": "provisional_agent_authored; independent human review pending",
        "test_status": (
            "retrieval test consumed previously; regression only; mapping test inference not run"
        ),
        "inference": "none; historical outputs only",
        "external_provider_calls": 0,
        "latency": "historical per-request milliseconds; p95 linear interpolation; warmup excluded",
        "cost": "provider-billed query embedding only; compute, energy, hosting not measured",
        "unavailable": [
            "fresh held-out quality",
            "human review",
            "reranker ablation",
            "tool selection quality",
            "workflow task success",
            "complete matched QA comparison",
        ],
    }
    predictions = (
        [{"domain": "retrieval", **r} for r in scored_retrieval]
        + [{"domain": "mapping", **r} for r in mapping]
        + [{"domain": "qa_partial", **r} for r in qa]
    )
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    (args.output / "predictions.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in predictions),
        encoding="utf-8",
        newline="\n",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream, fieldnames=["group", "variant", "metric", "value", "n"], lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(metrics)
    (args.output / "summary.csv").write_text(stream.getvalue(), encoding="utf-8", newline="\n")
    manifest = {
        "status": "historical_regression_not_unseen_quality",
        "records": len(predictions),
        "files_sha256": {
            name: sha(args.output / name)
            for name in ("config.json", "predictions.jsonl", "summary.csv")
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"output": str(args.output), **manifest}))


if __name__ == "__main__":
    main()
