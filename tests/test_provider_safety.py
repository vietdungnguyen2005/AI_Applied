from decimal import Decimal

import httpx
import pytest
from pydantic import TypeAdapter, ValidationError
from test_providers import catalog, completion, live_settings, prompt

from vmarket_ai.contracts import ToolIntent
from vmarket_ai.database import create_db_engine
from vmarket_ai.providers.budget import BudgetExceeded, BudgetLedger
from vmarket_ai.providers.openrouter import OpenRouterChatModel, ProviderError


def test_pending_reservation_survives_new_ledger_instance(migrated):
    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    first = BudgetLedger(engine, settings)
    usage_id = first.reserve()
    second = BudgetLedger(engine, settings)
    with pytest.raises(BudgetExceeded):
        second.reserve()
    first.settle(usage_id, cost=Decimal("0"))
    second.settle(second.reserve(), cost=Decimal("0"))
    engine.dispose()


def test_typed_tool_interface_rejects_mutation_and_arbitrary_path():
    adapter = TypeAdapter(ToolIntent)
    base = {
        "call_id": "11111111-1111-4111-8111-111111111111",
        "tool_name": "get_imports",
        "arguments": {},
    }
    assert adapter.validate_python(base).tool_name == "get_imports"
    for payload in [
        {**base, "tool_name": "confirm_import"},
        {**base, "arguments": {"url": "https://example.invalid"}},
    ]:
        with pytest.raises(ValidationError):
            adapter.validate_python(payload)


@pytest.mark.parametrize(
    "reply",
    [
        {},
        {"model": "fake", "choices": [], "usage": {"cost": 0}},
        {**completion(), "usage": {"prompt_tokens": 1, "completion_tokens": 1}},
    ],
)
async def test_malformed_or_unknown_usage_blocks_live(migrated, reply):
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
        BudgetLedger(engine, settings).reserve()
    engine.dispose()


async def test_unrelated_catalog_metadata_does_not_break_free_preflight(migrated):
    data = catalog()
    data["data"].append({"id": "other/model", "pricing": {"overrides": [{"nested": True}]}})
    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings,
        BudgetLedger(engine, settings),
        httpx.MockTransport(
            lambda r: httpx.Response(200, json=data if r.method == "GET" else completion())
        ),
    )
    assert (await model.complete(prompt())).cost_usd == 0
    engine.dispose()


async def test_redirect_does_not_forward_key_to_another_origin(migrated):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://example.invalid/steal"})

    settings = live_settings(migrated)
    engine = create_db_engine(settings)
    model = OpenRouterChatModel(
        settings, BudgetLedger(engine, settings), httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderError):
        await model.complete(prompt())
    assert all(url.startswith("https://openrouter.ai/") for url in calls)
    engine.dispose()
