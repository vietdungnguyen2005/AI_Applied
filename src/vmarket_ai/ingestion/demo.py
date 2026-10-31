"""Local synthetic corpus demonstration; no HTTP authentication or quality evaluation."""

import argparse
import asyncio
import json
from datetime import date
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from pydantic import SecretStr
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from vmarket_ai.database import Collection, create_db_engine
from vmarket_ai.datasets.audit import CorpusRecord, records
from vmarket_ai.datasets.release import owned_path, verify_release
from vmarket_ai.ingestion.models import ChunkRecord, ChunkVector, Grant, SourceVersion
from vmarket_ai.ingestion.service import DocumentReader, Ingestor, stable
from vmarket_ai.ingestion.spec import E5_PROFILE, FAKE_PROFILE, Actor, IngestionError, Metadata
from vmarket_ai.providers.fake import FakeEmbeddingProvider
from vmarket_ai.providers.local_e5 import LocalE5EmbeddingProvider
from vmarket_ai.settings import Settings, load_settings


async def run(output: Path, bundle: Path | None, postgres: bool) -> None:
    root = Path("data/v1")
    verify_release(root, Path("data/releases/v1.lock.json"))
    corpus = records(root / "corpus.jsonl", CorpusRecord)
    settings = (
        load_settings()
        if postgres
        else Settings(  # type: ignore[call-arg]
            _env_file=None,
            database_url=SecretStr("sqlite+pysqlite:///.local/p05-ingestion-demo.db"),
        )
    )
    if postgres and (
        not settings.migration_database_url
        or not settings.database_url.get_secret_value().startswith("postgresql+psycopg:")
    ):
        raise IngestionError("demo_requires_ai_postgres_and_curator_credentials")
    config = Config("alembic.ini")
    config.attributes["settings"] = settings
    command.upgrade(config, "head")
    engine = create_db_engine(settings)
    curator_engine = create_db_engine(settings, migration=True)
    curator = Actor(id=stable("demo-curator"))
    reader = Actor(id=stable("demo-reader"))
    public_ids = tuple(d.collection_id for d in corpus if d.id in {"a-current", "b-current"})
    for collection_id in sorted({d.collection_id for d in corpus}):
        with Session(curator_engine) as session, session.begin():
            if session.get(Collection, collection_id) is None:
                session.execute(insert(Collection).values(id=collection_id, label="P04 synthetic"))
            for actor in (curator, reader):
                if actor == reader and collection_id not in public_ids:
                    continue
                if session.get(Grant, (collection_id, actor.id)) is None:
                    session.execute(
                        insert(Grant).values(
                            collection_id=collection_id,
                            actor_id=actor.id,
                            role="writer" if actor == curator else "reader",
                        )
                    )
    profile = E5_PROFILE if bundle else FAKE_PROFILE
    provider = LocalE5EmbeddingProvider(bundle) if bundle else FakeEmbeddingProvider()
    service = Ingestor(engine, provider, profile)
    inventory: list[dict[str, object]] = []
    # Manifest declares current/retired status; source-version strings imply no precedence.
    for document in sorted(corpus, key=lambda d: d.status == "current"):
        meta = Metadata.model_validate(
            document.model_dump(mode="json", include=set(Metadata.model_fields))
        )
        # New demo DB per mode recommended; this accepts idempotent repeated executions.
        from vmarket_ai.ingestion.models import DocumentRecord

        with Session(engine) as session:
            current = session.get(DocumentRecord, document.document_id)
            revision = current.revision if current else 0
            retained = session.get(
                SourceVersion, stable(f"{document.document_id}:{document.source_version}")
            )
            if document.status == "retired" and retained:
                inventory.append({"fixture": document.id, "status": "retained_archive"})
                continue
        try:
            receipt = await service.ingest(
                curator,
                document.collection_id,
                document.document_id,
                meta,
                owned_path(root, document.path).read_bytes(),
                document.media_type,
                expected_revision=revision,
            )
            inventory.append(
                {
                    "fixture": document.id,
                    "status": "ingested",
                    "receipt": receipt.model_dump(mode="json"),
                }
            )
        except IngestionError as error:
            inventory.append({"fixture": document.id, "status": "rejected", "code": str(error)})
    access = DocumentReader(engine)
    candidates = access.read(reader, public_ids, as_of=date(2026, 10, 31))
    sample = next(c for c in candidates if c.locator == "section:encoding")
    assert access.read(Actor(id=UUID(int=0)), public_ids, as_of=date(2026, 10, 31)) == ()
    assert access.original(reader, public_ids, sample.version_id)
    assert access.read(reader, public_ids, as_of=date(2026, 10, 31), chunk_id=sample.chunk_id) == (
        sample,
    )
    with Session(engine) as session:
        counts = {
            "versions": session.scalar(select(func.count()).select_from(SourceVersion)),
            "chunks": session.scalar(select(func.count()).select_from(ChunkRecord)),
            "embeddings": session.scalar(select(func.count()).select_from(ChunkVector)),
        }
    report = {
        "status": "ingestion_demo_only",
        "storage": engine.dialect.name,
        "profile": profile.model_dump(),
        "inventory": inventory,
        "counts": counts,
        "authorized_current_chunks": len(candidates),
        "sample_citation": sample.model_dump(mode="json"),
        "source_version_crosswalk": [
            {
                "document_id": str(d.document_id),
                "source_version": d.source_version,
                "fixture_version_id": str(d.version_id),
                "stored_version_id": str(stable(f"{d.document_id}:{d.source_version}")),
            }
            for d in corpus
            if d.quality["status"] == "verified_text"
        ],
        "unauthorized_actor_results": 0,
        "external_inference_requests": 0,
        "model_quality_metrics": "NOT_RUN",
        "independent_gold_review": "pending",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "status",
                    "storage",
                    "profile",
                    "counts",
                    "authorized_current_chunks",
                    "model_quality_metrics",
                )
            }
        )
    )
    curator_engine.dispose()
    engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest frozen P04 synthetic documents locally")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--model-bundle", type=Path)
    parser.add_argument("--postgres", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.report, args.model_bundle, args.postgres))
