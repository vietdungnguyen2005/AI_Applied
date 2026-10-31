import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vmarket_ai.contracts import ChatModel
from vmarket_ai.database import create_db_engine, database_ready
from vmarket_ai.observability import request_event
from vmarket_ai.providers.budget import BudgetLedger
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.providers.openrouter import OpenRouterChatModel
from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS, PostgresEvidence
from vmarket_ai.qa.fake import FakeEvidenceModel
from vmarket_ai.qa.service import AnswerService
from vmarket_ai.qa.spec import AskRequest, AskResponse, QAError
from vmarket_ai.settings import Settings, load_settings


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready", "not_ready"]
    provider_mode: Literal["fake", "live", "local"]


def error(request_id: str, code: str, status: int) -> JSONResponse:
    return JSONResponse(
        {
            "request_id": request_id,
            "code": code,
            "message": "Request unavailable; inspect the correlation ID.",
        },
        status_code=status,
    )


class RequestBoundary:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = monotonic()
        request_id = str(uuid4())
        status = 500
        response_started = False
        route = (
            scope["path"] if scope["path"] in {"/health", "/ready", "/openapi.json"} else "unknown"
        )
        if scope["path"] == "/ai/ask":
            route = "/ai/ask"
        elif scope["path"].startswith("/ai/citations/"):
            route = "/ai/citations/{chunk_id}"

        async def wrapped_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                message["headers"] = [
                    *[
                        (k, v)
                        for k, v in message.get("headers", [])
                        if k.lower() not in {b"x-request-id", b"cache-control"}
                    ],
                    (b"x-request-id", request_id.encode()),
                    (b"cache-control", b"no-store"),
                ]
            await send(message)

        try:
            ids = [v for k, v in scope.get("headers", []) if k.lower() == b"x-request-id"]
            if ids:
                try:
                    raw = ids[0].decode("ascii")
                    if len(ids) != 1 or str(UUID(raw)) != raw:
                        raise ValueError
                    request_id = raw
                except (ValueError, UnicodeError):
                    await error(request_id, "INPUT_INVALID", 400)(scope, receive, wrapped_send)
                    return
            scope.setdefault("state", {})["request_id"] = request_id
            body = bytearray()
            async with asyncio.timeout(3):
                while True:
                    part = await receive()
                    if part["type"] == "http.disconnect":
                        status = 499
                        return
                    body.extend(part.get("body", b""))
                    if len(body) > 65_536:
                        await error(request_id, "INPUT_TOO_LARGE", 413)(
                            scope, receive, wrapped_send
                        )
                        return
                    if not part.get("more_body", False):
                        break
            delivered = False

            async def replay() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, replay, wrapped_send)
        except TimeoutError:
            if not response_started:
                await error(request_id, "DEADLINE_EXCEEDED", 504)(scope, receive, wrapped_send)
        except Exception:
            if not response_started:
                await error(request_id, "INTERNAL_ERROR", 500)(scope, receive, wrapped_send)
        finally:
            request_event(request_id, route, status, (monotonic() - started) * 1000)


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
    qa_service: AnswerService | None = None,
) -> FastAPI:
    config = settings or load_settings()
    database = engine or create_db_engine(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        database.dispose()

    app = FastAPI(
        title="V-Market AI — local foundation",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(RequestBoundary)

    @app.exception_handler(RequestValidationError)
    async def input_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error(str(request.state.request_id), "INPUT_INVALID", 400)

    @app.exception_handler(QAError)
    async def qa_error(request: Request, exc: QAError) -> JSONResponse:
        return error(str(request.state.request_id), exc.code, exc.status)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = "METHOD_NOT_ALLOWED" if exc.status_code == 405 else "ROUTE_NOT_AVAILABLE"
        return error(str(request.state.request_id), code, exc.status_code)

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health()

    @app.get("/ready", response_model=Readiness, responses={503: {"model": Readiness}})
    def ready() -> JSONResponse:
        try:
            available = database_ready(database)
        except SQLAlchemyError:
            available = False
        response = Readiness(
            status="ready" if available else "not_ready", provider_mode=config.provider_mode
        )
        return JSONResponse(response.model_dump(), status_code=200 if available else 503)

    if config.qa_enabled:
        if qa_service is None:
            evidence = PostgresEvidence(database, config)
            chat: ChatModel
            if config.provider_mode == "local":
                chat = OllamaChatModel(config)
            elif config.provider_mode == "live":
                chat = OpenRouterChatModel(config, BudgetLedger(database, config))
            else:
                chat = FakeEvidenceModel()
            qa_service = AnswerService(
                evidence,
                chat,
                mode=config.provider_mode,
                deadline_seconds=config.request_deadline_seconds,
            )
        prototype = qa_service

        def local_boundary(request: Request) -> None:
            # Fixed public synthetic scope; no supplied actor/cookie/header becomes identity.
            if request.url.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise QAError("ACCESS_DENIED", 403)
            origin = request.headers.get("origin")
            if origin and origin not in {
                f"http://127.0.0.1:{config.port}",
                f"http://localhost:{config.port}",
            }:
                raise QAError("ACCESS_DENIED", 403)

        @app.post("/ai/ask", response_model=AskResponse)
        async def ask(payload: AskRequest, request: Request) -> AskResponse:
            local_boundary(request)
            if not set(payload.collection_ids).issubset(DEMO_COLLECTIONS):
                raise QAError("ACCESS_DENIED", 403)
            service = AnswerService(
                prototype.retrieval,
                prototype.model,
                mode=config.provider_mode,
                deadline_seconds=config.request_deadline_seconds,
            )
            return await service.ask(DEMO_ACTOR, payload, UUID(request.state.request_id))

        @app.get("/ai/citations/{chunk_id}")
        def citation(chunk_id: UUID, request: Request) -> dict[str, object]:
            local_boundary(request)
            source = prototype.retrieval.current(DEMO_ACTOR, DEMO_COLLECTIONS, chunk_id)
            if source is None:
                raise QAError("DOCUMENT_NOT_AVAILABLE", 404)
            return source.model_dump(mode="json")

    return app
