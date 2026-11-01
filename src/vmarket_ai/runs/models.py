from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from vmarket_ai.database import Base


class RunRecord(Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started','waiting_for_operator','completed','failed',"
            "'cancelled','expired')"
        ),
        CheckConstraint("phase IN ('idle','planning','ready','executing','terminal')"),
        CheckConstraint("step BETWEEN 0 AND 3 AND revision >= 0 AND slot BETWEEN 0 AND 7"),
        Index(
            "agent_run_active_slot",
            "actor_ref",
            "slot",
            unique=True,
            postgresql_where=text("status IN ('started','waiting_for_operator')"),
            sqlite_where=text("status IN ('started','waiting_for_operator')"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    actor_ref: Mapped[str] = mapped_column(String(64))
    conversation_id: Mapped[UUID] = mapped_column(Uuid)
    initial_request_id: Mapped[UUID] = mapped_column(Uuid)
    slot: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    phase: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column(Integer)
    step: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(String(2000))
    collection_ids: Mapped[list[str]] = mapped_column(JSON)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    summaries: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    pending: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lease_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_until: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[int] = mapped_column(BigInteger)
    purge_after: Mapped[int] = mapped_column(BigInteger)


class RunEvent(Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (Index("agent_run_event_revision", "run_id", "revision", unique=True),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("ai.agent_runs.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    phase: Mapped[str] = mapped_column(String(16))
    step: Mapped[int] = mapped_column(Integer)
    at: Mapped[int] = mapped_column(BigInteger)
