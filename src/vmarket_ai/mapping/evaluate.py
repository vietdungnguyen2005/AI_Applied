"""Explicit local comparison on known train/dev/regression data; no held-out inference."""

import argparse
import asyncio
import hashlib
import json
import math
import statistics
import subprocess
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx

from vmarket_ai.contracts import ChatRequest, ChatResult
from vmarket_ai.database import create_db_engine
from vmarket_ai.datasets.release import InputRecord, load_mapping_input
from vmarket_ai.mapping.policy import JAVA_COMMIT, StandalonePolicy
from vmarket_ai.mapping.service import MappingService
from vmarket_ai.mapping.spec import MappingError, MappingRequest
from vmarket_ai.mapping.store import SQLDraftStore
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.qa.backend import DEMO_ACTOR, PostgresEvidence
from vmarket_ai.settings import load_settings


class MeasuredModel:
    def __init__(self, model: OllamaChatModel) -> None:
        self.model = model
        self.attempts = 0
        self.results: list[ChatResult] = []

    async def complete(self, request: ChatRequest) -> ChatResult:
        self.attempts += 1
        result = await self.model.complete(request)
        self.results.append(result)
        return result


async def run(output: Path) -> None:
    import base64

    settings = load_settings()
    if (
        settings.provider_mode != "local"
        or settings.qa_embedding_mode != "local"
        or not settings.mapping_enabled
        or output.exists()
    ):
        raise ValueError("Enabled local mapping/E5 and a fresh output directory required")
    output.mkdir(parents=True)
    root = Path("data/v1")
    records = [
        InputRecord.model_validate_json(s)
        for s in (root / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    # Exclude held-out inputs before projection or inference, including their candidate gold.
    selected = [r for r in records if r.partition != "test" and r.contract == "supplier_three"]
    source_hashes = {
        p.as_posix(): hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for p in sorted(Path("src/vmarket_ai").rglob("*.py"))
    }
    config = {
        "model": settings.ollama_model,
        "context": settings.ollama_context,
        "temperature": 0.2,
        "seed": 42,
        "thinking": False,
        "output_tokens": 256,
        "sample_rows": 2,
        "sample_cell_characters": 160,
        "partitions": ["train", "dev", "regression"],
        "test_inference": "NOT_RUN",
        "case_ids": [r.id for r in selected],
        "java_policy_commit": JAVA_COMMIT,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "implementation_sha256_lf": source_hashes,
        "labels_sha256": hashlib.sha256((root / "labels/mapping.jsonl").read_bytes()).hexdigest(),
        "independent_human_review": "pending",
    }
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    engine = create_db_engine(settings)
    model = MeasuredModel(OllamaChatModel(settings))
    service = MappingService(
        StandalonePolicy(),
        SQLDraftStore(engine),
        model,
        PostgresEvidence(engine, settings),
        mode="local",
        deadline_seconds=settings.request_deadline_seconds,
    )
    rows: list[dict[str, object]] = []
    try:
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:11434", trust_env=False, follow_redirects=False, timeout=180
        ) as client:
            tags = (await client.get("/api/tags")).json()
            installed = next(t for t in tags["models"] if t["name"] == settings.ollama_model)
            warm = await client.post(
                "/api/generate",
                json={
                    "model": settings.ollama_model,
                    "keep_alive": "5m",
                    "options": {"num_ctx": settings.ollama_context},
                },
            )
            warm.raise_for_status()
            config["installed_model"] = installed
            config["ollama_version"] = (await client.get("/api/version")).json()
        # Gold loaded only by scorer; service/provider never receive labels or case metadata.
        labels = {
            r["case_id"]: r
            for r in [
                json.loads(s)
                for s in (root / "labels/mapping.jsonl").read_text(encoding="utf-8").splitlines()
            ]
        }
        with (output / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as sink:
            for record in selected:
                data = load_mapping_input(root, Path("data/releases/v1.lock.json"), record.id)
                for method in ("rule", "ai"):
                    req = MappingRequest(
                        raw_base64=base64.b64encode(data.raw_bytes).decode(),
                        declared_encoding=data.declared_encoding,
                        selected_vendor_code=data.selected_vendor_code,
                        method=method,
                        synthetic=True,
                    )
                    before = model.attempts
                    started = perf_counter()
                    row: dict[str, object] = {
                        "case_id": record.id,
                        "method": method,
                        "partition": record.partition,
                        "fixture_supplier": record.supplier,
                        "selected_vendor": data.selected_vendor_code,
                    }
                    try:
                        response = await service.suggest(DEMO_ACTOR, req, uuid4())
                        row["response"] = response.model_dump(mode="json")
                        predicted = {a.target_field: a.source_header for a in response.assignments}
                        row["status"] = response.status
                        row["has_assignments"] = bool(predicted)
                        row["model_output_rejected"] = "MODEL_OUTPUT_INVALID" in response.warnings
                        row["model_unavailable"] = "MODEL_UNAVAILABLE" in response.warnings
                        row["required_field_coverage"] = len(predicted) / 3
                        row["citation_current_checks"] = sum(
                            len(a.citations) for a in response.assignments
                        )
                    except MappingError as error:
                        predicted = {}
                        row.update(
                            status="input_error" if error.status in (400, 413) else "error",
                            error=error.code,
                            http_status=error.status,
                            required_field_coverage=0,
                            model_output_rejected=False,
                            model_unavailable=False,
                            has_assignments=False,
                        )
                    gold = labels[record.id]
                    target = gold["target_to_source"]
                    row.update(
                        latency_ms=(perf_counter() - started) * 1000,
                        adapter_attempts=model.attempts - before,
                        exact_mapping=(predicted == target) if target is not None else None,
                        required_field_edits_proxy=sum(
                            predicted.get(t) != h for t, h in target.items()
                        )
                        if target is not None
                        else None,
                        expected_status=gold["expected_suggestion"],
                        mapping_gold_present=target is not None,
                        status_matches_provisional_label=row["status"]
                        == gold["expected_suggestion"],
                        business_condition_not_evaluated=gold["expected_business_condition"],
                    )
                    rows.append(row)
                    sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    sink.flush()
                    print(
                        json.dumps(
                            {
                                "case": record.id,
                                "method": method,
                                "status": row["status"],
                                "exact": row["exact_mapping"],
                            }
                        ),
                        flush=True,
                    )
        summary = {}
        for method in ("rule", "ai"):
            for supplier in ("all", "a", "b"):
                group = [
                    r
                    for r in rows
                    if r["method"] == method
                    and (supplier == "all" or r["fixture_supplier"] == supplier)
                ]
                eligible = [r for r in group if r["exact_mapping"] is not None]
                latencies = sorted(float(str(r["latency_ms"])) for r in group)
                summary[f"{method}/{supplier}"] = {
                    "cases": len(group),
                    "mapping_labeled_cases": len(eligible),
                    "exact_mapping_correct": sum(r["exact_mapping"] is True for r in eligible),
                    "required_field_coverage_mean": statistics.mean(
                        float(str(r["required_field_coverage"])) for r in eligible
                    ),
                    "required_field_edits_proxy": sum(
                        int(str(r["required_field_edits_proxy"])) for r in eligible
                    ),
                    "abstained": sum(r["status"] == "abstained" for r in group),
                    "input_rejected": sum(r["status"] == "input_error" for r in group),
                    "provider_or_dependency_errors": sum(r["status"] == "error" for r in group),
                    "model_output_rejected": sum(r["model_output_rejected"] is True for r in group),
                    "model_unavailable": sum(r["model_unavailable"] is True for r in group),
                    "adapter_attempts": sum(int(str(r["adapter_attempts"])) for r in group),
                    "model_output_rejection_rate_per_case": sum(
                        r["model_output_rejected"] is True for r in group
                    )
                    / len(group),
                    "abstention_rate_per_case": sum(r["status"] == "abstained" for r in group)
                    / len(group),
                    "negative_gold_cases_with_assignments": sum(
                        r["mapping_gold_present"] is False and r["has_assignments"] is True
                        for r in group
                    ),
                    "p50_ms": statistics.median(latencies),
                    "p95_ms_nearest_rank": latencies[math.ceil(0.95 * len(latencies)) - 1],
                }
        report = {
            "status": "known_development_regression_comparison",
            "summary": summary,
            "local_adapter_attempts": model.attempts,
            "returned_prompt_tokens": sum(r.prompt_tokens for r in model.results),
            "returned_completion_tokens": sum(r.completion_tokens for r in model.results),
            "external_provider_calls": 0,
            "provider_billed_usd": "0",
            "actual_human_edit_acceptance_metrics": "NOT_RUN",
            "semantic_review": "pending",
            "heldout_test_inference": "NOT_RUN",
            "predictions_sha256": hashlib.sha256(
                (output / "predictions.jsonl").read_bytes()
            ).hexdigest(),
        }
        (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report), flush=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Explicit local P08 train/dev/regression comparison"
    )
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
