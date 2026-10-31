import asyncio
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select

from vmarket_ai.contracts import ChatRequest, EmbeddingRequest, Message
from vmarket_ai.database import ProviderUsage, create_db_engine
from vmarket_ai.providers.budget import BudgetExceeded, BudgetLedger
from vmarket_ai.providers.fake import FakeChatModel, FakeEmbeddingProvider
from vmarket_ai.providers.openrouter import OpenRouterChatModel, ProviderError, ProviderTimeout
from vmarket_ai.settings import Settings


def live_settings(migrated, **changes):
    return Settings(
        _env_file=None,
        **{
            "database_url": migrated.database_url,
            "provider_mode": "live",
            "live_enabled": True,
            "openrouter_api": SecretStr("synthetic-test-key"),
            "live_request_usd": Decimal("0.001"),
            "live_daily_usd": Decimal("0.01"),
            "live_daily_requests": 2,
            **changes,
        },
    )


def prompt():
    return ChatRequest(messages=(Message(role="user", content="Synthetic hello"),))


def catalog():
    return {"data": [{"id": "openrouter/free", "pricing": {"prompt": "0", "completion": "0"}}]}


def completion():
    return {
        "model": "synthetic/free",
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1, "cost": 0},
    }


async def test_fake_providers_are_deterministic_and_not_semantic_metrics():
    model = FakeChatModel()
    assert await model.complete(prompt()) == await model.complete(prompt())
    result = await FakeEmbeddingProvider().embed(EmbeddingRequest(texts=("A", "B")))
    assert result == await FakeEmbeddingProvider().embed(EmbeddingRequest(texts=("A", "B")))
    assert len(result.vectors[0]) == 32
    assert result.vectors[0] != result.vectors[1]
    assert sum(v * v for v in result.vectors[0]) == pytest.approx(1)


@pytest.mark.parametrize(
    "payload",
    [
        {"messages": []},
        {"messages": [{"role": "user", "content": ""}]},
        {"messages": [{"role": "user", "content": "hello"}], "max_output_tokens": 513},
        {"messages": [{"role": "user", "content": "hello"}], "api_key": "sentinel"},
    ],
)
def test_provider_invalid_input(payload):
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


async def test_live_adapter_success_is_mocked_and_usage_persisted(migrated):
    calls = []

    def handle(request):
        calls.append((request.method, str(request.url)))
        assert request.url.host == "openrouter.ai"
        return httpx.Response(200, json=catalog() if request.method == "GET" else completion())

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handle)
    )
    result = await model.complete(prompt())
    assert result.text == "OK" and result.cost_usd == 0
    assert calls == [
        ("GET", "https://openrouter.ai/api/v1/models"),
        ("POST", "https://openrouter.ai/api/v1/chat/completions"),
    ]
    with engine.connect() as connection:
        row = connection.execute(select(ProviderUsage.__table__)).mappings().one()
        assert row["state"] == "completed" and row["prompt_tokens"] == 2
    engine.dispose()


async def test_structured_output_is_explicit_free_only_and_disables_reasoning(migrated):
    captured = []

    def handle(request):
        if request.method == "POST":
            captured.append(__import__("json").loads(request.content))
        return httpx.Response(200, json=catalog() if request.method == "GET" else completion())

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handle)
    )
    schema = {"type": "object", "additionalProperties": False, "properties": {}, "required": []}
    await model.complete(prompt().model_copy(update={"structured_output": schema}))
    assert len(captured) == 1
    body = captured[0]
    assert body["model"] == "openrouter/free"
    assert body["response_format"]["json_schema"]["schema"] == schema
    assert body["provider"] == {"require_parameters": True}
    assert body["reasoning"] == {"enabled": False}
    engine.dispose()


async def test_safe_read_retry_but_post_never_retried(migrated):
    counts = {"GET": 0, "POST": 0}

    def handle(request):
        counts[request.method] += 1
        if request.method == "GET":
            return (
                httpx.Response(503) if counts["GET"] == 1 else httpx.Response(200, json=catalog())
            )
        return httpx.Response(503, text="sentinel-upstream-internal")

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handle)
    )
    with pytest.raises(ProviderError) as exc:
        await model.complete(prompt())
    assert "sentinel" not in str(exc.value)
    assert counts == {"GET": 2, "POST": 1}
    with pytest.raises(BudgetExceeded):
        await model.complete(prompt())
    assert counts["POST"] == 1
    engine.dispose()


async def test_provider_timeout_holds_reservation_and_blocks_next_call(migrated):
    def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        raise httpx.ReadTimeout("sentinel-private-prompt")

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    ledger = BudgetLedger(engine, settings)
    model = OpenRouterChatModel(settings, ledger, httpx.MockTransport(handle))
    with pytest.raises(ProviderTimeout) as exc:
        await model.complete(prompt())
    assert "sentinel" not in str(exc.value)
    with pytest.raises(BudgetExceeded):
        ledger.reserve()
    with engine.connect() as connection:
        assert connection.execute(select(ProviderUsage.state)).scalar_one() == "uncertain"
    engine.dispose()


async def test_outer_deadline_cancels_provider_wait(migrated):
    async def handle(request):
        if request.method == "GET":
            return httpx.Response(200, json=catalog())
        await asyncio.sleep(10)
        return httpx.Response(200, json=completion())

    settings = live_settings(migrated, request_deadline_seconds=0.1)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handle)
    )
    with pytest.raises(ProviderTimeout):
        await model.complete(prompt())
    engine.dispose()


@pytest.mark.parametrize(
    "reply",
    [
        {"data": [{"id": "openrouter/free", "pricing": {"prompt": "0.001", "completion": "0"}}]},
        {"data": []},
        {"data": [{"id": "openrouter/free", "pricing": {}}]},
    ],
)
async def test_unknown_or_paid_pricing_prevents_inference(migrated, reply):
    calls = []

    def handle(request):
        calls.append(request.method)
        return httpx.Response(200, json=reply)

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handle)
    )
    with pytest.raises(ProviderError):
        await model.complete(prompt())
    assert calls == ["GET"]
    engine.dispose()


async def test_unexpected_charge_is_recorded_and_stops_further_spend(migrated):
    reply = completion()
    reply["usage"]["cost"] = 0.02
    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    ledger = BudgetLedger(engine, settings)
    model = OpenRouterChatModel(
        settings,
        ledger,
        httpx.MockTransport(
            lambda r: httpx.Response(200, json=catalog() if r.method == "GET" else reply)
        ),
    )
    with pytest.raises(ProviderError):
        await model.complete(prompt())
    with pytest.raises(BudgetExceeded):
        ledger.reserve()
    with engine.connect() as connection:
        assert connection.execute(select(ProviderUsage.spent_microusd)).scalar_one() == 20000
    engine.dispose()
