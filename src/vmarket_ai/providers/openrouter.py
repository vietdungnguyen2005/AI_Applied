import asyncio
from decimal import Decimal
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from vmarket_ai.contracts import ChatRequest, ChatResult
from vmarket_ai.providers.budget import BudgetLedger
from vmarket_ai.settings import Settings


class ProviderError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Provider response unavailable or invalid; no automatic retry")


class ProviderTimeout(ProviderError):
    pass


class _Usage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cost: Decimal = Field(ge=0, allow_inf_nan=False)
    prompt_tokens: int = Field(ge=0, strict=True)
    completion_tokens: int = Field(ge=0, strict=True)


class _Message(BaseModel):
    content: str | None = Field(max_length=8000)


class _Choice(BaseModel):
    message: _Message


class _Completion(BaseModel):
    model: str = Field(max_length=200)
    choices: list[_Choice] = Field(min_length=1, max_length=1)
    usage: _Usage


class _Model(BaseModel):
    id: str
    pricing: dict[str, Decimal]


class _CatalogEntry(BaseModel):
    id: str
    pricing: JsonValue = None


class _Catalog(BaseModel):
    data: list[_CatalogEntry]


class OpenRouterChatModel:
    """Only openrouter/free; fixed origin, current zero-price preflight, no inference retry."""

    def __init__(
        self,
        settings: Settings,
        ledger: BudgetLedger,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (
            settings.provider_mode != "live"
            or not settings.live_enabled
            or not settings.openrouter_api
        ):
            raise ProviderError()
        self.settings = settings
        self.ledger = ledger
        self.transport = transport

    async def _catalog(self, client: httpx.AsyncClient) -> None:
        for attempt in range(2):
            try:
                response = await self._bounded(client, "GET", "/models")
                if response.status_code in {429, 502, 503, 504} and attempt == 0:
                    await asyncio.sleep(0.05)
                    continue
                response.raise_for_status()
                catalog = _Catalog.model_validate_json(response.content)
                entry = next(m for m in catalog.data if m.id == "openrouter/free")
                model = _Model.model_validate(entry.model_dump())
                if not {"prompt", "completion"}.issubset(model.pricing):
                    raise ProviderError()
                if any(v != 0 for v in model.pricing.values()):
                    raise ProviderError()
                return
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 0:
                    await asyncio.sleep(0.05)
                    continue
                raise ProviderError() from None
            except (ValidationError, StopIteration, ValueError, ArithmeticError):
                raise ProviderError() from None
        raise ProviderError()

    async def _bounded(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
    ) -> httpx.Response:
        async with client.stream(method, path, json=body) as response:
            if response.headers.get("content-encoding", "identity") != "identity":
                raise ProviderError()
            chunks = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=65_536):
                chunks.extend(chunk)
                if len(chunks) > 5_000_000:
                    raise ProviderError()
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=bytes(chunks),
                request=response.request,
            )

    async def complete(self, request: ChatRequest) -> ChatResult:
        usage_id: UUID | None = None
        settled = False
        key = self.settings.openrouter_api
        if key is None:
            raise ProviderError()
        try:
            async with asyncio.timeout(self.settings.request_deadline_seconds):
                async with httpx.AsyncClient(
                    base_url="https://openrouter.ai/api/v1",
                    transport=self.transport,
                    headers={
                        "Authorization": "Bearer " + key.get_secret_value(),
                        "Accept-Encoding": "identity",
                    },
                    timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                    follow_redirects=False,
                    trust_env=False,
                ) as client:
                    await self._catalog(client)
                    usage_id = await asyncio.to_thread(self.ledger.reserve)
                    response = await self._bounded(
                        client,
                        "POST",
                        "/chat/completions",
                        {
                            "model": "openrouter/free",
                            "max_tokens": request.max_output_tokens,
                            "messages": [message.model_dump() for message in request.messages],
                            **(
                                {
                                    "response_format": {
                                        "type": "json_schema",
                                        "json_schema": {
                                            "name": "evidence_proposal",
                                            "strict": True,
                                            "schema": request.structured_output,
                                        },
                                    },
                                    "provider": {"require_parameters": True},
                                    "reasoning": {"enabled": False},
                                }
                                if request.structured_output is not None
                                else {}
                            ),
                        },
                    )
                    response.raise_for_status()
                    output = _Completion.model_validate_json(response.content)
                    await asyncio.to_thread(
                        self.ledger.settle,
                        usage_id,
                        cost=output.usage.cost,
                        prompt_tokens=output.usage.prompt_tokens,
                        completion_tokens=output.usage.completion_tokens,
                    )
                    settled = True
                    content = output.choices[0].message.content
                    if output.usage.cost != 0 or not content:
                        raise ProviderError()
                    return ChatResult(
                        text=content,
                        model=output.model,
                        provider_mode="live",
                        prompt_tokens=output.usage.prompt_tokens,
                        completion_tokens=output.usage.completion_tokens,
                        cost_usd=output.usage.cost,
                    )
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderTimeout() from None
        except (httpx.HTTPError, ValidationError, SQLAlchemyError):
            raise ProviderError() from None
        finally:
            if usage_id is not None and not settled:
                try:
                    await asyncio.shield(asyncio.to_thread(self.ledger.settle, usage_id, cost=None))
                except SQLAlchemyError:
                    raise ProviderError() from None
