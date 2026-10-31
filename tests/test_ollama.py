import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from vmarket_ai.contracts import ChatRequest, Message
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.providers.openrouter import ProviderError, ProviderTimeout
from vmarket_ai.settings import Settings


def test_local_default_choice_and_no_api_key_requirement():
    s = config()
    assert s.ollama_model == "qwen3.5:4b-q4_K_M" and s.openrouter_api is None
    assert s.provider_mode == "local" and not s.live_enabled


def config(**changes):
    return Settings(_env_file=None, provider_mode="local", **changes)


def prompt():
    return ChatRequest(
        messages=(Message(role="user", content="Synthetic source"),),
        structured_output={"type": "object"},
    )


def reply(**changes):
    return {
        "model": "qwen3.5:4b-q4_K_M",
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": '{"decision":"insufficient","claims":[]}'},
        "prompt_eval_count": 25,
        "eval_count": 10,
        **changes,
    }


async def test_local_payload_no_auth_proxy_download_or_billing(migrated, monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        assert request.url.host == "127.0.0.1" and request.url.port == 11434
        assert "authorization" not in request.headers and "cookie" not in request.headers
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"details": {"quantization_level": "Q4_K_M"}})
        assert request.url.path == "/api/chat"
        body = json.loads(request.content)
        assert body["think"] is False and body["stream"] is False
        assert body["format"] == {"type": "object"}
        assert body["options"]["num_ctx"] == 4096
        assert body["options"]["num_predict"] == 128
        return httpx.Response(200, json=reply())

    monkeypatch.setenv("HTTPS_PROXY", "http://invalid-proxy.example:1")
    result = await OllamaChatModel(
        config(openrouter_api="synthetic-unused-key"), httpx.MockTransport(handle)
    ).complete(prompt())
    assert result.provider_mode == "local" and result.cost_usd == 0
    assert result.prompt_tokens == 25 and result.completion_tokens == 10
    assert len(requests) == 2


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ollama_model": "qwen3.5:cloud"},
        {"ollama_model": "https://evil.example/model"},
        {"ollama_context": 131072},
        {"ollama_timeout_seconds": 31},
        {"live_enabled": True},
        {"private_container": True},
    ],
)
def test_cloud_tags_oversize_context_and_live_flags_are_rejected(kwargs):
    with pytest.raises(ValidationError):
        config(**kwargs)


@pytest.mark.parametrize(
    "metadata",
    [
        {"remote_host": "https://ollama.com", "details": {"quantization_level": "Q4_K_M"}},
        {"remote_model": "cloud-model", "details": {"quantization_level": "Q4_K_M"}},
        {"details": {"quantization_level": "F16"}},
        [],
    ],
)
async def test_local_preflight_refuses_remote_alias_or_unexpected_format(metadata):
    paths = []

    def handle(request):
        paths.append(request.url.path)
        return httpx.Response(200, json=metadata)

    with pytest.raises(ProviderError):
        await OllamaChatModel(config(), httpx.MockTransport(handle)).complete(prompt())
    assert paths == ["/api/show"]


@pytest.mark.parametrize(
    "changes",
    [
        {"done": False},
        {"done_reason": "length"},
        {"model": "different-model"},
        {"message": {"role": "assistant", "content": ""}},
        {"message": {"role": "tool", "content": "invented"}},
        {"message": {"role": "assistant", "content": "invented", "tool_calls": [{}]}},
        {"prompt_eval_count": -1},
        {"eval_count": True},
    ],
)
async def test_invalid_local_output_is_not_accepted_or_retried(changes):
    calls = []

    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(
            200,
            json={"details": {"quantization_level": "Q4_K_M"}}
            if request.url.path == "/api/show"
            else reply(**changes),
        )

    with pytest.raises(ProviderError):
        await OllamaChatModel(config(), httpx.MockTransport(handle)).complete(prompt())
    assert calls == ["/api/show", "/api/chat"]


@pytest.mark.parametrize("status", [404, 429, 500, 503, 302])
async def test_http_errors_fail_without_pull_or_redirect_or_retry(status):
    calls = []

    def handle(request):
        calls.append(request.url.path)
        return httpx.Response(status, headers={"Location": "https://evil.example"})

    with pytest.raises(ProviderError):
        await OllamaChatModel(config(), httpx.MockTransport(handle)).complete(prompt())
    assert calls == ["/api/show"]


async def test_local_timeout_and_response_size_limits():
    async def slow(request):
        await asyncio.sleep(1)

    with pytest.raises(ProviderTimeout):
        await OllamaChatModel(
            config(ollama_timeout_seconds=0.001), httpx.MockTransport(slow)
        ).complete(prompt())

    def large(request):
        return httpx.Response(200, content=b"x" * 1_000_001)

    with pytest.raises(ProviderError):
        await OllamaChatModel(config(), httpx.MockTransport(large)).complete(prompt())


async def test_shared_adapter_serializes_requests():
    active = 0
    maximum = 0

    async def handle(request):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(
            200,
            json={"details": {"quantization_level": "Q4_K_M"}}
            if request.url.path == "/api/show"
            else reply(),
        )

    model = OllamaChatModel(config(), httpx.MockTransport(handle))
    await asyncio.gather(model.complete(prompt()), model.complete(prompt()))
    assert maximum == 1
