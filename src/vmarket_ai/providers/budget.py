from datetime import UTC, datetime
from decimal import ROUND_CEILING, Decimal
from uuid import UUID, uuid4

from sqlalchemy import Table, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine

from vmarket_ai.database import BudgetDay, ProviderControl, ProviderUsage
from vmarket_ai.settings import Settings


class BudgetExceeded(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Live provider budget unavailable; no request was authorized")


def micros(value: Decimal) -> int:
    return int((value * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


class BudgetLedger:
    """Atomic AI-owned reservations shared across processes; unknown outcomes block the day."""

    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        self.request_cap = micros(settings.live_request_usd)
        self.daily_cap = micros(settings.live_daily_usd)
        self.daily_requests = settings.live_daily_requests

    def reserve(self) -> UUID:
        day = datetime.now(UTC).date()
        usage_id = uuid4()
        table = BudgetDay.__table__
        control = ProviderControl.__table__
        assert isinstance(table, Table) and isinstance(control, Table)
        statement = (
            pg_insert(table) if self.engine.dialect.name == "postgresql" else sqlite_insert(table)
        )
        statement = statement.values(
            provider="openrouter",
            day=day,
            requests_used=0,
            reserved_microusd=0,
            spent_microusd=0,
            blocked=False,
        ).on_conflict_do_nothing(index_elements=["provider", "day"])
        with self.engine.begin() as connection:
            create_control = (
                pg_insert(control)
                if self.engine.dialect.name == "postgresql"
                else sqlite_insert(control)
            )
            connection.execute(
                create_control.values(
                    provider="openrouter", pending_usage_id=None, blocked=False
                ).on_conflict_do_nothing(index_elements=["provider"])
            )
            grant = connection.execute(
                update(control)
                .where(
                    control.c.provider == "openrouter",
                    control.c.blocked.is_(False),
                    control.c.pending_usage_id.is_(None),
                )
                .values(pending_usage_id=usage_id)
            )
            if grant.rowcount != 1:
                raise BudgetExceeded()
            connection.execute(statement)
            result = connection.execute(
                update(table)
                .where(
                    table.c.provider == "openrouter",
                    table.c.day == day,
                    table.c.blocked.is_(False),
                    table.c.requests_used < self.daily_requests,
                    table.c.spent_microusd + table.c.reserved_microusd + self.request_cap
                    <= self.daily_cap,
                )
                .values(
                    requests_used=table.c.requests_used + 1,
                    reserved_microusd=table.c.reserved_microusd + self.request_cap,
                )
            )
            if self.request_cap <= 0 or result.rowcount != 1:
                raise BudgetExceeded()
            connection.execute(
                insert(ProviderUsage).values(
                    id=usage_id,
                    provider="openrouter",
                    day=day,
                    state="reserved",
                    reserved_microusd=self.request_cap,
                )
            )
        return usage_id

    def settle(
        self,
        usage_id: UUID,
        *,
        cost: Decimal | None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> None:
        usage = ProviderUsage.__table__
        budget = BudgetDay.__table__
        control = ProviderControl.__table__
        assert isinstance(usage, Table) and isinstance(budget, Table) and isinstance(control, Table)
        with self.engine.begin() as connection:
            row = (
                connection.execute(select(usage).where(usage.c.id == usage_id).with_for_update())
                .mappings()
                .one()
            )
            if row["state"] != "reserved":
                return
            unknown = cost is None
            charge = 0 if cost is None else micros(cost)
            # A supposedly free model charging anything stops further calls for review.
            blocked = unknown or charge > 0
            connection.execute(
                update(budget)
                .where(
                    budget.c.provider == row["provider"],
                    budget.c.day == row["day"],
                )
                .values(
                    reserved_microusd=budget.c.reserved_microusd
                    - (0 if unknown else row["reserved_microusd"]),
                    spent_microusd=budget.c.spent_microusd + charge,
                    blocked=budget.c.blocked | blocked,
                )
            )
            connection.execute(
                update(usage)
                .where(usage.c.id == usage_id)
                .values(
                    state="uncertain" if unknown else "completed",
                    spent_microusd=None if unknown else charge,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            )
            connection.execute(
                update(control)
                .where(
                    control.c.provider == row["provider"],
                    control.c.pending_usage_id == usage_id,
                )
                .values(blocked=blocked, pending_usage_id=usage_id if unknown else None)
            )
