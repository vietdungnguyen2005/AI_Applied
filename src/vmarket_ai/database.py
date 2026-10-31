from datetime import date
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Uuid,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

from vmarket_ai.settings import Settings

REVISION = "0002_document_ingestion"


class Base(DeclarativeBase):
    metadata = MetaData(schema="ai")


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (CheckConstraint("synthetic = true"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    label: Mapped[str] = mapped_column(String(120))
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))


class BudgetDay(Base):
    __tablename__ = "provider_budget_days"
    __table_args__ = (
        CheckConstraint("requests_used >= 0"),
        CheckConstraint("reserved_microusd >= 0"),
        CheckConstraint("spent_microusd >= 0"),
    )
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    requests_used: Mapped[int] = mapped_column(Integer, default=0)
    reserved_microusd: Mapped[int] = mapped_column(BigInteger, default=0)
    spent_microusd: Mapped[int] = mapped_column(BigInteger, default=0)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class ProviderControl(Base):
    __tablename__ = "provider_controls"
    provider: Mapped[str] = mapped_column(String(32), primary_key=True)
    pending_usage_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class ProviderUsage(Base):
    __tablename__ = "provider_usage"
    __table_args__ = (
        ForeignKeyConstraint(
            ["provider", "day"], ["ai.provider_budget_days.provider", "ai.provider_budget_days.day"]
        ),
        CheckConstraint("state IN ('reserved','completed','uncertain')"),
        CheckConstraint("reserved_microusd >= 0"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    provider: Mapped[str] = mapped_column(String(32))
    day: Mapped[date] = mapped_column(Date)
    state: Mapped[str] = mapped_column(String(16))
    reserved_microusd: Mapped[int] = mapped_column(BigInteger)
    spent_microusd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)


def create_db_engine(settings: Settings, *, migration: bool = False) -> Engine:
    secret = settings.migration_database_url if migration else None
    url = make_url((secret or settings.database_url).get_secret_value())
    if url.drivername == "sqlite+pysqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).resolve().parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"poolclass": StaticPool} if url.database in {None, ":memory:"} else {}
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False, "timeout": 2},
            hide_parameters=True,
            **kwargs,
        )

        @event.listens_for(engine, "connect")
        def foreign_keys(connection: SQLiteConnection, _: ConnectionPoolEntry) -> None:
            cursor = connection.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine.execution_options(schema_translate_map={"ai": None})
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=0,
        pool_timeout=2,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 2,
            "options": "-c statement_timeout=1000 -c lock_timeout=500",
        },
    )


def database_ready(engine: Engine) -> bool:
    table = "ai.alembic_version" if engine.dialect.name == "postgresql" else "alembic_version"
    with engine.connect() as connection:
        version = connection.execute(text(f"SELECT version_num FROM {table}")).scalar_one_or_none()
        return version == REVISION
