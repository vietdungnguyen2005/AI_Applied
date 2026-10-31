"""Loopback-only Ollama inference. Never downloads, forwards keys or invokes cloud fallback."""

import asyncio
import json
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field, ValidationError

from vmarket_ai.contracts import ChatRequest, ChatResult
from vmarket_ai.providers.openrouter import ProviderError, ProviderTimeout
from vmarket_ai.settings import Settings


class _Message(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=8000)
    tool_calls: list[object] | None = None


class _Reply(BaseModel):
    model: str
    done: bool
    done_reason: str = "stop"
    message: _Message
    prompt_eval_count: int = Field(ge=0, strict=True)
    eval_count: int = Field(ge=0, strict=True)


class OllamaChatModel:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        if settings.provider_mode != "local" or settings.live_enabled:
            raise ProviderError()
        self.settings, self.transport = settings, transport
        self._slot = asyncio.Semaphore(1)

    async def _read(self, client: httpx.AsyncClient, path: str, body: dict[str, object]) -> bytes:
        async with client.stream("POST", path, json=body) as response:
            response.raise_for_status()
            if response.headers.get("content-encoding", "identity") != "identity":
                raise ProviderError()
            data = bytearray()
            async for block in response.aiter_bytes(chunk_size=16384):
                data.extend(block)
                if len(data) > 1_000_000:
                    raise ProviderError()
            return bytes(data)

    async def complete(self, request: ChatRequest) -> ChatResult:
        try:
            async with (
                asyncio.timeout(self.settings.ollama_timeout_seconds),
                self._slot,
                httpx.AsyncClient(
                    base_url="http://127.0.0.1:11434",
                    transport=self.transport,
                    trust_env=False,
                    follow_redirects=False,
                    headers={"Accept-Encoding": "identity"},
                    timeout=httpx.Timeout(self.settings.ollama_timeout_seconds),
                ) as client,
            ):
                info = json.loads(
                    await self._read(client, "/api/show", {"model": self.settings.ollama_model})
                )
                if (
                    info.get("remote_host")
                    or info.get("remote_model")
                    or info.get("details", {}).get("quantization_level") != "Q4_K_M"
                ):
                    raise ProviderError()
                body: dict[str, object] = {
                    "model": self.settings.ollama_model,
                    "stream": False,
                    "think": False,
                    "messages": [m.model_dump() for m in request.messages],
                    "options": {
                        "num_ctx": self.settings.ollama_context,
                        "num_predict": request.max_output_tokens,
                        "temperature": 0.2,
                        "seed": 42,
                    },
                    "keep_alive": "2m",
                }
                if request.structured_output is not None:
                    body["format"] = request.structured_output
                output = _Reply.model_validate_json(await self._read(client, "/api/chat", body))
                if (
                    not output.done
                    or output.done_reason != "stop"
                    or output.model != self.settings.ollama_model
                    or output.message.role != "assistant"
                    or output.message.tool_calls
                ):
                    raise ProviderError()
                return ChatResult(
                    text=output.message.content,
                    model=output.model,
                    provider_mode="local",
                    prompt_tokens=output.prompt_eval_count,
                    completion_tokens=output.eval_count,
                    cost_usd=Decimal("0"),
                )
        except (httpx.TimeoutException, TimeoutError):
            raise ProviderTimeout() from None
        except (httpx.HTTPError, ValidationError, ValueError, AttributeError, TypeError):
            raise ProviderError() from None
