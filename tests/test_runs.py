import os
from uuid import uuid4

import pytest

from vmarket_ai.database import create_db_engine
from vmarket_ai.gateway.agent import AgentService
from vmarket_ai.gateway.mock import execute
from vmarket_ai.gateway.wire import GatewayError
from vmarket_ai.runs.store import RunStore


def planned(store, actor="a" * 64):
    row = store.start(actor, uuid4(), uuid4(), "List imports", (), uuid4(), now=1000)
    row = store.begin(row, row["revision"], uuid4(), 1030, now=1001)
    intent = AgentService.fake_plan({"question": "List imports", "collection_ids": []})
    response = {
        "protocol_version": 1,
        "request_id": str(uuid4()),
        "run_id": str(row["id"]),
        "step": 0,
        "kind": "tool_intent",
        "intent": intent,
    }
    return store.planned(row, response, uuid4(), now=1002)


def test_run_survives_new_store_and_binds_owner_and_revision(migrated):
    engine = create_db_engine(migrated)
    store = RunStore(engine)
    run = store.start("a" * 64, uuid4(), uuid4(), "List imports", (), uuid4(), now=1000)
    restored = RunStore(engine).get(run["id"], "a" * 64, (), uuid4(), now=1001)
    assert restored["conversation_id"] == run["conversation_id"]
    assert restored["status"] == "started" and restored["revision"] == 0
    with pytest.raises(GatewayError, match="RUN_NOT_AVAILABLE"):
        store.get(run["id"], "b" * 64, (), uuid4(), now=1001)
    cancelled = store.cancel(run["id"], "a" * 64, 0, (), uuid4(), now=1001)
    assert cancelled["status"] == "cancelled" and cancelled["revision"] == 1
    with pytest.raises(GatewayError, match="STEP_CONFLICT"):
        store.cancel(run["id"], "a" * 64, 0, (), uuid4(), now=1002)


def test_interrupted_read_becomes_unknown_and_is_not_redispatched(migrated):
    store = RunStore(create_db_engine(migrated))
    row = planned(store)
    leased = store.claim(row, row["revision"], uuid4(), 1010, now=1003)
    recovered = RunStore(store.engine).get(row["id"], "a" * 64, (), uuid4(), now=1011)
    assert (
        recovered["status"] == "waiting_for_operator" and recovered["reason"] == "OUTCOME_UNKNOWN"
    )
    with pytest.raises(GatewayError, match="STEP_CONFLICT"):
        store.record(
            leased,
            leased["revision"],
            leased["lease_id"],
            execute(leased["pending"]),
            uuid4(),
            now=1012,
        )
    resumed = store.recover(recovered, recovered["revision"], uuid4(), now=1012)
    assert resumed["pending"] is None and resumed["step"] == 1
    assert resumed["history"][0]["status"] == "unavailable"
    with pytest.raises(GatewayError, match="STEP_CONFLICT"):
        store.recover(recovered, recovered["revision"], uuid4(), now=1013)


def test_cancel_fences_inflight_read_and_prevents_late_result(migrated):
    store = RunStore(create_db_engine(migrated))
    row = planned(store)
    leased = store.claim(row, row["revision"], uuid4(), 1030, now=1003)
    store.cancel(row["id"], "a" * 64, leased["revision"], (), uuid4(), now=1004)
    with pytest.raises(GatewayError, match="STEP_CONFLICT"):
        store.record(
            leased,
            leased["revision"],
            leased["lease_id"],
            execute(leased["pending"]),
            uuid4(),
            now=1005,
        )
    current = store.get(row["id"], "a" * 64, (), uuid4(), now=1005)
    assert current["status"] == "cancelled" and current["history"] == []


def test_record_is_once_only_and_expiry_erases_payload_then_owner_purges(migrated):
    from sqlalchemy import func, select

    from vmarket_ai.runs.models import RunEvent

    store = RunStore(create_db_engine(migrated))
    row = planned(store)
    leased = store.claim(row, row["revision"], uuid4(), 1030, now=1003)
    observed = execute(leased["pending"])
    saved = store.record(
        leased, leased["revision"], leased["lease_id"], observed, uuid4(), now=1004
    )
    assert len(saved["history"]) == 1 and saved["summaries"][0]["item_count"] == 1
    with pytest.raises(GatewayError, match="STEP_CONFLICT"):
        store.record(leased, leased["revision"], leased["lease_id"], observed, uuid4(), now=1005)
    expired = store.get(row["id"], "a" * 64, (), uuid4(), now=1600)
    assert expired["status"] == "expired" and expired["question"] == "" and expired["history"] == []
    assert store.purge(now=1601) == 0
    assert store.purge(now=88000) == 1
    with store.engine.connect() as c:
        assert c.execute(select(func.count()).select_from(RunEvent)).scalar_one() == 0


def test_active_run_quota_is_bounded_and_expired_slots_are_reusable(migrated):
    store = RunStore(create_db_engine(migrated))
    for _ in range(8):
        store.start("a" * 64, uuid4(), uuid4(), "List imports", (), uuid4(), now=1000)
    with pytest.raises(GatewayError, match="BUDGET_EXCEEDED"):
        store.start("a" * 64, uuid4(), uuid4(), "List imports", (), uuid4(), now=1001)
    assert (
        store.start("a" * 64, uuid4(), uuid4(), "List imports", (), uuid4(), now=1601)["status"]
        == "started"
    )


PG = os.environ.get("AI_TEST_DATABASE_URL")
OWNER = os.environ.get("AI_TEST_OWNER_DATABASE_URL")


@pytest.mark.postgres
@pytest.mark.skipif(not PG or not OWNER, reason="Disposable AI PostgreSQL absent")
def test_pg_claim_cas_has_one_winner_and_protected_metadata():
    from concurrent.futures import ThreadPoolExecutor

    from pydantic import SecretStr
    from sqlalchemy import delete, func, select, text

    from vmarket_ai.runs.models import RunEvent, RunRecord
    from vmarket_ai.settings import Settings

    store = RunStore(create_db_engine(Settings(_env_file=None, database_url=SecretStr(PG))))
    owner = create_db_engine(Settings(_env_file=None, database_url=SecretStr(OWNER)))
    row = planned(store)
    try:

        def claim(_):
            try:
                store.claim(row, row["revision"], uuid4(), 1030, now=1003)
                return 200
            except GatewayError as e:
                return e.status

        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(claim, range(2))) == [200, 409]
        with store.engine.connect() as c:
            assert (
                c.execute(
                    select(func.count())
                    .select_from(RunEvent)
                    .where(RunEvent.run_id == row["id"], RunEvent.revision == 3)
                ).scalar_one()
                == 1
            )
            assert c.execute(
                text(
                    "SELECT "
                    "has_column_privilege(current_user,'ai.agent_runs','actor_ref','UPDATE'),"
                    "has_table_privilege(current_user,'ai.agent_runs','DELETE'),"
                    "has_table_privilege(current_user,'ai.agent_run_events','UPDATE')"
                )
            ).one() == (False, False, False)
    finally:
        with owner.begin() as c:
            c.execute(delete(RunRecord).where(RunRecord.id == row["id"]))
        owner.dispose()
        store.engine.dispose()


def test_knowledge_history_retains_counts_but_never_cached_sop_text(migrated):
    store = RunStore(create_db_engine(migrated))
    scope = str(uuid4())
    row = store.start("a" * 64, uuid4(), uuid4(), "SOP encoding", (scope,), uuid4(), now=1000)
    row = store.begin(row, 0, uuid4(), 1030, now=1001)
    intent = AgentService.fake_plan({"question": "SOP encoding", "collection_ids": [scope]})
    row = store.planned(
        row,
        {
            "protocol_version": 1,
            "request_id": str(uuid4()),
            "run_id": str(row["id"]),
            "step": 0,
            "kind": "tool_intent",
            "intent": intent,
        },
        uuid4(),
        now=1002,
    )
    row = store.claim(row, row["revision"], uuid4(), 1030, now=1003)
    observation = execute(intent)
    hits = []
    for _ in range(2):
        chunk = str(uuid4())
        hits.append(
            {
                "citation": {
                    "document_id": str(uuid4()),
                    "version_id": str(uuid4()),
                    "chunk_id": chunk,
                    "locator": {"kind": "section", "value": "mapping"},
                    "source_url": "/ai/citations/" + chunk,
                },
                "excerpt": "日本語" * 600,
                "score": 0.9,
                "retrieval_mode": "dense",
            }
        )
    observation["data"] = {"hits": hits}
    saved = store.record(row, row["revision"], row["lease_id"], observation, uuid4(), now=1004)
    assert saved["history"][0]["data"] == {"hits": []}
    assert saved["summaries"][0]["item_count"] == 2
