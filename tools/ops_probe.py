"""Bounded loopback health load probe; never sends application data or model requests."""

import argparse
import asyncio
import json
import platform
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from vmarket_ai.retrieval.metrics import latency


async def probe(base: str, count: int, concurrency: int, transport=None) -> dict:
    origin = urlsplit(base)
    if (
        origin.scheme != "http"
        or origin.hostname not in {"127.0.0.1", "localhost", "::1"}
        or origin.username
        or origin.password
        or origin.query
        or origin.fragment
        or origin.path not in {"", "/"}
        or not 1 <= count <= 1000
        or not 1 <= concurrency <= 16
    ):
        raise ValueError("Loopback HTTP origin and bounded request/concurrency counts required")
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(
        base_url=base.rstrip("/"),
        timeout=2,
        trust_env=False,
        follow_redirects=False,
        transport=transport,
    ) as client:

        async def request(index):
            async with sem:
                trace = str(uuid4())
                started = time.perf_counter()
                try:
                    response = await client.get(
                        "/health" if index % 2 == 0 else "/ready", headers={"X-Request-ID": trace}
                    )
                    status, echoed = (
                        response.status_code,
                        response.headers.get("x-request-id") == trace,
                    )
                except httpx.HTTPError:
                    status, echoed = 0, False
                return {
                    "endpoint": "/health" if index % 2 == 0 else "/ready",
                    "status": status,
                    "request_id": trace,
                    "correlation_echo": echoed,
                    "elapsed_ms": (time.perf_counter() - started) * 1000,
                }

        started = time.perf_counter()
        observations = await asyncio.gather(*(request(i) for i in range(count)))
        duration = time.perf_counter() - started
    return {
        "scope": "local health/readiness only; no model/tool quality or production SLA",
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "requests": count,
        "concurrency": concurrency,
        "duration_seconds": duration,
        "error_rate": sum(r["status"] != 200 for r in observations) / count,
        "correlation_coverage": sum(r["correlation_echo"] for r in observations) / count,
        "latency_all_outcomes": latency([r["elapsed_ms"] for r in observations]),
        "model_calls": 0,
        "provider_charge_usd": 0,
        "observations": observations,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8090")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a fresh output file")
    result = asyncio.run(probe(args.base, args.requests, args.concurrency))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k != "observations"}))
