"""Opt-in real ACL/current-source enforcement behind signed P12 HTTP reads."""

import base64
import os
from datetime import date
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, insert, update
from sqlalchemy.orm import Session
from test_ingestion import metadata
from test_qa import Scripted, proposal
from test_signed_qa import post

from vmarket_ai.app import create_app
from vmarket_ai.database import Collection, create_db_engine
from vmarket_ai.ingestion.models import DocumentRecord, Grant
from vmarket_ai.ingestion.service import DocumentReader, Ingestor
from vmarket_ai.ingestion.spec import FAKE_PROFILE, Actor
from vmarket_ai.providers.fake import FakeEmbeddingProvider
from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS, PostgresEvidence
from vmarket_ai.qa.service import AnswerService
from vmarket_ai.settings import Settings

PG = os.environ.get("AI_TEST_DATABASE_URL")
OWNER = os.environ.get("AI_TEST_OWNER_DATABASE_URL")


@pytest.mark.postgres
@pytest.mark.skipif(not PG or not OWNER, reason="Disposable AI app/owner PostgreSQL absent")
async def test_signed_pg_source_rejects_wrong_scope_and_deleted_source():
    owner = create_db_engine(Settings(_env_file=None, database_url=SecretStr(OWNER)))
    key = Ed25519PrivateKey.generate()
    config = Settings(
        _env_file=None,
        mode="integrated",
        agent_enabled=True,
        qa_enabled=True,
        database_url=SecretStr(PG),
        gateway_public_keys={
            "test": base64.b64encode(key.public_key().public_bytes_raw()).decode()
        },
    )
    engine = create_db_engine(config)
    collection = DEMO_COLLECTIONS[0]
    curator, document_id = Actor(id=uuid4()), uuid4()
    with Session(owner) as session, session.begin():
        existed = session.get(Collection, collection) is not None
        reader_existed = session.get(Grant, (collection, DEMO_ACTOR.id)) is not None
        if not existed:
            session.execute(insert(Collection).values(id=collection, label="P12 signed source"))
        session.execute(
            insert(Grant).values(collection_id=collection, actor_id=curator.id, role="writer")
        )
        if not reader_existed:
            session.execute(
                insert(Grant).values(
                    collection_id=collection, actor_id=DEMO_ACTOR.id, role="reader"
                )
            )
    try:
        await Ingestor(engine, FakeEmbeddingProvider(), FAKE_PROFILE).ingest(
            curator,
            collection,
            document_id,
            metadata(),
            b"Original bytes use UTF-8.",
            "text/plain",
            expected_revision=0,
        )
        known = next(
            c
            for c in DocumentReader(engine).read(curator, (collection,), as_of=date(2026, 11, 1))
            if c.document_id == document_id
        )
        qa = AnswerService(PostgresEvidence(engine, config), Scripted(proposal(known)), mode="fake")
        with TestClient(
            create_app(config, engine, qa_service=qa), base_url="http://127.0.0.1:8090"
        ) as client:
            scope = [str(collection)]
            body = {"chunk_id": str(known.chunk_id), "collection_ids": scope}
            assert (
                post(
                    client, key, "/ai/citations/read", "documents_read", body, collection_ids=scope
                ).status_code
                == 200
            )
            other = [str(DEMO_COLLECTIONS[1])]
            wrong_scope = post(
                client,
                key,
                "/ai/citations/read",
                "documents_read",
                {**body, "collection_ids": other},
                collection_ids=other,
            )
            assert wrong_scope.status_code == 404
            with owner.begin() as connection:
                connection.execute(
                    update(DocumentRecord)
                    .where(DocumentRecord.id == document_id)
                    .values(deleted=True)
                )
            deleted = post(
                client, key, "/ai/citations/read", "documents_read", body, collection_ids=scope
            )
            assert deleted.status_code == 404
            assert deleted.json()["code"] == wrong_scope.json()["code"] == "DOCUMENT_NOT_AVAILABLE"
    finally:
        with owner.begin() as connection:
            connection.execute(delete(DocumentRecord).where(DocumentRecord.id == document_id))
            connection.execute(
                delete(Grant).where(Grant.actor_id == curator.id, Grant.collection_id == collection)
            )
            if not reader_existed:
                connection.execute(
                    delete(Grant).where(
                        Grant.actor_id == DEMO_ACTOR.id, Grant.collection_id == collection
                    )
                )
            if not existed:
                connection.execute(delete(Collection).where(Collection.id == collection))
        owner.dispose()
        engine.dispose()
