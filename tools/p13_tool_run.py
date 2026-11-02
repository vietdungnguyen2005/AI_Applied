"""Run preregistered first-intent planner comparison against local Ollama only."""

import argparse
import asyncio
import csv
import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from vmarket_ai.evaluation.tool_questions import (
    DATASET,
    ROOT,
    aggregate,
    score,
    scoring_labels,
    verify_inputs,
)
from vmarket_ai.gateway.agent import SYSTEM, AgentService
from vmarket_ai.gateway.wire import GatewayError
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.qa.backend import DEMO_COLLECTIONS
from vmarket_ai.settings import Settings


class MeasuredModel:
    def __init__(self, model):
        self.model = model
        self.attempts = 0
        self.returned = []

    async def complete(self, request):
        self.attempts += 1
        result = await self.model.complete(request)
        # Do not persist untrusted raw model content; only validated public intents and usage.
        self.returned.append((result.prompt_tokens, result.completion_tokens))
        return result


async def run(output: Path) -> None:
    if output.exists():
        raise ValueError("Output must be a fresh directory")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("Commit the tool dataset and runner before model inference")
    inputs, lock = verify_inputs()
    protocol = json.loads((DATASET / "protocol.json").read_text(encoding="utf-8"))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    settings = Settings(
        _env_file=None,
        mode="standalone",
        provider_mode="local",
        live_enabled=False,
        agent_enabled=False,
        qa_enabled=False,
        mapping_enabled=False,
        runs_enabled=False,
        ollama_model="qwen3.5:4b-q4_K_M",
        ollama_context=4096,
        ollama_timeout_seconds=25,
    )
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:11434", timeout=180, trust_env=False, follow_redirects=False
    ) as client:
        model = next(
            m
            for m in (await client.get("/api/tags")).json()["models"]
            if m["name"] == settings.ollama_model
        )
        if model["digest"] != protocol["model_digest"]:
            raise ValueError("Installed local model digest differs from frozen protocol")
        runtime = (await client.get("/api/version")).json()
        start = time.perf_counter()
        warm = await client.post(
            "/api/generate",
            json={
                "model": settings.ollama_model,
                "keep_alive": "5m",
                "options": {"num_ctx": settings.ollama_context},
            },
        )
        warm.raise_for_status()
        warmup_ms = (time.perf_counter() - start) * 1000
    output.mkdir(parents=True)
    measured = MeasuredModel(OllamaChatModel(settings))
    services = {
        "deterministic_fake_router": AgentService(),
        "local_qwen_router": AgentService(measured),
    }
    predictions = []
    with (output / "raw.jsonl").open("x", encoding="utf-8", newline="\n") as sink:
        # Model input is limited to question, allowed scope and empty history.
        for case in inputs:
            for method, service in services.items():
                payload = {
                    "protocol_version": 1,
                    "request_id": str(uuid4()),
                    "run_id": str(uuid4()),
                    "step": 0,
                    "question": case["question"],
                    "collection_ids": [str(DEMO_COLLECTIONS[1])],
                    "tool_result": None,
                    "previous_results": [],
                }
                before_calls, before_results = measured.attempts, len(measured.returned)
                started = time.perf_counter()
                try:
                    response, error = await service.step(payload), None
                except GatewayError as exc:
                    response, error = None, {"code": exc.code, "status": exc.status}
                calls = measured.attempts - before_calls if method == "local_qwen_router" else 0
                returned = (
                    measured.returned[before_results:] if method == "local_qwen_router" else []
                )
                complete_usage = len(returned) == calls
                row = {
                    "case_id": case["id"],
                    "method": method,
                    "response": response,
                    "error": error,
                    "model_calls": calls,
                    "prompt_tokens": sum(x[0] for x in returned) if complete_usage else None,
                    "completion_tokens": sum(x[1] for x in returned) if complete_usage else None,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "recorded_at_utc": datetime.now(UTC).isoformat(),
                }
                predictions.append(row)
                sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                sink.flush()
                os.fsync(sink.fileno())
    labels = scoring_labels(inputs)
    for row in predictions:
        row["score"] = score(row, labels[row["case_id"]])
    metrics = aggregate(predictions)
    config = {
        "source_commit": commit,
        "dataset_lock_sha256": hashlib.sha256((DATASET / "lock.json").read_bytes()).hexdigest(),
        "dataset_file_hashes": lock["files_sha256"],
        "model": {"name": model["name"], "digest": model["digest"], "runtime": runtime},
        "parameters": {
            "context": 4096,
            "temperature": 0.2,
            "seed": 42,
            "thinking": False,
            "max_output_tokens": 256,
            "system_prompt_sha256": hashlib.sha256(SYSTEM.encode("utf-8")).hexdigest(),
        },
        "model_warmup_ms": warmup_ms,
        "scope": "first intent only; no tools dispatched, no Java auth or business action",
        "label_review": "provisional_agent_authored; independent review pending",
        "external_provider_calls": 0,
        "local_provider_billed_usd": 0,
        "compute_and_energy_cost": "NOT_MEASURED",
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    (output / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (output / "report.json").write_text(
        json.dumps({"predictions": predictions, "metrics": metrics}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with (output / "summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["method", "metric", "value", "n"], lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(metrics)
    manifest = {
        "status": "measurement_complete_not_quality_acceptance",
        "cases": len(inputs),
        "records": len(predictions),
        "source_commit": commit,
        "files_sha256": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("config.json", "raw.jsonl", "report.json", "summary.csv")
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    asyncio.run(run(parser.parse_args().output))
