import hashlib
import json
import math
import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import insert, text
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import SQLAlchemyError

from vmarket_ai.contracts import EmbeddingRequest, QueryEmbeddingProvider
from vmarket_ai.ingestion.models import DocumentAudit
from vmarket_ai.ingestion.spec import Actor, Citation, fingerprint
from vmarket_ai.retrieval.spec import (
    Hit,
    Method,
    RetrievalConfig,
    RetrievalError,
    SearchRequest,
    SearchResult,
)


def query_text(value: str, normalization: str) -> str:
    return unicodedata.normalize("NFC", value).strip() if normalization == "nfc" else value


def lexical_query(value: str, match: str) -> str:
    # Generated quoted words only, never tsquery syntax or SQL from user input.
    words = re.findall(r"[^\W_]+(?:[-'][^\W_]+)*", value, flags=re.UNICODE)[:256]
    return (" OR " if match == "any" else " ").join('"' + word + '"' for word in words)


def fuse(
    lexical: tuple[Hit, ...], dense: tuple[Hit, ...], config: RetrievalConfig
) -> tuple[Hit, ...]:
    by_id: dict[UUID, Hit] = {}
    for branch, weight, name in (
        (lexical, config.lexical_weight, "lexical"),
        (dense, config.dense_weight, "dense"),
    ):
        for rank, hit in enumerate(branch, 1):
            key = hit.citation.chunk_id
            previous = by_id.get(key)
            score = weight / (config.rrf_constant + rank)
            ranks = {
                "lexical_rank": previous.lexical_rank if previous else None,
                "dense_rank": previous.dense_rank if previous else None,
            }
            ranks[name + "_rank"] = rank
            by_id[key] = Hit(
                citation=hit.citation, score=score + (previous.score if previous else 0), **ranks
            )
    return tuple(sorted(by_id.values(), key=lambda h: (-h.score, str(h.citation.chunk_id))))


def authorized_sql(config: RetrievalConfig, request: SearchRequest) -> str:
    # Identifiers here are server-selected from validated enums; all values use bound parameters.
    vector = "vector_e5" if config.embedding.mode == "local" else "vector_fake"
    scopes = ",".join(f":scope{i}" for i in range(len(request.collection_ids)))
    languages = ",".join(f":lang{i}" for i in range(len(request.languages)))
    vendors = ",".join(f":vendor{i}" for i in range(len(request.vendors)))
    optional = ""
    if languages:
        optional += f" AND v.metadata_json->>'language' IN ({languages})"
    if vendors:
        optional += f" AND v.metadata_json->>'vendor' IN ({vendors})"
    return f"""
    WITH authorized AS MATERIALIZED (
      SELECT c.id AS chunk_id, c.snapshot_id, c.ordinal, c.locator, c.start_offset,
             c.end_offset, c.text, c.text_sha256, v.id AS version_id,
             v.source_version, v.raw_sha256, d.id AS document_id, e.{vector} AS embedding
      FROM ai.document_chunks c
      JOIN ai.document_snapshots s ON c.snapshot_id=s.id
      JOIN ai.document_versions v ON s.version_id=v.id
      JOIN ai.documents d ON v.document_id=d.id AND d.active_snapshot_id=s.id
      JOIN ai.chunk_embeddings e ON c.id=e.chunk_id
      WHERE d.deleted=false AND s.eligible=true AND e.{vector} IS NOT NULL
        AND s.pipeline_sha256=:pipeline AND s.dimensions=:dimensions
        AND s.profile_json->'embedding'->>'model'=:model
        AND d.collection_id IN ({scopes})
        AND EXISTS(SELECT 1 FROM ai.collection_grants g WHERE g.collection_id=d.collection_id
                   AND g.actor_id=:actor AND g.role IN ('reader','writer'))
        AND v.metadata_json->>'effective_from' <= :as_of
        AND (v.metadata_json->>'effective_until' IS NULL
             OR v.metadata_json->>'effective_until' >= :as_of)
        {optional}
    )
    """


def to_hit(row: RowMapping) -> Hit:
    return Hit(
        citation=Citation(
            document_id=row["document_id"],
            version_id=row["version_id"],
            snapshot_id=row["snapshot_id"],
            chunk_id=row["chunk_id"],
            source_version=row["source_version"],
            raw_sha256=row["raw_sha256"],
            locator=row["locator"],
            start=row["start_offset"],
            end=row["end_offset"],
            text=row["text"],
        ),
        score=float(row["score"]),
    )


class Retriever:
    def __init__(
        self,
        engine: Engine,
        config: RetrievalConfig,
        provider: QueryEmbeddingProvider | None = None,
    ) -> None:
        self.engine, self.config, self.provider = engine, config, provider

    async def search(self, actor: Actor, request: SearchRequest, method: Method) -> SearchResult:
        if method not in {"lexical", "dense", "hybrid"}:
            raise RetrievalError("unsupported_method")
        if self.engine.dialect.name != "postgresql":
            raise RetrievalError("postgres_required")
        started = perf_counter()
        config = self.config
        question = query_text(request.query, config.query_normalization)
        cte = authorized_sql(config, request)
        params: dict[str, object] = {
            "pipeline": fingerprint(config.embedding, config.chunking),
            "dimensions": config.embedding.dimensions,
            "model": config.embedding.model,
            "actor": actor.id,
            "as_of": request.as_of.isoformat(),
            "pool": config.candidate_pool,
            **{f"scope{i}": c for i, c in enumerate(request.collection_ids)},
            **{f"lang{i}": language for i, language in enumerate(request.languages)},
            **{f"vendor{i}": vendor for i, vendor in enumerate(request.vendors)},
        }
        embedding_ms = 0.0
        calls = 0
        tokens: int | None = 0
        cost: Decimal | None = Decimal("0")
        try:
            # A single repeatable-read snapshot fixes the authorized corpus for both branches.
            with (
                self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
                conn.begin(),
            ):
                identities = conn.execute(
                    text(
                        cte + "SELECT chunk_id,snapshot_id,text_sha256 "
                        "FROM authorized ORDER BY chunk_id LIMIT 10001"
                    ),
                    params,
                ).all()
                if len(identities) > 10000:
                    raise RetrievalError("corpus_limit")
                corpus_sha = hashlib.sha256(
                    json.dumps([[str(v) for v in row] for row in identities]).encode()
                ).hexdigest()
                branches: dict[str, tuple[Hit, ...]] = {"lexical": (), "dense": ()}
                if identities and method in {"dense", "hybrid"}:
                    if self.provider is None:
                        raise RetrievalError("query_embedding_unavailable")
                    embedding_started = perf_counter()
                    try:
                        result = await self.provider.embed_queries(
                            EmbeddingRequest(texts=(question,))
                        )
                    except Exception:
                        raise RetrievalError("query_embedding_failed") from None
                    embedding_ms = (perf_counter() - embedding_started) * 1000
                    calls = 1
                    if (
                        result.model != config.embedding.model
                        or result.dimensions != config.embedding.dimensions
                        or result.provider_mode != config.embedding.mode
                        or len(result.vectors) != 1
                    ):
                        raise RetrievalError("query_embedding_mismatch")
                    vector = result.vectors[0]
                    if (
                        len(vector) != config.embedding.dimensions
                        or not all(math.isfinite(v) for v in vector)
                        or not 0.99 <= math.sqrt(sum(v * v for v in vector)) <= 1.01
                    ):
                        raise RetrievalError("invalid_query_embedding")
                    params["vector"] = json.dumps(vector, allow_nan=False)
                    tokens, cost = result.input_tokens, result.billed_usd
                sql_started = perf_counter()
                if identities and method in {"lexical", "hybrid"}:
                    params["terms"] = lexical_query(question, config.lexical_match)
                    # Literal config is an enum, enabling PostgreSQL expression-index matching.
                    lex = config.lexical_config
                    statement = (
                        cte
                        + f"""
                      SELECT *, ts_rank_cd(to_tsvector('{lex}'::regconfig,text),
                          websearch_to_tsquery('{lex}'::regconfig,:terms)) AS score
                      FROM authorized WHERE to_tsvector('{lex}'::regconfig,text)
                          @@ websearch_to_tsquery('{lex}'::regconfig,:terms)
                      ORDER BY score DESC,chunk_id LIMIT :pool
                    """
                    )
                    branches["lexical"] = tuple(
                        to_hit(r) for r in conn.execute(text(statement), params).mappings()
                    )
                if identities and method in {"dense", "hybrid"}:
                    dims = config.embedding.dimensions
                    statement = (
                        cte
                        + f"""
                      SELECT *, 1-(embedding <=> CAST(:vector AS vector({dims}))) AS score
                      FROM authorized
                      ORDER BY embedding <=> CAST(:vector AS vector({dims})),chunk_id
                      LIMIT :pool
                    """
                    )
                    branches["dense"] = tuple(
                        to_hit(r) for r in conn.execute(text(statement), params).mappings()
                    )
                sql_ms = (perf_counter() - sql_started) * 1000
                hits = (
                    fuse(branches["lexical"], branches["dense"], config)
                    if method == "hybrid"
                    else branches[method]
                )[: config.top_k]
                conn.execute(
                    insert(DocumentAudit).values(
                        id=uuid4(),
                        actor_id=actor.id,
                        event="retrieve_" + method,
                        entity_id=None,
                        count=len(hits),
                        observed_at=datetime.now(UTC),
                    )
                )
            return SearchResult(
                method=method,
                hits=hits,
                eligible_corpus_sha256=corpus_sha,
                eligible_chunks=len(identities),
                latency_ms=(perf_counter() - started) * 1000,
                embedding_ms=embedding_ms,
                sql_ms=sql_ms,
                embedding_calls=calls,
                input_tokens=tokens,
                billed_embedding_usd=cost,
                semantic_embeddings=config.embedding.mode == "local",
            )
        except SQLAlchemyError:
            raise RetrievalError("retrieval_storage_failed") from None
