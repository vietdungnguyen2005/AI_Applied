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
from vmarket_ai.qa.service import AnswerService, wire
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
    app: FastAPI,
    config: Settings,
    engine: Engine,
    service: AgentService | None = None,
    *,
    qa_service: AnswerService | None = None,
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

    if config.mode == "integrated" and config.qa_enabled:
        from pydantic import ValidationError

        from vmarket_ai.contracts import StrictModel
        from vmarket_ai.qa.fake import FakeEvidenceModel
        from vmarket_ai.qa.spec import AskRequest

        class CitationRead(StrictModel):
            chunk_id: UUID
            collection_ids: tuple[UUID, ...]

        prototype = qa_service or AnswerService(
            evidence,
            OllamaChatModel(config) if config.provider_mode == "local" else FakeEvidenceModel(),
            mode="local" if config.provider_mode == "local" else "fake",
        )

        def qa_scope(payload: AskRequest | CitationRead, claims: dict[str, Any]) -> None:
            if (
                claims["step"] != 0
                or not 1 <= len(payload.collection_ids) <= 10
                or (
                    len(set(payload.collection_ids)) != len(payload.collection_ids)
                    or not set(map(str, payload.collection_ids)).issubset(claims["collection_ids"])
                )
            ):
                raise GatewayError("ACCESS_DENIED", 403)

        def qa_deadline(claims: dict[str, Any]) -> float:
            return max(
                0,
                min(
                    config.request_deadline_seconds,
                    datetime.fromisoformat(claims["deadline_at"].replace("Z", "+00:00")).timestamp()
                    - time.time(),
                ),
            )

        @app.post("/ai/ask")
        async def signed_ask(request: Request) -> dict[str, Any]:
            claims = await context(request, "ask")
            try:
                payload = AskRequest.model_validate(strict_json(await request.body()))
            except ValidationError:
                raise GatewayError("INPUT_INVALID", 400) from None
            qa_scope(payload, claims)
            deadline = qa_deadline(claims)

            async def answer() -> dict[str, Any]:
                qa = AnswerService(
                    prototype.retrieval,
                    prototype.model,
                    mode=prototype.mode,
                    deadline_seconds=deadline,
                )
                result = await qa.ask(DEMO_ACTOR, payload, UUID(claims["request_id"]))
                return result.model_dump(mode="json")

            try:
                return await pending(request, answer(), deadline)
            except TimeoutError:
                raise GatewayError("DEADLINE_EXCEEDED", 504) from None

        @app.post("/ai/citations/read")
        async def signed_citation(request: Request) -> dict[str, Any]:
            claims = await context(request, "documents_read")
            try:
                payload = CitationRead.model_validate(strict_json(await request.body()))
            except ValidationError:
                raise GatewayError("INPUT_INVALID", 400) from None
            qa_scope(payload, claims)

            async def read() -> dict[str, Any]:
                source = prototype.retrieval.current(
                    DEMO_ACTOR, payload.collection_ids, payload.chunk_id
                )
                if source is None:
                    raise GatewayError("DOCUMENT_NOT_AVAILABLE", 404)
                return {
                    "request_id": claims["request_id"],
                    "citation": wire(source).model_dump(mode="json"),
                    "excerpt": source.text[:2000],
                    "truncated": len(source.text) > 2000,
                }

            try:
                return await pending(request, read(), qa_deadline(claims))
            except TimeoutError:
                raise GatewayError("DEADLINE_EXCEEDED", 504) from None

    if config.runs_enabled:
        from pydantic import ValidationError

        from vmarket_ai.runs.service import RunService
        from vmarket_ai.runs.spec import RunCommand
        from vmarket_ai.runs.store import RunStore

        runs = RunService(RunStore(engine), agent)

        @app.post("/ai/runs/control")
        async def control_run(request: Request) -> dict[str, Any]:
            claims = await context(request, "run_control")
            try:
                command = RunCommand.model_validate(strict_json(await request.body()))
            except ValidationError:
                raise GatewayError("INPUT_INVALID", 400) from None
            deadline = min(
                time.time() + config.request_deadline_seconds,
                datetime.fromisoformat(claims["deadline_at"].replace("Z", "+00:00")).timestamp(),
            )
            try:
                return await pending(
                    request, runs.execute(command, claims, deadline), max(0, deadline - time.time())
                )
            except TimeoutError:
                raise GatewayError("DEADLINE_EXCEEDED", 504) from None

    if config.mode == "integrated" and config.mapping_enabled:
        from pydantic import ValidationError

        from vmarket_ai.gateway.mapping import SignedMapping, SnapshotPolicy
        from vmarket_ai.mapping.service import MappingService
        from vmarket_ai.mapping.store import SQLDraftStore

        @app.post("/ai/mapping/suggest")
        async def mapping(request: Request) -> dict[str, Any]:
            claims = await context(request, "mapping_suggest")
            try:
                payload = SignedMapping.model_validate(strict_json(await request.body()))
            except ValidationError:
                raise GatewayError("INPUT_INVALID", 400) from None
            policy = SnapshotPolicy(payload)
            scope = policy.scope(payload.input.selected_vendor_code)
            if scope is None or str(scope) not in claims["collection_ids"] or claims["step"] != 0:
                raise GatewayError("ACCESS_DENIED", 403)
            deadline = min(
                config.request_deadline_seconds,
                datetime.fromisoformat(claims["deadline_at"].replace("Z", "+00:00")).timestamp()
                - time.time(),
            )

            async def draft() -> dict[str, Any]:
                mapper = MappingService(
                    policy,
                    SQLDraftStore(engine),
                    agent.model,
                    evidence,
                    mode="local" if config.provider_mode == "local" else "fake",
                    deadline_seconds=deadline,
                )
                result = await mapper.suggest(DEMO_ACTOR, payload.input, UUID(claims["request_id"]))
                # Excerpts only for sources already selected by mapping, rechecking current ACL.
                sources = {}
                for assignment in result.assignments:
                    for ref in assignment.citations:
                        source = evidence.current(DEMO_ACTOR, (scope,), ref.chunk_id)
                        if source is None or wire(source) != ref:
                            raise GatewayError("DOCUMENT_NOT_AVAILABLE", 404)
                        sources[str(ref.chunk_id)] = {
                            "citation": ref.model_dump(mode="json"),
                            "excerpt": source.text[:2000],
                        }
                return {
                    "draft": result.model_dump(mode="json"),
                    "evidence": list(sources.values())[:2],
                }

            try:
                return await pending(request, draft(), deadline)
            except TimeoutError:
                raise GatewayError("DEADLINE_EXCEEDED", 504) from None

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
