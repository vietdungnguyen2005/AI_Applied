"""Opt-in local P13 question run using disposable P12 Java/BFF/AI storage."""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from p11_local_smoke import main
from pydantic import SecretStr

from vmarket_ai.database import create_db_engine
from vmarket_ai.evaluation.new_questions import DATASET, ROOT, scoring_labels, verify_inputs
from vmarket_ai.evaluation.new_score import aggregate, score_qa, score_retrieval
from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS, PostgresEvidence
from vmarket_ai.qa.service import SYSTEM, AnswerService
from vmarket_ai.qa.spec import AskRequest
from vmarket_ai.retrieval.spec import SearchRequest, SearchResult
from vmarket_ai.settings import Settings


class NoEvidence:
    async def retrieve(self, actor, request):
        return SearchResult(
            method="dense",
            hits=(),
            eligible_corpus_sha256="0" * 64,
            eligible_chunks=0,
            latency_ms=0,
            embedding_ms=0,
            sql_ms=0,
            embedding_calls=0,
            input_tokens=0,
            billed_embedding_usd=0,
            semantic_embeddings=True,
        )

    def current(self, actor, scopes, chunk_id):
        return None


class NoModelCall:
    async def complete(self, request):
        raise AssertionError("Empty evidence must return before any model call")


def exercise(
    *, operator_login, sql_connect, snapshot, report, ai_port, provider, migration_env, **unused
):
    inputs, lock = verify_inputs()
    # Record the exact committed protocol before any model is contacted.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report.update(
        dataset="p13-new-questions-v1",
        source_commit=commit,
        dataset_lock_sha256=hashlib.sha256((DATASET / "lock.json").read_bytes()).hexdigest(),
        input_hashes=lock["files_sha256"],
        predictions=[],
        label_review="pending",
    )
    journal = ROOT / ".local" / ("p13-new-questions-journal-" + uuid4().hex + ".jsonl")
    report["journal_file"] = journal.name

    def business():
        with sql_connect() as connection:
            return snapshot(connection)

    before = business()
    provider("local")
    with httpx.Client(base_url="http://127.0.0.1:11434", timeout=180, trust_env=False) as ollama:
        tags = ollama.get("/api/tags").json()["models"]
        model = next(m for m in tags if m["name"] == "qwen3.5:4b-q4_K_M")
        started = time.perf_counter()
        warm = ollama.post(
            "/api/generate",
            json={"model": model["name"], "keep_alive": "5m", "options": {"num_ctx": 4096}},
        )
        warm.raise_for_status()
        report["model_warmup_ms"] = (time.perf_counter() - started) * 1000
        report["model"] = {
            "name": model["name"],
            "digest": model["digest"],
            "runtime": ollama.get("/api/version").json(),
        }
    report["parameters"] = {
        "context": 4096,
        "temperature": 0.2,
        "seed": 42,
        "thinking": False,
        "max_output_tokens": 512,
        "qa_system_prompt_sha256": hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest(),
        "retrieval_top_k": 5,
        "reranker": "none",
    }
    settings = Settings(
        _env_file=None,
        mode="standalone",
        provider_mode="fake",
        live_enabled=False,
        qa_enabled=False,
        mapping_enabled=False,
        agent_enabled=False,
        runs_enabled=False,
        database_url=SecretStr(migration_env["AI_DATABASE_URL"]),
        qa_embedding_mode="local",
        qa_model_bundle=Path(migration_env["AI_QA_MODEL_BUNDLE"]),
    )
    engine = create_db_engine(settings)
    operator, csrf = operator_login()
    try:
        with closing(operator), journal.open("x", encoding="utf-8", newline="\n") as sink:

            def record(row):
                row["recorded_at_utc"] = datetime.now(UTC).isoformat()
                report["predictions"].append(row)
                sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                sink.flush()
                os.fsync(sink.fileno())

            profiles = operator.get("/api/ops/integration-profiles").json()
            selected = {
                scope: next(p for p in profiles if p["vendorCode"] == vendor and p["active"])
                for scope, vendor in (("a", "NAMI"), ("b", "RIVERBYTE"))
            }
            # Only inputs.jsonl is decoded here. Labels are parsed after all calls finish.
            for case in inputs:
                profile = selected[case["collection"]]
                body = {
                    "question": case["question"],
                    "language": case["language"],
                    "profile_id": profile["profileId"],
                    "profile_version": profile["version"],
                }
                as_of_at_start = datetime.now(UTC).date().isoformat()
                started = time.perf_counter()
                try:
                    response = operator.post(
                        "/api/ops/ai/ask", json=body, headers={"X-CSRF-TOKEN": csrf}
                    )
                    status, payload = response.status_code, response.json()
                except (httpx.HTTPError, ValueError):
                    status, payload = 0, None
                record(
                    {
                        "domain": "qa",
                        "case_id": case["id"],
                        "method": "signed_dense_local",
                        "as_of_utc_at_request": as_of_at_start,
                        "http_status": status,
                        "response": payload,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                    }
                )

            async def reads():
                evidence = PostgresEvidence(engine, settings)
                guard = AnswerService(
                    NoEvidence(), NoModelCall(), mode="local", deadline_seconds=25
                )
                as_of = datetime.now(UTC).date()
                report["retrieval_as_of_utc"] = as_of.isoformat()
                for case in inputs:
                    scope = DEMO_COLLECTIONS[0 if case["collection"] == "a" else 1]
                    for method in ("lexical", "dense", "hybrid"):
                        started = time.perf_counter()
                        try:
                            result = await evidence.retriever.search(
                                DEMO_ACTOR,
                                SearchRequest(
                                    query=case["question"], collection_ids=(scope,), as_of=as_of
                                ),
                                method,
                            )
                            hits = [
                                {
                                    "document_id": str(h.citation.document_id),
                                    "chunk_id": str(h.citation.chunk_id),
                                    "section": h.citation.locator.removeprefix("section:"),
                                    "score": h.score,
                                }
                                for h in result.hits
                            ]
                            row = {
                                "status": "ok",
                                "hits": hits,
                                "eligible_corpus_sha256": result.eligible_corpus_sha256,
                                "embedding_calls": result.embedding_calls,
                                "input_tokens": result.input_tokens,
                                "provider_billed_usd": str(result.billed_embedding_usd),
                            }
                        except Exception:
                            row = {"status": "unavailable", "hits": []}
                        record(
                            {
                                "domain": "retrieval",
                                "case_id": case["id"],
                                "method": method,
                                "latency_ms": (time.perf_counter() - started) * 1000,
                                **row,
                            }
                        )
                    started = time.perf_counter()
                    answer = await guard.ask(
                        DEMO_ACTOR,
                        AskRequest(
                            question=case["question"],
                            collection_ids=(scope,),
                            language=case["language"],
                        ),
                        uuid4(),
                    )
                    record(
                        {
                            "domain": "qa",
                            "case_id": case["id"],
                            "method": "empty_evidence_guard",
                            "http_status": 200,
                            "response": answer.model_dump(mode="json"),
                            "latency_ms": (time.perf_counter() - started) * 1000,
                        }
                    )

            asyncio.run(reads())
        assert len(report["predictions"]) == len(inputs) * 5
        labels = scoring_labels(inputs)
        for row in report["predictions"]:
            row["score"] = (
                score_qa(row, labels[row["case_id"]])
                if row["domain"] == "qa"
                else score_retrieval(row, labels[row["case_id"]])
            )
        qa = [r for r in report["predictions"] if r["domain"] == "qa"]
        retrieval = [r for r in report["predictions"] if r["domain"] == "retrieval"]
        for case in inputs:
            hashes = {
                r["eligible_corpus_sha256"]
                for r in retrieval
                if r["case_id"] == case["id"] and r["status"] == "ok"
            }
            if len(hashes) > 1:
                raise ValueError("Retrieval methods did not use the same eligible corpus")
        report["metrics"] = aggregate(qa, retrieval)
        report["journal_sha256"] = hashlib.sha256(journal.read_bytes()).hexdigest()
        after = business()
        assert before == after, "Read-only evaluation changed business data"
        signed_qa = [r for r in qa if r["method"] == "signed_dense_local"]
        report.update(
            status="PASS"
            if any(r["score"]["valid"] for r in signed_qa)
            and any(r["score"]["valid"] for r in retrieval)
            else "PARTIAL_DEPENDENCY_FAILURE",
            timestamp_utc=datetime.now(UTC).isoformat(),
            business_before=before,
            business_after=after,
            business_unchanged_11_tables=True,
            external_provider_calls=0,
            local_provider_billed_usd=0,
            compute_and_energy_cost="NOT_MEASURED",
            token_usage="NOT_RETURNED_BY_BFF",
            scope=(
                "new questions on shared known synthetic documents; "
                "provisional labels, no independent review"
            ),
            baseline=(
                "empty-evidence service guard only; no prompt-only LLM call, "
                "not matched HTTP latency"
            ),
            output_status="case outcomes may fail; PASS means the complete measurement ran",
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        sys.exit("Commit the preregistered protocol and inputs before inference")
    main(args.project2, args.output, qa=True, checks=exercise)
    print("P13_NEW_QUESTION_RUN_COMPLETED")
