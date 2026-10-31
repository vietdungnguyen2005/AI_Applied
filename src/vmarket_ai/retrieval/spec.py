from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel
from vmarket_ai.ingestion.spec import E5_PROFILE, ChunkConfig, Citation, EmbedProfile

Method = Literal["lexical", "dense", "hybrid"]


class RetrievalError(RuntimeError):
    """Static safe code; never store a raw query or underlying SQL/provider exception."""


class RetrievalConfig(StrictModel):
    embedding: EmbedProfile = E5_PROFILE
    chunking: ChunkConfig = ChunkConfig()
    top_k: int = Field(default=5, ge=1, le=5)
    candidate_pool: int = Field(default=20, ge=5, le=100)
    lexical_config: Literal["simple", "english"] = "english"
    lexical_match: Literal["any", "all"] = "any"
    query_normalization: Literal["nfc", "verbatim"] = "nfc"
    rrf_constant: int = Field(default=60, ge=1, le=1000)
    lexical_weight: float = Field(default=1, gt=0, le=10, allow_inf_nan=False)
    dense_weight: float = Field(default=1, gt=0, le=10, allow_inf_nan=False)
    reranker: Literal["none"] = "none"


class SearchRequest(StrictModel):
    query: Annotated[str, Field(min_length=1, max_length=2000)]
    collection_ids: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=10)]
    as_of: date
    languages: Annotated[tuple[Literal["en", "ja", "mixed"], ...], Field(max_length=3)] = ()
    vendors: Annotated[tuple[Literal["NAMI", "RIVERBYTE"], ...], Field(max_length=2)] = ()

    @model_validator(mode="after")
    def meaningful(self) -> "SearchRequest":
        if not self.query.strip() or len(self.collection_ids) != len(set(self.collection_ids)):
            raise ValueError("Query and scope must be meaningful")
        return self


class Hit(StrictModel):
    citation: Citation
    score: float = Field(allow_inf_nan=False)
    lexical_rank: int | None = None
    dense_rank: int | None = None


class SearchResult(StrictModel):
    method: Method
    hits: tuple[Hit, ...]
    eligible_corpus_sha256: str
    eligible_chunks: int
    latency_ms: float
    embedding_ms: float
    sql_ms: float
    embedding_calls: int
    input_tokens: int | None
    billed_embedding_usd: Decimal | None
    semantic_embeddings: bool
    reranker: Literal["none"] = "none"
