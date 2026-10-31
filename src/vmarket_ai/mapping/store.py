from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import JSON, DateTime, LargeBinary, String, Uuid, insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, mapped_column

from vmarket_ai.database import Base
from vmarket_ai.mapping.spec import MappingResponse


class DraftRecord(Base):
    __tablename__ = "mapping_drafts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    raw_sha256: Mapped[str] = mapped_column(String(64))
    raw_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    response_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DraftStore(Protocol):
    def save(self, raw: bytes, response: MappingResponse) -> None: ...


class SQLDraftStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def save(self, raw: bytes, response: MappingResponse) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                insert(DraftRecord).values(
                    id=response.request_id,
                    raw_sha256=response.raw_sha256,
                    raw_bytes=raw,
                    response_json=response.model_dump(mode="json"),
                    created_at=datetime.now(UTC),
                )
            )
