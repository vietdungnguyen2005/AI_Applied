from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, Literal, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Message(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=8000)]


class ChatRequest(StrictModel):
    messages: Annotated[tuple[Message, ...], Field(min_length=1, max_length=8)]
    max_output_tokens: Annotated[int, Field(ge=1, le=512)] = 128
    structured_output: dict[str, object] | None = None


class ChatResult(StrictModel):
    text: str
    model: str
    provider_mode: Literal["fake", "live"]
    prompt_tokens: int
    completion_tokens: int
    cost_usd: Decimal


class EmbeddingRequest(StrictModel):
    texts: Annotated[
        tuple[Annotated[str, Field(min_length=1, max_length=4000)], ...],
        Field(min_length=1, max_length=8),
    ]


class EmbeddingResult(StrictModel):
    vectors: tuple[tuple[float, ...], ...]
    model: str = "fake-sha256-32"
    dimensions: int = 32
    provider_mode: Literal["fake", "local"] = "fake"
    input_tokens: int | None = Field(default=None, ge=0)
    billed_usd: Decimal | None = Field(default=None, ge=0)


class ChatModel(Protocol):
    async def complete(self, request: ChatRequest) -> ChatResult: ...


class EmbeddingProvider(Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...


class QueryEmbeddingProvider(Protocol):
    async def embed_queries(self, request: EmbeddingRequest) -> EmbeddingResult: ...


class EmptyArguments(StrictModel):
    pass


class JobArguments(StrictModel):
    job_id: UUID


class KnowledgeArguments(StrictModel):
    query: Annotated[str, Field(min_length=1, max_length=2000)]
    collection_ids: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=10)]
    top_k: Annotated[int, Field(ge=1, le=5)]


class ProfilesIntent(StrictModel):
    call_id: UUID
    tool_name: Literal["get_integration_profiles"]
    arguments: EmptyArguments


class ImportsIntent(StrictModel):
    call_id: UUID
    tool_name: Literal["get_imports"]
    arguments: EmptyArguments


class InspectionIntent(StrictModel):
    call_id: UUID
    tool_name: Literal["inspect_import_job"]
    arguments: JobArguments


class ReportIntent(StrictModel):
    call_id: UUID
    tool_name: Literal["get_reconciliation_report"]
    arguments: JobArguments


class KnowledgeIntent(StrictModel):
    call_id: UUID
    tool_name: Literal["search_supplier_knowledge"]
    arguments: KnowledgeArguments


ToolIntent = Annotated[
    ProfilesIntent | ImportsIntent | InspectionIntent | ReportIntent | KnowledgeIntent,
    Field(discriminator="tool_name"),
]
Payload = TypeVar("Payload", bound=BaseModel)


class ToolResult(StrictModel, Generic[Payload]):
    """Typed interface only; no business executor exists in P03."""

    call_id: UUID
    observed_at: datetime
    status: Literal["ok", "denied", "unavailable", "invalid", "timeout", "budget_exceeded"]
    data: Payload | None
