"""Explicit bounded synthetic development probe; not unseen or human-reviewed QA evidence."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from time import perf_counter

import httpx
from pydantic import ValidationError

from vmarket_ai.app import create_app
from vmarket_ai.contracts import ChatRequest, ChatResult, Message
from vmarket_ai.database import create_db_engine
from vmarket_ai.providers.budget import BudgetExceeded, BudgetLedger
from vmarket_ai.providers.openrouter import OpenRouterChatModel, ProviderError
from vmarket_ai.qa.backend import DEMO_COLLECTIONS, PostgresEvidence
from vmarket_ai.qa.service import AnswerService
from vmarket_ai.qa.spec import BaselineProposal
from vmarket_ai.settings import load_settings

BASELINE_SYSTEM = """Answer a fictional supplier operations question without retrieval.
Do not invent supplier-specific facts. Return only JSON:
{"decision":"answer|insufficient","answer":"text or null"}.
If facts are missing, set decision insufficient and answer null. No citations are available.
"""


class RecordedModel:
    def __init__(self, model: OpenRouterChatModel) -> None:
        self.model = model
        self.outputs: list[ChatResult] = []
        self.attempts = 0

    async def complete(self, request: ChatRequest) -> ChatResult:
        if self.attempts >= 8:
            raise BudgetExceeded()
        self.attempts += 1
        result = await self.model.complete(request)
        self.outputs.append(result)
        return result


async def run(output: Path, live: bool) -> None:
    if not live or output.exists():
        raise ValueError("Explicit --live and a fresh output directory are required")
    settings = load_settings()
    if not settings.qa_enabled or settings.provider_mode != "live":
        raise ValueError("Use enabled live QA with the documented budgets")
    path = Path("evals/qa/cases.jsonl")
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if len(cases) != 4:
        raise ValueError("This probe is bounded to four synthetic cases")
    output.mkdir(parents=True)
    engine = create_db_engine(settings)
    model = RecordedModel(OpenRouterChatModel(settings, BudgetLedger(engine, settings)))
    service = AnswerService(PostgresEvidence(engine, settings), model, mode="live")
    app = create_app(settings, engine, service)
    rows = []
    stop = False
    started = perf_counter()
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:8090"
        ) as client:
            with (output / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
                for case in cases:
                    scope = DEMO_COLLECTIONS[0 if case["collection"] == "a" else 1]
                    for mode in ("retrieval", "prompt_only"):
                        before = len(model.outputs)
                        if stop:
                            row = {
                                "case_id": case["id"],
                                "mode": mode,
                                "status": "NOT_RUN_AFTER_PROVIDER_FAILURE",
                            }
                        elif mode == "retrieval":
                            response = await client.post(
                                "/ai/ask",
                                json={
                                    "question": case["question"],
                                    "collection_ids": [str(scope)],
                                    "language": case["language"],
                                },
                            )
                            body = response.json()
                            row = {
                                "case_id": case["id"],
                                "mode": mode,
                                "http_status": response.status_code,
                                "response": body,
                                "request_id": response.headers.get("x-request-id"),
                            }
                            if response.status_code in {429, 503, 504}:
                                stop = True
                            row["decision_correct"] = (
                                response.status_code == 200 and body["status"] == case["expected"]
                            )
                            row["factual_anchor_proxy"] = (
                                case["expected"] == "answered"
                                and response.status_code == 200
                                and body["status"] == "answered"
                                and all(
                                    a.lower() in (body["answer"] or "").lower()
                                    for a in case["anchors"]
                                )
                            )
                            row["citation_verified"] = (
                                response.status_code == 200
                                and body["status"] == "answered"
                                and bool(body["citations"])
                            )
                            if response.status_code == 200:
                                row["citation_open_statuses"] = [
                                    (await client.get(c["source_url"])).status_code
                                    for c in body["citations"]
                                ]
                        else:
                            try:
                                completion = await model.complete(
                                    ChatRequest(
                                        messages=(
                                            Message(role="system", content=BASELINE_SYSTEM),
                                            Message(role="user", content=case["question"]),
                                        ),
                                        max_output_tokens=256,
                                    )
                                )
                                proposal = BaselineProposal.model_validate_json(completion.text)
                                row = {
                                    "case_id": case["id"],
                                    "mode": mode,
                                    "status": "completed",
                                    "proposal": proposal.model_dump(),
                                    "citation_verified": False,
                                    "decision_correct": (
                                        "answered" if proposal.decision == "answer" else "abstained"
                                    )
                                    == case["expected"],
                                    "factual_anchor_proxy": case["expected"] == "answered"
                                    and proposal.decision == "answer"
                                    and all(
                                        a.lower() in (proposal.answer or "").lower()
                                        for a in case["anchors"]
                                    ),
                                }
                            except ValidationError:
                                row = {
                                    "case_id": case["id"],
                                    "mode": mode,
                                    "status": "OUTPUT_INVALID",
                                }
                            except (ProviderError, BudgetExceeded):
                                row = {
                                    "case_id": case["id"],
                                    "mode": mode,
                                    "status": "PROVIDER_UNAVAILABLE_NO_RETRY",
                                }
                                stop = True
                        row["model_outputs"] = [
                            r.model_dump(mode="json") for r in model.outputs[before:]
                        ]
                        rows.append(row)
                        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                        handle.flush()
        summary = {
            "status": "partial_provider_failure" if stop else "completed",
            "cases_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "cases": len(cases),
            "rows": len(rows),
            "elapsed_seconds": perf_counter() - started,
            "independent_human_review": "pending",
            "human_semantic_factual_accuracy": "NOT_RUN",
            "human_citation_relevance_review": "NOT_RUN",
            "notes": (
                "Anchor matching is a proxy, not semantic factual correctness. "
                "Four development cases; not unseen evaluation."
            ),
            "by_mode": {
                m: {
                    "case_count": 4,
                    "positive_cases": 2,
                    "negative_cases": 2,
                    "decision_correct": sum(
                        r.get("decision_correct", False) for r in rows if r["mode"] == m
                    ),
                    "positive_anchor_pass": sum(
                        r.get("factual_anchor_proxy", False) for r in rows if r["mode"] == m
                    ),
                    "citation_verified_answers": sum(
                        r.get("citation_verified", False) for r in rows if r["mode"] == m
                    ),
                }
                for m in ("retrieval", "prompt_only")
            },
            "provider_call_attempts": model.attempts,
            "completed_calls": len(model.outputs),
            "reported_cost_usd": str(sum(r.cost_usd for r in model.outputs)),
            "prompt_tokens": sum(r.prompt_tokens for r in model.outputs),
            "completion_tokens": sum(r.completion_tokens for r in model.outputs),
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic free-only QA probe, no paid fallback")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.output, args.live))
