from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from vmarket_ai.database import Base


class Grant(Base):
    __tablename__ = "collection_grants"
    __table_args__ = (CheckConstraint("role IN ('reader','writer')"),)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai.collections.id", ondelete="CASCADE"), primary_key=True
    )
    actor_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    role: Mapped[str] = mapped_column(String(8))


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint("revision >= 1"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("ai.collections.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    # Atomic publication pointer; validated under document CAS by the service.
    active_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class SourceVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "source_version"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("ai.documents.id", ondelete="CASCADE"))
    source_version: Mapped[str] = mapped_column(String(80))
    raw_sha256: Mapped[str] = mapped_column(String(64))
    raw_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    media_type: Mapped[str] = mapped_column(String(100))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON)


class Snapshot(Base):
    __tablename__ = "document_snapshots"
    __table_args__ = (
        UniqueConstraint("version_id", "pipeline_sha256"),
        CheckConstraint("dimensions IN (32,384)"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai.document_versions.id", ondelete="CASCADE")
    )
    pipeline_sha256: Mapped[str] = mapped_column(String(64))
    profile_json: Mapped[dict[str, object]] = mapped_column(JSON)
    dimensions: Mapped[int] = mapped_column(Integer)
    extraction_json: Mapped[dict[str, object]] = mapped_column(JSON)
    # Only effective curated current sources can be current retrieval candidates.
    eligible: Mapped[bool] = mapped_column(Boolean)


class ChunkRecord(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "ordinal"),
        CheckConstraint("start_offset >= 0 AND end_offset > start_offset"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai.document_snapshots.id", ondelete="CASCADE"), index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer)
    locator: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_sha256: Mapped[str] = mapped_column(String(64))


class ChunkVector(Base):
    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        CheckConstraint(
            "(vector_fake IS NOT NULL AND vector_e5 IS NULL) OR "
            "(vector_fake IS NULL AND vector_e5 IS NOT NULL)"
        ),
    )
    chunk_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai.document_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    vector_fake: Mapped[list[float] | None] = mapped_column(
        Vector(32).with_variant(JSON(none_as_null=True), "sqlite"), nullable=True
    )
    vector_e5: Mapped[list[float] | None] = mapped_column(
        Vector(384).with_variant(JSON(none_as_null=True), "sqlite"), nullable=True
    )


class DocumentAudit(Base):
    __tablename__ = "document_audit"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(Uuid)
    event: Mapped[str] = mapped_column(String(24))
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    count: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
