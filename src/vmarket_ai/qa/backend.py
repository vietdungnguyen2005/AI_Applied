from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from vmarket_ai.contracts import QueryEmbeddingProvider
from vmarket_ai.ingestion.models import ChunkRecord, DocumentRecord, Grant, Snapshot, SourceVersion
from vmarket_ai.ingestion.service import audit, stable
from vmarket_ai.ingestion.spec import E5_PROFILE, FAKE_PROFILE, Actor, Citation
from vmarket_ai.providers.fake import FakeEmbeddingProvider
from vmarket_ai.providers.local_e5 import LocalE5EmbeddingProvider
from vmarket_ai.retrieval.service import Retriever
from vmarket_ai.retrieval.spec import RetrievalConfig, SearchRequest, SearchResult
from vmarket_ai.settings import Settings

DEMO_ACTOR = Actor(id=stable("demo-reader"))
DEMO_COLLECTIONS = (
    UUID("ed76d914-7c66-5102-9178-676334063938"),
    UUID("4aa83e9f-0a0a-5558-8f5e-0f87db27c923"),
)


class PostgresEvidence:
    def __init__(self, engine: Engine, settings: Settings) -> None:
        self.engine = engine
        provider: QueryEmbeddingProvider
        if settings.qa_embedding_mode == "local":
            assert settings.qa_model_bundle is not None
            provider = LocalE5EmbeddingProvider(settings.qa_model_bundle)
            profile = E5_PROFILE
        else:
            provider = FakeEmbeddingProvider()
            profile = FAKE_PROFILE
        self.retriever = Retriever(engine, RetrievalConfig(embedding=profile), provider)

    async def retrieve(self, actor: Actor, request: SearchRequest) -> SearchResult:
        return await self.retriever.search(actor, request, "dense")

    def current(self, actor: Actor, scopes: tuple[UUID, ...], chunk_id: UUID) -> Citation | None:
        # Re-check current grants AND active/effective provenance after the model round trip.
        now = datetime.now(UTC).date().isoformat()
        until = SourceVersion.metadata_json["effective_until"].as_string()
        query = (
            select(
                ChunkRecord,
                SourceVersion.id.label("version_id"),
                SourceVersion.document_id,
                SourceVersion.source_version,
                SourceVersion.raw_sha256,
            )
            .join(Snapshot, ChunkRecord.snapshot_id == Snapshot.id)
            .join(SourceVersion, Snapshot.version_id == SourceVersion.id)
            .join(DocumentRecord, SourceVersion.document_id == DocumentRecord.id)
            .join(Grant, Grant.collection_id == DocumentRecord.collection_id)
            .where(
                ChunkRecord.id == chunk_id,
                Grant.actor_id == actor.id,
                Grant.role.in_(("reader", "writer")),
                DocumentRecord.collection_id.in_(scopes),
                DocumentRecord.active_snapshot_id == Snapshot.id,
                DocumentRecord.deleted.is_(False),
                Snapshot.eligible.is_(True),
                SourceVersion.metadata_json["effective_from"].as_string() <= now,
                or_(until.is_(None), until >= now),
            )
        )
        with Session(self.engine) as session, session.begin():
            row = session.execute(query).one_or_none()
            if row is None:
                return None
            c = row.ChunkRecord
            audit(session, actor, "qa_citation_read", chunk_id, 1)
            return Citation(
                document_id=row.document_id,
                version_id=row.version_id,
                source_version=row.source_version,
                raw_sha256=row.raw_sha256,
                snapshot_id=c.snapshot_id,
                chunk_id=c.id,
                locator=c.locator,
                start=c.start_offset,
                end=c.end_offset,
                text=c.text,
            )
