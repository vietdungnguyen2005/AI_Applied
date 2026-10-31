import hashlib
import logging
import math
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import delete, insert, or_, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from vmarket_ai.contracts import EmbeddingProvider, EmbeddingRequest
from vmarket_ai.ingestion.models import (
    ChunkRecord,
    ChunkVector,
    DocumentAudit,
    DocumentRecord,
    Grant,
    Snapshot,
    SourceVersion,
)
from vmarket_ai.ingestion.parsing import chunk, extract
from vmarket_ai.ingestion.spec import (
    Actor,
    ChunkConfig,
    Citation,
    EmbedProfile,
    IngestionError,
    Metadata,
    Receipt,
    fingerprint,
    pipeline_manifest,
)


def stable(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, "vmarket-ingest-v1:" + value)


def require_write(session: Session, actor: Actor, collection_id: UUID) -> None:
    if (
        session.scalar(
            select(Grant.actor_id).where(
                Grant.actor_id == actor.id,
                Grant.collection_id == collection_id,
                Grant.role == "writer",
            )
        )
        is None
    ):
        raise IngestionError("denied")


def audit(session: Session, actor: Actor, event: str, entity: UUID | None, count: int) -> None:
    session.execute(
        insert(DocumentAudit).values(
            id=uuid4(),
            actor_id=actor.id,
            event=event,
            entity_id=entity,
            count=count,
            observed_at=datetime.now(UTC),
        )
    )


class Ingestor:
    def __init__(
        self,
        engine: Engine,
        provider: EmbeddingProvider,
        profile: EmbedProfile,
        config: ChunkConfig | None = None,
    ) -> None:
        self.engine, self.provider, self.profile = engine, provider, profile
        self.config = config or ChunkConfig()

    async def ingest(
        self,
        actor: Actor,
        collection_id: UUID,
        document_id: UUID,
        metadata: Metadata,
        raw: bytes,
        media_type: str,
        *,
        expected_revision: int,
        parse_timeout: float = 10,
    ) -> Receipt:
        try:
            return await self._ingest(
                actor,
                collection_id,
                document_id,
                metadata,
                raw,
                media_type,
                expected_revision=expected_revision,
                parse_timeout=parse_timeout,
            )
        except (IngestionError, SQLAlchemyError) as error:
            try:
                with Session(self.engine) as session, session.begin():
                    audit(session, actor, "ingest_rejected", document_id, 0)
            except SQLAlchemyError:
                logging.getLogger(__name__).warning('{"event":"ingest_audit_unavailable"}')
            if isinstance(error, IngestionError):
                raise
            raise IngestionError("storage_failed") from None

    async def _ingest(
        self,
        actor: Actor,
        collection_id: UUID,
        document_id: UUID,
        metadata: Metadata,
        raw: bytes,
        media_type: str,
        *,
        expected_revision: int,
        parse_timeout: float = 10,
    ) -> Receipt:
        pipeline = fingerprint(self.profile, self.config)
        version_id = stable(f"{document_id}:{metadata.source_version}")
        snapshot_id = stable(f"{version_id}:{pipeline}")
        raw_hash = hashlib.sha256(raw).hexdigest()
        if expected_revision < 0:
            raise IngestionError("revision_conflict")
        with Session(self.engine) as session, session.begin():
            require_write(session, actor, collection_id)
            current = session.get(DocumentRecord, document_id)
            if current and (current.collection_id != collection_id or current.deleted):
                raise IngestionError("document_identity_conflict")
            previous = session.get(SourceVersion, version_id) if current else None
            if previous and (
                previous.raw_sha256 != raw_hash
                or previous.media_type != media_type
                or previous.metadata_json != metadata.model_dump(mode="json")
            ):
                raise IngestionError("immutable_version_conflict")
            if current and current.active_snapshot_id == snapshot_id:
                count = len(
                    session.scalars(
                        select(ChunkRecord.id).where(ChunkRecord.snapshot_id == snapshot_id)
                    ).all()
                )
                audit(session, actor, "ingest_unchanged", document_id, count)
                return Receipt(
                    document_id=document_id,
                    version_id=version_id,
                    snapshot_id=snapshot_id,
                    revision=current.revision,
                    chunks=count,
                    unchanged=True,
                )
            if (current.revision if current else 0) != expected_revision:
                raise IngestionError("revision_conflict")
        # Expensive work is outside the write transaction. Any failure leaves publication untouched.
        extraction = extract(raw, media_type, timeout=parse_timeout)
        parts = chunk(extraction, self.config)
        vectors: list[tuple[float, ...]] = []
        try:
            for offset in range(0, len(parts), 8):
                batch = parts[offset : offset + 8]
                result = await self.provider.embed(
                    EmbeddingRequest(texts=tuple(p.text for p in batch))
                )
                if (
                    result.model != self.profile.model
                    or result.dimensions != self.profile.dimensions
                    or result.provider_mode != self.profile.mode
                    or len(result.vectors) != len(batch)
                ):
                    raise IngestionError("embedding_profile_mismatch")
                for vector in result.vectors:
                    if (
                        len(vector) != self.profile.dimensions
                        or not all(math.isfinite(v) for v in vector)
                        or not 0.99 <= math.sqrt(sum(v * v for v in vector)) <= 1.01
                    ):
                        raise IngestionError("invalid_embedding")
                    vectors.append(vector)
        except IngestionError:
            raise
        except Exception:
            raise IngestionError("embedding_failed") from None
        try:
            with Session(self.engine) as session, session.begin():
                require_write(
                    session, actor, collection_id
                )  # ACL may have changed during embedding.
                if expected_revision == 0:
                    session.execute(
                        insert(DocumentRecord).values(
                            id=document_id,
                            collection_id=collection_id,
                            revision=1,
                            deleted=False,
                            active_snapshot_id=None,
                        )
                    )
                else:
                    changed = session.connection().execute(
                        update(DocumentRecord)
                        .where(
                            DocumentRecord.id == document_id,
                            DocumentRecord.collection_id == collection_id,
                            DocumentRecord.revision == expected_revision,
                            DocumentRecord.deleted.is_(False),
                        )
                        .values(revision=expected_revision + 1, active_snapshot_id=None)
                    )
                    if changed.rowcount != 1:
                        raise IngestionError("revision_conflict")
                existing_version = session.get(SourceVersion, version_id)
                if existing_version is None:
                    session.execute(
                        insert(SourceVersion).values(
                            id=version_id,
                            document_id=document_id,
                            source_version=metadata.source_version,
                            raw_sha256=raw_hash,
                            raw_bytes=raw,
                            media_type=media_type,
                            metadata_json=metadata.model_dump(mode="json"),
                        )
                    )
                elif (
                    existing_version.raw_sha256 != raw_hash
                    or existing_version.media_type != media_type
                    or existing_version.metadata_json != metadata.model_dump(mode="json")
                ):
                    raise IngestionError("immutable_version_conflict")
                if session.get(Snapshot, snapshot_id) is None:
                    session.execute(
                        insert(Snapshot).values(
                            id=snapshot_id,
                            version_id=version_id,
                            pipeline_sha256=pipeline,
                            profile_json=pipeline_manifest(self.profile, self.config),
                            dimensions=self.profile.dimensions,
                            extraction_json=extraction.model_dump(mode="json"),
                            eligible=(
                                metadata.status == "current"
                                and metadata.trust_level == "curated_synthetic"
                            ),
                        )
                    )
                    for part, vector in zip(parts, vectors, strict=True):
                        chunk_id = stable(f"{snapshot_id}:{part.ordinal}:{part.text_sha256}")
                        session.execute(
                            insert(ChunkRecord).values(
                                id=chunk_id,
                                snapshot_id=snapshot_id,
                                ordinal=part.ordinal,
                                locator=part.locator,
                                start_offset=part.start,
                                end_offset=part.end,
                                text=part.text,
                                text_sha256=part.text_sha256,
                            )
                        )
                        session.execute(
                            insert(ChunkVector).values(
                                chunk_id=chunk_id,
                                vector_fake=list(vector) if self.profile.mode == "fake" else None,
                                vector_e5=list(vector) if self.profile.mode == "local" else None,
                            )
                        )
                session.execute(
                    update(DocumentRecord)
                    .where(DocumentRecord.id == document_id)
                    .values(active_snapshot_id=snapshot_id)
                )
                audit(session, actor, "ingest_published", document_id, len(parts))
        except IntegrityError:
            raise IngestionError("revision_conflict") from None
        return Receipt(
            document_id=document_id,
            version_id=version_id,
            snapshot_id=snapshot_id,
            revision=expected_revision + 1,
            chunks=len(parts),
            unchanged=False,
        )

    def delete(
        self, actor: Actor, collection_id: UUID, document_id: UUID, *, expected_revision: int
    ) -> None:
        with Session(self.engine) as session, session.begin():
            require_write(session, actor, collection_id)
            changed = session.connection().execute(
                update(DocumentRecord)
                .where(
                    DocumentRecord.id == document_id,
                    DocumentRecord.collection_id == collection_id,
                    DocumentRecord.revision == expected_revision,
                    DocumentRecord.deleted.is_(False),
                )
                .values(deleted=True, active_snapshot_id=None, revision=expected_revision + 1)
            )
            if changed.rowcount != 1:
                raise IngestionError("revision_conflict")
            # Transactionally remove originals, archived/active chunks, snapshots and vectors.
            session.execute(delete(SourceVersion).where(SourceVersion.document_id == document_id))
            audit(session, actor, "document_deleted", document_id, 0)


class DocumentReader:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def read(
        self,
        actor: Actor,
        collection_ids: tuple[UUID, ...],
        *,
        as_of: date,
        chunk_id: UUID | None = None,
        limit: int = 100,
    ) -> tuple[Citation, ...]:
        if not collection_ids or len(collection_ids) > 10 or not 1 <= limit <= 100:
            raise IngestionError("invalid_scope_or_limit")
        # ACL in SQL before candidate materialization / LIMIT. No unauthorized text reaches Python.
        query = (
            select(
                ChunkRecord,
                SourceVersion.source_version,
                SourceVersion.raw_sha256,
                SourceVersion.id.label("version_id"),
                DocumentRecord.id.label("document_id"),
            )
            .join(Snapshot, ChunkRecord.snapshot_id == Snapshot.id)
            .join(SourceVersion, Snapshot.version_id == SourceVersion.id)
            .join(DocumentRecord, SourceVersion.document_id == DocumentRecord.id)
            .join(Grant, Grant.collection_id == DocumentRecord.collection_id)
            .where(
                Grant.actor_id == actor.id,
                Grant.role.in_(("reader", "writer")),
                DocumentRecord.collection_id.in_(collection_ids),
                DocumentRecord.deleted.is_(False),
            )
        )
        if chunk_id:
            query = query.where(ChunkRecord.id == chunk_id)  # Authorized archived citation allowed.
        else:
            effective_until = SourceVersion.metadata_json["effective_until"].as_string()
            query = query.where(
                DocumentRecord.active_snapshot_id == Snapshot.id,
                Snapshot.eligible.is_(True),
                SourceVersion.metadata_json["effective_from"].as_string() <= as_of.isoformat(),
                or_(effective_until.is_(None), effective_until >= as_of.isoformat()),
            )
        query = query.order_by(DocumentRecord.id, ChunkRecord.ordinal).limit(limit)
        with Session(self.engine) as session, session.begin():
            rows = session.execute(query).all()
            results = tuple(
                Citation(
                    document_id=r.document_id,
                    version_id=r.version_id,
                    snapshot_id=r.ChunkRecord.snapshot_id,
                    chunk_id=r.ChunkRecord.id,
                    source_version=r.source_version,
                    raw_sha256=r.raw_sha256,
                    locator=r.ChunkRecord.locator,
                    start=r.ChunkRecord.start_offset,
                    end=r.ChunkRecord.end_offset,
                    text=r.ChunkRecord.text,
                )
                for r in rows
            )
            audit(
                session,
                actor,
                "citation_read" if chunk_id else "candidates_read",
                chunk_id,
                len(results),
            )
            return results

    def original(self, actor: Actor, collection_ids: tuple[UUID, ...], version_id: UUID) -> bytes:
        if not collection_ids or len(collection_ids) > 10:
            raise IngestionError("invalid_scope_or_limit")
        query = (
            select(SourceVersion.raw_bytes)
            .join(DocumentRecord, SourceVersion.document_id == DocumentRecord.id)
            .join(Grant, Grant.collection_id == DocumentRecord.collection_id)
            .where(
                Grant.actor_id == actor.id,
                Grant.role.in_(("reader", "writer")),
                DocumentRecord.collection_id.in_(collection_ids),
                DocumentRecord.deleted.is_(False),
                SourceVersion.id == version_id,
            )
        )
        with Session(self.engine) as session, session.begin():
            value = session.scalar(query)
            if value is None:
                raise IngestionError("not_found_or_denied")
            audit(session, actor, "original_read", version_id, 1)
            return value
