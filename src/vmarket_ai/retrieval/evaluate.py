"""Offline synthetic evaluation only. Gold compilation never calls a retrieval/model path."""

import argparse
import asyncio
import csv
import hashlib
import io
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from vmarket_ai.database import create_db_engine
from vmarket_ai.datasets.audit import CorpusRecord, Query, RelevanceLabel, records
from vmarket_ai.datasets.release import verify_release
from vmarket_ai.ingestion.models import ChunkRecord, DocumentRecord, Grant, Snapshot, SourceVersion
from vmarket_ai.ingestion.service import stable
from vmarket_ai.ingestion.spec import Actor, fingerprint, pipeline_manifest
from vmarket_ai.providers.local_e5 import LocalE5EmbeddingProvider
from vmarket_ai.retrieval.metrics import latency, ranked_metrics
from vmarket_ai.retrieval.service import Retriever
from vmarket_ai.retrieval.spec import Method, RetrievalConfig, SearchRequest
from vmarket_ai.settings import load_settings

BASE = Path("evals/retrieval")
DATA = Path("data/v1")
METHODS: tuple[Method, ...] = ("lexical", "dense", "hybrid")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def code_hash() -> str:
    entries = {
        p.as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in sorted(Path("src/vmarket_ai").rglob("*.py"))
    }
    return hashlib.sha256(json_bytes(entries)).hexdigest()


def input_hashes() -> dict[str, str]:
    files = [
        BASE / "config.json",
        BASE / "protocol.json",
        Path("data/releases/v1.lock.json"),
        DATA / "corpus.jsonl",
        DATA / "queries.jsonl",
        DATA / "labels/relevance.jsonl",
    ]
    return {p.as_posix(): sha(p) for p in files}


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Refusing to overwrite evaluation artifact")
        return
    path.write_bytes(raw)


def config() -> RetrievalConfig:
    return RetrievalConfig.model_validate_json((BASE / "config.json").read_bytes())


def actor_for(query: Query) -> Actor:
    # Authority comes from the test's explicit readable scopes, never relevance/outcome labels.
    return Actor(
        id=stable(
            "retrieval-eval-reader:"
            + ",".join(sorted(str(c) for c in query.readable_collection_ids))
        )
    )


def prepare() -> None:
    verify_release(DATA, Path("data/releases/v1.lock.json"))
    cfg = config()
    queries = {q.id: q for q in records(DATA / "queries.jsonl", Query)}
    labels = records(DATA / "labels/relevance.jsonl", RelevanceLabel)
    corpus = records(DATA / "corpus.jsonl", CorpusRecord)
    source_map = {(d.document_id, d.version_id): d for d in corpus}
    settings = load_settings()
    if not settings.migration_database_url:
        raise ValueError("Explicit AI curator credentials required for eval grants")
    owner = create_db_engine(settings, migration=True)
    app = create_db_engine(settings)
    try:
        with Session(owner) as session, session.begin():
            for query in queries.values():
                actor = actor_for(query)
                for collection in query.readable_collection_ids:
                    if session.get(Grant, (collection, actor.id)) is None:
                        session.execute(
                            insert(Grant).values(
                                collection_id=collection, actor_id=actor.id, role="reader"
                            )
                        )
        with Session(app) as session:
            rows = session.execute(
                select(
                    ChunkRecord,
                    SourceVersion.id.label("version_id"),
                    SourceVersion.document_id,
                    SourceVersion.source_version,
                )
                .join(Snapshot, ChunkRecord.snapshot_id == Snapshot.id)
                .join(SourceVersion, Snapshot.version_id == SourceVersion.id)
                .join(DocumentRecord, SourceVersion.document_id == DocumentRecord.id)
                .where(
                    DocumentRecord.active_snapshot_id == Snapshot.id,
                    DocumentRecord.deleted.is_(False),
                    Snapshot.eligible.is_(True),
                    Snapshot.pipeline_sha256 == fingerprint(cfg.embedding, cfg.chunking),
                )
            ).all()
        compiled: list[dict[str, Any]] = []
        for label in labels:
            relevant = []
            for section in label.relevant_sections:
                source = source_map[(section.document_id, section.version_id)]
                matches = [
                    r
                    for r in rows
                    if r.document_id == section.document_id
                    and r.source_version == source.source_version
                    and r.ChunkRecord.locator == "section:" + section.section_id
                ]
                # P04 labels whole sections. Require an unambiguous single chunk in this release.
                if len(matches) != 1:
                    raise ValueError("Section gold does not uniquely resolve to an active chunk")
                row = matches[0]
                if source.collection_id not in queries[label.query_id].readable_collection_ids:
                    raise ValueError("Positive gold crosses authorized scope")
                relevant.append(
                    {
                        "document_id": str(row.document_id),
                        "fixture_version_id": str(section.version_id),
                        "version_id": str(row.version_id),
                        "chunk_id": str(row.ChunkRecord.id),
                        "locator": row.ChunkRecord.locator,
                        "grade": section.grade,
                    }
                )
            compiled.append(
                {
                    "query_id": label.query_id,
                    "partition": label.partition,
                    "relevant": relevant,
                    "expected_outcome": label.expected_outcome,
                    "forbidden_document_ids": [str(d) for d in label.forbidden_document_ids],
                    "rationale": label.rationale,
                    "label_status": label.label_status,
                    "independent_review": label.independent_review,
                }
            )
        gold_path = BASE / "gold/v1.jsonl"
        raw = b"".join(
            (json.dumps(g, ensure_ascii=False, sort_keys=True) + "\n").encode()
            for g in sorted(compiled, key=lambda g: g["query_id"])
        )
        write_new(gold_path, raw)
        write_new(
            BASE / "gold/v1.lock.json",
            json_bytes(
                {
                    "gold_sha256": sha(gold_path),
                    "input_hashes": input_hashes(),
                    "implementation_sha256": code_hash(),
                    "code_hash_scope": "src/vmarket_ai Python source, canonical LF bytes",
                    "pipeline": pipeline_manifest(cfg.embedding, cfg.chunking),
                    "queries": len(compiled),
                    "status": "provisional_agent_authored",
                    "independent_human_review": "pending",
                }
            ),
        )
        print(json.dumps({"compiled_queries": len(compiled), "gold_sha256": sha(gold_path)}))
    finally:
        owner.dispose()
        app.dispose()


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for method in METHODS:
        group = [r for r in rows if r["method"] == method]
        positive = [r for r in group if r["metrics"]["1"]["hit"] is not None]
        summary: dict[str, Any] = {
            "queries": len(group),
            "positive_queries": len(positive),
            "zero_relevance_queries": len(group) - len(positive),
            "latency": latency([r["result"]["latency_ms"] for r in group]),
            "embedding_calls": sum(r["result"]["embedding_calls"] for r in group),
            "input_tokens": sum(r["result"]["input_tokens"] for r in group)
            if all(r["result"]["input_tokens"] is not None for r in group)
            else None,
            "billed_embedding_usd": sum(float(r["result"]["billed_embedding_usd"]) for r in group)
            if all(r["result"]["billed_embedding_usd"] is not None for r in group)
            else None,
            "cpu_energy_hosting_cost": "NOT_MEASURED",
            "forbidden_hits": sum(r["forbidden_hits"] for r in group),
            "zero_relevance_empty_results": sum(
                not r["result"]["hits"] for r in group if r["metrics"]["1"]["hit"] is None
            ),
            "at_k": {},
        }
        for k in (1, 3, 5):
            summary["at_k"][str(k)] = {
                name: sum(r["metrics"][str(k)][name] for r in positive) / len(positive)
                if positive
                else None
                for name in ("hit", "recall", "mrr", "ndcg")
            }
        result[method] = summary
    return result


async def run(split: str, output: Path, bundle: Path) -> None:
    if split not in {"train", "dev", "test"} or output.exists():
        raise ValueError("Choose a split and a fresh output directory")
    verify_release(DATA, Path("data/releases/v1.lock.json"))
    lock = json.loads((BASE / "gold/v1.lock.json").read_text(encoding="utf-8"))
    if (
        lock["gold_sha256"] != sha(BASE / "gold/v1.jsonl")
        or lock["input_hashes"] != input_hashes()
        or lock["implementation_sha256"] != code_hash()
    ):
        raise ValueError("Frozen evaluation inputs/code have changed")
    if split == "test":
        if output != BASE / "runs/test-v1":
            raise ValueError("Held-out evaluation has one designated, non-overwritable run")
        for name in (
            "selection.json",
            "config.json",
            "protocol.json",
            "gold/v1.jsonl",
            "gold/v1.lock.json",
        ):
            path = BASE / name
            committed = subprocess.check_output(["git", "show", "HEAD:" + path.as_posix()])
            if committed != path.read_bytes():
                raise ValueError("Test requires committed selection/config/gold freeze")
        selection = json.loads((BASE / "selection.json").read_text(encoding="utf-8"))
        if selection["implementation_sha256"] != code_hash() or selection["config_sha256"] != sha(
            BASE / "config.json"
        ):
            raise ValueError("Test config differs from development selection")
    cfg = config()
    queries = [q for q in records(DATA / "queries.jsonl", Query) if q.partition == split]
    gold = {
        r["query_id"]: r
        for r in [
            json.loads(line)
            for line in (BASE / "gold/v1.jsonl").read_text(encoding="utf-8").splitlines()
        ]
    }
    output.mkdir(parents=True)
    manifest: dict[str, Any] = {
        "status": "running",
        "split": split,
        "config_sha256": sha(BASE / "config.json"),
        "protocol_sha256": sha(BASE / "protocol.json"),
        "gold_sha256": sha(BASE / "gold/v1.jsonl"),
        "implementation_sha256": code_hash(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.version,
        "label_status": "provisional_agent_authored",
        "independent_human_review": "pending",
        "provider_inference_requests": 0,
    }
    (output / "manifest.json").write_bytes(json_bytes(manifest))
    loaded = perf_counter()
    provider = LocalE5EmbeddingProvider(bundle)
    manifest["provider_load_ms"] = (perf_counter() - loaded) * 1000
    engine = create_db_engine(load_settings())
    retriever = Retriever(engine, cfg, provider)
    rows: list[dict[str, Any]] = []
    try:
        with (output / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for query in queries:
                reference = gold[query.id]
                request = SearchRequest(
                    query=query.question,
                    collection_ids=query.requested_collection_ids,
                    as_of=date(2026, 10, 31),
                )
                identities = set()
                for method in METHODS:
                    result = await retriever.search(actor_for(query), request, method)
                    identities.add(result.eligible_corpus_sha256)
                    grades = {r["chunk_id"]: r["grade"] for r in reference["relevant"]}
                    ranked = [str(h.citation.chunk_id) for h in result.hits]
                    forbidden = sum(
                        str(h.citation.document_id) in reference["forbidden_document_ids"]
                        for h in result.hits
                    )
                    row = {
                        "query_id": query.id,
                        "partition": split,
                        "language": query.language,
                        "question": query.question,
                        "method": method,
                        "request": request.model_dump(mode="json"),
                        "result": result.model_dump(mode="json"),
                        "forbidden_hits": forbidden,
                        "metrics": {str(k): ranked_metrics(ranked, grades, k) for k in (1, 3, 5)},
                    }
                    rows.append(row)
                    handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    if forbidden or (
                        reference["expected_outcome"] == "deny_access" and result.hits
                    ):
                        raise ValueError("Authorization negative failed")
                if len(identities) != 1:
                    raise ValueError("Retrieval methods did not use identical authorized corpus")
        summary = summarize(rows)
        (output / "metrics.json").write_bytes(json_bytes(summary))
        csv_file = io.StringIO(newline="")
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(
            [
                "method",
                "k",
                "positive_queries",
                "hit",
                "recall",
                "mrr",
                "ndcg",
                "median_ms",
                "p95_ms",
                "input_tokens",
                "billed_embedding_usd",
            ]
        )
        for summary_method, values in summary.items():
            for k, scores in values["at_k"].items():
                writer.writerow(
                    [
                        summary_method,
                        k,
                        values["positive_queries"],
                        *[scores[n] for n in ("hit", "recall", "mrr", "ndcg")],
                        values["latency"]["median_ms"],
                        values["latency"]["p95_ms"],
                        values["input_tokens"],
                        values["billed_embedding_usd"],
                    ]
                )
        (output / "metrics.csv").write_text(csv_file.getvalue(), encoding="utf-8", newline="\n")
        failures = [
            {
                "query_id": r["query_id"],
                "method": r["method"],
                "metrics": r["metrics"],
                "rationale": gold[r["query_id"]]["rationale"],
            }
            for r in rows
            if r["metrics"]["1"]["hit"] == 0 or (r["metrics"]["5"]["recall"] or 1) < 1
        ]
        (output / "failures.json").write_bytes(json_bytes(failures))
        manifest.update(
            status="completed",
            queries=len(queries),
            predictions=len(rows),
            predictions_sha256=sha(output / "predictions.jsonl"),
            metrics_sha256=sha(output / "metrics.json"),
        )
        print(
            json.dumps(
                {
                    "split": split,
                    "queries": len(queries),
                    "predictions": len(rows),
                    "metrics": summary,
                }
            )
        )
    except Exception:
        manifest["status"] = "failed; inspect preserved partial artifacts, no automatic retry"
        raise
    finally:
        engine.dispose()
        (output / "manifest.json").write_bytes(json_bytes(manifest))


def select_development(run_dir: Path) -> None:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "completed" or manifest["split"] != "dev":
        raise ValueError("Selection requires a completed development split")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    method = min(
        METHODS,
        key=lambda m: (
            -metrics[m]["at_k"]["3"]["mrr"],
            -metrics[m]["at_k"]["5"]["recall"],
            metrics[m]["latency"]["median_ms"],
            m,
        ),
    )
    selection = {
        "status": "local_baseline_recommendation; not production approval",
        "selected_method": method,
        "config_sha256": sha(BASE / "config.json"),
        "implementation_sha256": code_hash(),
        "development_run": run_dir.as_posix(),
        "development_metrics_sha256": sha(run_dir / "metrics.json"),
        "selection_rule": json.loads((BASE / "protocol.json").read_text())["selection"],
        "heldout_used_for_selection": False,
        "independent_human_review": "pending",
    }
    write_new(BASE / "selection.json", json_bytes(selection))
    print(json.dumps(selection))


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline pinned P04 retrieval evaluation")
    parser.add_argument("action", choices=["prepare", "run", "select"])
    parser.add_argument("--split", choices=["train", "dev", "test"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--development-run", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare()
    elif args.action == "select" and args.development_run:
        select_development(args.development_run)
    elif args.action == "run" and args.split and args.output and args.bundle:
        asyncio.run(run(args.split, args.output, args.bundle))
    else:
        parser.error("Action requires its documented arguments")


if __name__ == "__main__":
    main()
