import math
import os
from datetime import date
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, event, select, text
from sqlalchemy.orm import Session
from test_ingestion import metadata, provision

from vmarket_ai.contracts import EmbeddingRequest, EmbeddingResult
from vmarket_ai.database import Collection, create_db_engine
from vmarket_ai.ingestion.models import DocumentAudit, DocumentRecord, Grant
from vmarket_ai.ingestion.service import DocumentReader, Ingestor
from vmarket_ai.ingestion.spec import FAKE_PROFILE, Actor, ChunkConfig, Citation
from vmarket_ai.providers.fake import FakeEmbeddingProvider
from vmarket_ai.retrieval.evaluate import summarize, write_new
from vmarket_ai.retrieval.metrics import latency, ranked_metrics
from vmarket_ai.retrieval.service import Retriever, authorized_sql, fuse, lexical_query, query_text
from vmarket_ai.retrieval.spec import Hit, RetrievalConfig, RetrievalError, SearchRequest
from vmarket_ai.settings import Settings

POSTGRES_URL = os.environ.get("AI_TEST_DATABASE_URL")
OWNER_URL = os.environ.get("AI_TEST_OWNER_DATABASE_URL")
TODAY = date(2026, 10, 31)


def hit(key, score=0.1):
    return Hit(
        citation=Citation(
            document_id=uuid4(),
            version_id=uuid4(),
            snapshot_id=uuid4(),
            chunk_id=key,
            source_version="1",
            raw_sha256="a" * 64,
            locator="section:policy",
            start=0,
            end=1,
            text="Synthetic",
        ),
        score=score,
    )


def test_rrf_fuses_rank_positions_not_incompatible_raw_scores():
    a, b, c = uuid4(), uuid4(), uuid4()
    lexical = (hit(a, 9999), hit(b, 1))
    dense = (hit(b, 0.99), hit(c, 0.9))
    config = RetrievalConfig(top_k=3)
    result = fuse(lexical, dense, config)
    assert result[0].citation.chunk_id == b
    assert result[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert result[0].lexical_rank == 2 and result[0].dense_rank == 1
    assert next(h for h in result if h.citation.chunk_id == a).score == pytest.approx(1 / 61)
    assert fuse((), (), config) == ()
    assert fuse(lexical, (), config)[0].citation.chunk_id == a


def test_rrf_ties_are_deterministic_and_weights_configurable():
    a, b = sorted((uuid4(), uuid4()))
    result = fuse((hit(a),), (hit(b),), RetrievalConfig())
    assert [h.citation.chunk_id for h in result] == [a, b]
    weighted = fuse((hit(a),), (hit(b),), RetrievalConfig(dense_weight=2))
    assert weighted[0].citation.chunk_id == b


def test_metrics_with_hand_calculated_graded_rankings():
    measured = ranked_metrics(["low", "high", "irrelevant"], {"high": 2, "low": 1}, 3)
    expected = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
    assert measured == pytest.approx({"hit": 1, "recall": 1, "mrr": 1, "ndcg": expected})
    assert ranked_metrics(["none", "high"], {"high": 2}, 1) == {
        "hit": 0,
        "recall": 0,
        "mrr": 0,
        "ndcg": 0,
    }
    assert ranked_metrics(["none", "high"], {"high": 2}, 3)["mrr"] == 0.5
    assert all(v is None for v in ranked_metrics(["anything"], {}, 5).values())
    with pytest.raises(ValueError):
        ranked_metrics(["duplicate", "duplicate"], {"duplicate": 2}, 5)
    assert latency([0, 10, 20]) == {"median_ms": 10, "p95_ms": 19}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"top_k": 0},
        {"top_k": 6},
        {"candidate_pool": 101},
        {"lexical_config": "unsafe'"},
        {"rrf_constant": 0},
        {"lexical_weight": float("nan")},
        {"reranker": "pretend-model"},
        {"query_normalization": "unknown"},
    ],
)
def test_retrieval_config_rejects_invalid_or_unimplemented_options(kwargs):
    with pytest.raises(ValidationError):
        RetrievalConfig(**kwargs)


def test_query_words_are_quoted_and_unicode_normalization_is_explicit():
    assert lexical_query("HTTP 202", "any") == '"HTTP" OR "202"'
    assert lexical_query("HTTP 202", "all") == '"HTTP" "202"'
    assert lexical_query("'; DROP TABLE ai.documents; --", "any") == (
        '"DROP" OR "TABLE" OR "ai" OR "documents"'
    )
    assert query_text(" e\u0301 ", "nfc") == "é"
    assert query_text(" e\u0301 ", "verbatim") == " e\u0301 "
    with pytest.raises(ValidationError):
        SearchRequest(query="  ", collection_ids=(uuid4(),), as_of=TODAY)


def test_sql_materializes_acl_and_profile_before_scoring_or_limit():
    request = SearchRequest(
        query="query", collection_ids=(uuid4(),), as_of=TODAY, languages=("ja",), vendors=("NAMI",)
    )
    sql = authorized_sql(RetrievalConfig(), request)
    assert "authorized AS MATERIALIZED" in sql
    assert "collection_grants" in sql and "g.actor_id=:actor" in sql
    assert "d.active_snapshot_id=s.id" in sql and "s.pipeline_sha256=:pipeline" in sql
    assert "language' IN (:lang0)" in sql and "vendor' IN (:vendor0)" in sql
    assert "LIMIT" not in sql and "query" not in sql
    assert "vector_e5 IS NOT NULL" in sql


async def test_sqlite_is_not_misrepresented_as_pgvector_or_fts(migrated):
    engine = create_db_engine(migrated)
    with pytest.raises(RetrievalError, match="postgres_required"):
        await Retriever(engine, RetrievalConfig()).search(
            Actor(id=uuid4()),
            SearchRequest(query="test", collection_ids=(uuid4(),), as_of=TODAY),
            "lexical",
        )
    engine.dispose()


def test_negative_queries_are_not_scored_as_perfect_retrieval_or_zero_unknown_cost():
    rows = []
    for method in ("lexical", "dense", "hybrid"):
        for relevant in (True, False):
            rows.append(
                {
                    "method": method,
                    "metrics": {
                        str(k): ranked_metrics(["positive"], {"positive": 2} if relevant else {}, k)
                        for k in (1, 3, 5)
                    },
                    "forbidden_hits": 0,
                    "result": {
                        "latency_ms": 2,
                        "embedding_calls": 1,
                        "input_tokens": None,
                        "billed_embedding_usd": None,
                        "hits": ["positive"],
                    },
                }
            )
    report = summarize(rows)
    assert all(r["queries"] == 2 and r["positive_queries"] == 1 for r in report.values())
    assert report["dense"]["zero_relevance_empty_results"] == 0
    assert report["dense"]["input_tokens"] is None
    assert report["dense"]["billed_embedding_usd"] is None


def test_evaluation_artifacts_cannot_be_overwritten(tmp_path):
    path = tmp_path / "frozen.json"
    write_new(path, b"first")
    write_new(path, b"first")
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        write_new(path, b"different")
    assert path.read_bytes() == b"first"


@pytest.mark.postgres
@pytest.mark.skipif(
    not POSTGRES_URL or not OWNER_URL, reason="Disposable AI app/owner DB opt-in absent"
)
async def test_all_paths_use_identical_authorized_corpus_and_filter_before_limit():
    owner = create_db_engine(Settings(_env_file=None, database_url=SecretStr(OWNER_URL)))
    app = create_db_engine(Settings(_env_file=None, database_url=SecretStr(POSTGRES_URL)))
    a, b, reader, ca, cb = provision(owner)
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "WITH authorized" in statement:
            queries.append(statement)

    event.listen(app, "before_cursor_execute", capture)

    class SemanticMock:
        # Intentional fake CI query vector, never called an embedding quality result.
        async def embed_queries(self, request):
            return await FakeEmbeddingProvider().embed_queries(
                EmbeddingRequest(texts=("Allowed policy needle",))
            )

    try:
        ingest = Ingestor(app, FakeEmbeddingProvider(), FAKE_PROFILE)
        doc = uuid4()
        first = await ingest.ingest(
            a, ca, doc, metadata(), b"Allowed policy needle", "text/plain", expected_revision=0
        )
        await ingest.ingest(
            b,
            cb,
            uuid4(),
            metadata(),
            b"Forbidden policy needle needle needle",
            "text/plain",
            expected_revision=0,
        )
        await ingest.ingest(
            a,
            ca,
            uuid4(),
            metadata(status="retired"),
            b"needle retired",
            "text/plain",
            expected_revision=0,
        )
        cfg = RetrievalConfig(embedding=FAKE_PROFILE, top_k=1)
        service = Retriever(app, cfg, SemanticMock())
        request = SearchRequest(query="needle", collection_ids=(ca, cb), as_of=TODAY)
        results = [await service.search(reader, request, m) for m in ("lexical", "dense", "hybrid")]
        assert {r.eligible_chunks for r in results} == {1}
        assert len({r.eligible_corpus_sha256 for r in results}) == 1
        assert all(r.hits[0].citation.document_id == doc for r in results)
        assert all(not r.semantic_embeddings for r in results)
        assert results[0].embedding_calls == 0 and results[1].embedding_calls == 1

        class BadQuery:
            async def embed_queries(self, request):
                return EmbeddingResult(vectors=((float("nan"),) * 32,))

        with pytest.raises(RetrievalError, match="invalid_query_embedding"):
            await Retriever(app, cfg, BadQuery()).search(reader, request, "dense")
        with pytest.raises(RetrievalError, match="query_embedding_unavailable"):
            await Retriever(app, cfg).search(reader, request, "hybrid")
        for method in ("lexical", "dense", "hybrid"):
            result = await service.search(
                b, SearchRequest(query="needle", collection_ids=(ca,), as_of=TODAY), method
            )
            assert result.hits == () and result.embedding_calls == 0
            language = await service.search(
                reader, request.model_copy(update={"languages": ("en",)}), method
            )
            assert language.hits == ()
        # Deleted and superseded snapshots must not be scored as current candidates.
        current = await ingest.ingest(
            a,
            ca,
            doc,
            metadata("2"),
            b"Replacement policy needle",
            "text/plain",
            expected_revision=1,
        )
        updated = await service.search(reader, request, "hybrid")
        assert {h.citation.version_id for h in updated.hits} == {current.version_id}
        assert first.version_id != current.version_id
        incompatible = Retriever(
            app,
            cfg.model_copy(update={"chunking": ChunkConfig(size=64, overlap=8)}),
            SemanticMock(),
        )
        assert (await incompatible.search(reader, request, "dense")).hits == ()
        with owner.begin() as c:
            c.execute(delete(Grant).where(Grant.actor_id == reader.id))
        assert (await service.search(reader, request, "hybrid")).hits == ()
        assert DocumentReader(app).read(reader, (ca,), as_of=TODAY) == ()
        assert all(q.index("collection_grants") < q.index("FROM authorized") for q in queries)
        with Session(app) as session:
            events = session.scalars(
                select(DocumentAudit.event).where(DocumentAudit.actor_id == reader.id)
            ).all()
            assert {"retrieve_lexical", "retrieve_dense", "retrieve_hybrid"}.issubset(events)
        with app.connect() as c:
            # Default FTS has no Japanese morphology: a short Japanese word does not match
            # the continuous Japanese clause. This is a real parser limitation, not a mock.
            assert (
                c.execute(
                    text(
                        "SELECT to_tsvector('simple','在庫数は整数です') "
                        "@@ plainto_tsquery('simple','在庫')"
                    )
                ).scalar_one()
                is False
            )
            names = (
                c.execute(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE schemaname='ai' "
                        "AND indexname LIKE 'ix_chunks_fts_%'"
                    )
                )
                .scalars()
                .all()
            )
            assert set(names) == {"ix_chunks_fts_english", "ix_chunks_fts_simple"}
    finally:
        with owner.begin() as c:
            c.execute(delete(DocumentRecord).where(DocumentRecord.collection_id.in_((ca, cb))))
            c.execute(delete(Collection).where(Collection.id.in_((ca, cb))))
        app.dispose()
        owner.dispose()
