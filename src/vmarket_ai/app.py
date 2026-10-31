import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from typing import Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from vmarket_ai.database import create_db_engine, database_ready
from vmarket_ai.observability import request_event
from vmarket_ai.settings import Settings, load_settings


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"] = "ok"


class Readiness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ready", "not_ready"]
    provider_mode: Literal["fake", "live"]


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


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
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

    return app
