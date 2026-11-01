import base64
import json
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from test_gateway import signed, step

from vmarket_ai.app import create_app
from vmarket_ai.database import create_db_engine
from vmarket_ai.gateway.mock import execute


def setup(migrated):
    key = Ed25519PrivateKey.generate()
    config = migrated.model_copy(
        update={
            "mode": "integrated",
            "agent_enabled": True,
            "runs_enabled": True,
            "gateway_public_keys": {
                "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
            },
        }
    )
    return key, TestClient(
        create_app(config, create_db_engine(config)), base_url="http://127.0.0.1:8090"
    )


def post(client, key, run, command, step_index=0, **updates):
    identity = step(run_id=str(run), step=step_index)
    headers, body = signed(
        key,
        identity,
        body=json.dumps(command).encode(),
        path="/ai/runs/control",
        operation="run_control",
        collection_ids=[],
        **updates,
    )
    return client.post("/ai/runs/control", content=body, headers=headers)


def test_signed_run_roundtrip_checkpointed_without_browser_authority(migrated):
    key, client = setup(migrated)
    run = uuid4()
    with client:
        response = post(
            client,
            key,
            run,
            {
                "action": "start",
                "question": "List imports",
                "conversation_id": str(uuid4()),
                "collection_ids": [],
            },
        )
        assert response.status_code == 200, response.text
        from vmarket_ai.gateway.wire import validate

        validate("RunSnapshot", response.json())
        assert response.json()["state"]["revision"] == 0
        planned = post(client, key, run, {"action": "plan", "expected_revision": 0})
        assert planned.status_code == 200, planned.text
        ready = planned.json()
        assert ready["state"]["phase"] == "ready" and ready["state"]["revision"] == 2
        claimed = post(client, key, run, {"action": "claim", "expected_revision": 2}).json()
        observed = execute(claimed["pending_intent"])
        saved = post(
            client,
            key,
            run,
            {
                "action": "record",
                "expected_revision": 3,
                "lease_id": claimed["lease_id"],
                "observation": observed,
            },
        )
        assert saved.status_code == 200, saved.text
        complete = post(client, key, run, {"action": "plan", "expected_revision": 4}, step_index=1)
        assert complete.status_code == 200, complete.text
        state = complete.json()["state"]
        assert state["status"] == "completed" and state["step"] == 1
        assert (
            "data" not in state["observations"][0] and state["observations"][0]["item_count"] == 1
        )
        assert "question" not in state
        assert (
            post(
                client, key, run, {"action": "plan", "expected_revision": 4}, step_index=1
            ).status_code
            == 409
        )


def test_business_handoff_never_accepts_an_approval_as_resume(migrated):
    key, client = setup(migrated)
    run = uuid4()
    with client:
        assert (
            post(
                client,
                key,
                run,
                {
                    "action": "start",
                    "question": "Confirm import",
                    "conversation_id": str(uuid4()),
                    "collection_ids": [],
                },
            ).status_code
            == 200
        )
        paused = post(client, key, run, {"action": "plan", "expected_revision": 0}).json()["state"]
        assert paused["status"] == "waiting_for_operator" and paused["reason"] == "BUSINESS_HANDOFF"
        assert paused["can_resume"] is False
        assert (
            post(
                client,
                key,
                run,
                {"action": "recover", "expected_revision": paused["revision"], "approved": True},
            ).status_code
            == 400
        )
        assert (
            post(
                client, key, run, {"action": "recover", "expected_revision": paused["revision"]}
            ).status_code
            == 409
        )


@pytest.mark.parametrize("actor,expected", [("b" * 64, 404), ("a" * 64, 200)])
def test_run_payload_never_crosses_owner_boundary(migrated, actor, expected):
    key, client = setup(migrated)
    run = uuid4()
    with client:
        post(
            client,
            key,
            run,
            {
                "action": "start",
                "question": "List imports",
                "conversation_id": str(uuid4()),
                "collection_ids": [],
            },
        )
        assert (
            post(client, key, run, {"action": "inspect"}, actor_ref=actor).status_code == expected
        )


@pytest.mark.parametrize(
    "content", ["not JSON", '{"tool_name":"confirm_import","job_id":"","query":""}']
)
def test_bad_planner_output_is_failed_once_and_cannot_be_resumed(migrated, monkeypatch, content):
    from decimal import Decimal

    from vmarket_ai.contracts import ChatResult
    from vmarket_ai.gateway.agent import AgentService

    class Bad:
        calls = 0

        async def complete(self, request):
            self.calls += 1
            return ChatResult(
                text=content,
                model="test-only",
                provider_mode="fake",
                prompt_tokens=0,
                completion_tokens=0,
                cost_usd=Decimal(0),
            )

    model = Bad()
    monkeypatch.setattr("vmarket_ai.gateway.routes.AgentService", lambda *_: AgentService(model))
    key, client = setup(migrated)
    run = uuid4()
    with client:
        post(
            client,
            key,
            run,
            {
                "action": "start",
                "question": "List imports",
                "conversation_id": str(uuid4()),
                "collection_ids": [],
            },
        )
        assert post(client, key, run, {"action": "plan", "expected_revision": 0}).status_code == 502
        current = post(client, key, run, {"action": "inspect"}).json()["state"]
        assert current["status"] == "failed" and current["reason"] == "OUTPUT_INVALID"
        assert (
            post(
                client, key, run, {"action": "plan", "expected_revision": current["revision"]}
            ).status_code
            == 409
        )
        assert model.calls == 1


async def test_planner_timeout_is_bounded_and_does_not_implicitly_retry(migrated):
    import asyncio
    import time

    from vmarket_ai.gateway.agent import AgentService
    from vmarket_ai.gateway.wire import GatewayError
    from vmarket_ai.runs.service import RunService
    from vmarket_ai.runs.spec import RunCommand
    from vmarket_ai.runs.store import RunStore

    class Slow:
        calls = 0
        stopped = False

        async def complete(self, request):
            self.calls += 1
            try:
                await asyncio.sleep(30)
            finally:
                self.stopped = True

    model = Slow()
    store = RunStore(create_db_engine(migrated))
    service = RunService(store, AgentService(model))
    run = uuid4()
    claims = {
        "actor_ref": "a" * 64,
        "run_id": str(run),
        "request_id": str(uuid4()),
        "collection_ids": [],
        "step": 0,
    }
    await service.execute(
        RunCommand(
            action="start", question="List imports", conversation_id=uuid4(), collection_ids=()
        ),
        claims,
        time.time() + 25,
    )
    with pytest.raises(GatewayError, match="DEADLINE_EXCEEDED"):
        await service.execute(
            RunCommand(action="plan", expected_revision=0), claims, time.time() + 0.05
        )
    state = store.get(run, "a" * 64, (), uuid4())
    assert state["status"] == "failed" and model.calls == 1 and model.stopped
