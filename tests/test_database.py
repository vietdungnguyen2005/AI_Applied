import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from conftest import migrate
from pydantic import SecretStr
from sqlalchemy import insert, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from vmarket_ai.database import Collection, ProviderUsage, create_db_engine, database_ready
from vmarket_ai.providers.budget import BudgetExceeded, BudgetLedger
from vmarket_ai.settings import Settings

# Preserve only the test-DB opt-in; ordinary AI_* settings are cleared by conftest.
POSTGRES_TEST_URL = os.environ.get("AI_TEST_DATABASE_URL")


def test_sqlite_upgrade_downgrade_and_synthetic_constraint(migrated):
    engine = create_db_engine(migrated)
    assert database_ready(engine)
    with engine.begin() as connection:
        connection.execute(insert(Collection).values(id=uuid4(), label="Synthetic demo"))
    with engine.connect() as connection:
        assert connection.execute(select(Collection.synthetic)).scalar_one() is True
    engine.dispose()
    config = Config("alembic.ini")
    config.attributes["settings"] = migrated
    command.downgrade(config, "base")
    engine = create_db_engine(migrated)
    assert "collections" not in inspect(engine).get_table_names()
    engine.dispose()
    migrate(migrated)
    engine = create_db_engine(migrated)
    assert database_ready(engine)
    engine.dispose()


def test_budget_reservation_is_atomic_under_concurrency(migrated):
    settings = Settings(
        _env_file=None,
        database_url=migrated.database_url,
        live_request_usd=Decimal("0.001"),
        live_daily_usd=Decimal("0.01"),
        live_daily_requests=2,
    )
    engine = create_db_engine(settings)
    ledger = BudgetLedger(engine, settings)

    def reserve(_):
        try:
            usage_id = ledger.reserve()
            ledger.settle(usage_id, cost=Decimal("0"))
            return usage_id
        except BudgetExceeded:
            return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(reserve, range(8)))
    accepted = len([r for r in results if r is not None])
    assert 1 <= accepted <= 2
    for _ in range(2 - accepted):
        ledger.settle(ledger.reserve(), cost=Decimal("0"))
    with pytest.raises(BudgetExceeded):
        ledger.reserve()
    engine.dispose()


def test_sqlite_budget_foreign_key_is_actually_enforced(migrated):
    engine = create_db_engine(migrated)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            insert(ProviderUsage).values(
                id=uuid4(),
                provider="missing-provider",
                day=date(2026, 1, 1),
                state="reserved",
                reserved_microusd=1,
            )
        )
    engine.dispose()


@pytest.mark.postgres
@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="Disposable AI PostgreSQL opt-in not configured")
def test_real_postgres_schema_vector_and_app_permissions():
    settings = Settings(
        _env_file=None,
        database_url=SecretStr(POSTGRES_TEST_URL),
        live_request_usd=Decimal("0.001"),
        live_daily_usd=Decimal("0.1"),
        live_daily_requests=100,
    )
    engine = create_db_engine(settings)
    assert database_ready(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname='vector'")
            ).scalar_one()
            == "vector"
        )
        assert not connection.execute(
            text("SELECT has_schema_privilege(current_user,'ai','CREATE')")
        ).scalar_one()
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("CREATE TABLE ai.should_not_exist(id integer)"))
    with pytest.raises(DBAPIError), engine.begin() as connection:
        connection.execute(text("DELETE FROM ai.alembic_version"))
    ledger = BudgetLedger(engine, settings)
    usage_id = ledger.reserve()
    with pytest.raises(BudgetExceeded):
        BudgetLedger(engine, settings).reserve()
    ledger.settle(usage_id, cost=Decimal("0"))
    engine.dispose()
