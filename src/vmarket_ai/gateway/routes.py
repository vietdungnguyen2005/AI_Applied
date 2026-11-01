import asyncio
import time
from collections.abc import Coroutine
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from sqlalchemy.engine import Engine
from starlette.responses import JSONResponse

from vmarket_ai.gateway.agent import AgentService
from vmarket_ai.gateway.security import ContextVerifier
from vmarket_ai.gateway.wire import GatewayError, strict_json, validate
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS, PostgresEvidence
from vmarket_ai.qa.service import wire
from vmarket_ai.retrieval.spec import SearchRequest
from vmarket_ai.settings import Settings


async def pending(
    request: Request, task: Coroutine[Any, Any, dict[str, Any]], deadline: float
) -> dict[str, Any]:
    stopping = asyncio.Event()

    async def disconnected() -> None:
        while not stopping.is_set():
            if await request.is_disconnected():
                return
            await asyncio.sleep(0.05)

    work, watch = asyncio.create_task(task), asyncio.create_task(disconnected())
    try:
        async with asyncio.timeout(deadline):
            done, _ = await asyncio.wait((work, watch), return_when=asyncio.FIRST_COMPLETED)
            if watch in done:
                raise GatewayError("REQUEST_CANCELLED", 499)
            return await work
    finally:
        stopping.set()
        work.cancel()
        watch.cancel()
        await asyncio.gather(work, watch, return_exceptions=True)


def install(
    app: FastAPI, config: Settings, engine: Engine, service: AgentService | None = None
) -> None:
    verifier = ContextVerifier(engine, config.gateway_public_keys)
    agent = service or AgentService(
        OllamaChatModel(config) if config.provider_mode == "local" else None
    )
    evidence = PostgresEvidence(engine, config)

    if config.mode == "standalone":

        @app.post("/ai/agent/demo")
        async def demo(request: Request) -> dict[str, Any]:
            await context(request, "agent_step")
            payload = strict_json(await request.body())
            if (
                not isinstance(payload, dict)
                or set(payload) != {"question"}
                or not isinstance(payload["question"], str)
                or not 1 <= len(payload["question"]) <= 2000
            ):
                raise GatewayError("INPUT_INVALID", 400)
            from vmarket_ai.gateway.mock import run

            try:
                async with asyncio.timeout(config.request_deadline_seconds):
                    return await run(
                        agent,
                        {
                            "protocol_version": 1,
                            "question": payload["question"],
                            "request_id": request.state.request_id,
                            "run_id": str(uuid4()),
                            "collection_ids": list(map(str, DEMO_COLLECTIONS)),
                        },
                    )
            except TimeoutError:
                raise GatewayError("DEADLINE_EXCEEDED", 504) from None

    @app.exception_handler(GatewayError)
    async def failure(request: Request, error: GatewayError) -> JSONResponse:
        return JSONResponse(
            {
                "request_id": request.state.request_id,
                "code": error.code,
                "message": "Request unavailable; inspect the correlation ID.",
            },
            status_code=error.status,
        )

    async def context(request: Request, operation: str) -> dict[str, Any]:
        if config.mode == "integrated":
            claims = await verifier.verify(request, operation)
            if not set(claims["collection_ids"]).issubset(map(str, DEMO_COLLECTIONS)):
                raise GatewayError("ACCESS_DENIED", 403)
            return claims
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise GatewayError("ACCESS_DENIED", 403)
        if request.headers.get("origin") not in (
            None,
            f"http://127.0.0.1:{config.port}",
            f"http://localhost:{config.port}",
        ):
            raise GatewayError("ACCESS_DENIED", 403)
        return {"collection_ids": list(map(str, DEMO_COLLECTIONS)), "deadline_at": None}

    @app.post("/ai/agent/step")
    async def step(request: Request) -> dict[str, Any]:
        claims = await context(request, "agent_step")
        payload = strict_json(await request.body())
        validate("AgentStepRequest", payload)
        if config.mode == "integrated" and any(
            payload[k] != claims[k] for k in ("request_id", "run_id", "step")
        ):
            raise GatewayError("STEP_CONFLICT", 409)
        if not set(payload["collection_ids"]).issubset(claims["collection_ids"]):
            raise GatewayError("ACCESS_DENIED", 403)
        deadline = config.request_deadline_seconds
        if claims["deadline_at"]:
            deadline = min(
                deadline,
                datetime.fromisoformat(claims["deadline_at"].replace("Z", "+00:00")).timestamp()
                - time.time(),
            )
        try:
            response = await pending(request, agent.step(payload), deadline)
            validate("AgentStepResponse", response)
            return response
        except TimeoutError:
            raise GatewayError("DEADLINE_EXCEEDED", 504) from None

    @app.post("/ai/knowledge/search")
    async def knowledge(request: Request) -> dict[str, Any]:
        claims = await context(request, "knowledge_search")
        payload = strict_json(await request.body())
        validate(
            "ToolIntent",
            {
                "call_id": str(uuid4()),
                "tool_name": "search_supplier_knowledge",
                "arguments": payload,
            },
        )
        if not set(payload["collection_ids"]).issubset(claims["collection_ids"]):
            raise GatewayError("ACCESS_DENIED", 403)
        from datetime import UTC

        from vmarket_ai.retrieval.spec import RetrievalError

        try:
            async with asyncio.timeout(config.request_deadline_seconds):
                found = await evidence.retrieve(
                    DEMO_ACTOR,
                    SearchRequest(
                        query=payload["query"],
                        collection_ids=tuple(UUID(s) for s in payload["collection_ids"]),
                        as_of=datetime.now(UTC).date(),
                    ),
                )
                hits = []
                for hit in found.hits[: payload["top_k"]]:
                    source = evidence.current(
                        DEMO_ACTOR,
                        tuple(UUID(s) for s in payload["collection_ids"]),
                        hit.citation.chunk_id,
                    )
                    if source is None or source != hit.citation:
                        raise GatewayError("DOCUMENT_NOT_AVAILABLE", 404)
                    hits.append(
                        {
                            "citation": wire(source).model_dump(mode="json"),
                            "excerpt": source.text[:2000],
                            "score": hit.score,
                            "retrieval_mode": found.method,
                        }
                    )
                return {"hits": hits}
        except TimeoutError:
            raise GatewayError("DEADLINE_EXCEEDED", 504) from None
        except RetrievalError:
            raise GatewayError("DEPENDENCY_UNAVAILABLE", 503) from None
