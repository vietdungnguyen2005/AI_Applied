from typing import Annotated, Literal, Protocol
from uuid import UUID

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel
from vmarket_ai.ingestion.spec import Actor, Citation
from vmarket_ai.retrieval.spec import SearchRequest, SearchResult


class AskRequest(StrictModel):
    question: Annotated[str, Field(min_length=1, max_length=2000)]
    collection_ids: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=10)]
    language: Literal["en", "ja"]

    @model_validator(mode="after")
    def meaningful(self) -> "AskRequest":
        if not self.question.strip() or len(set(self.collection_ids)) != len(self.collection_ids):
            raise ValueError("Question/scope invalid")
        return self


class Claim(StrictModel):
    chunk_id: UUID
    quote: Annotated[str, Field(min_length=8, max_length=800)]


class Proposal(StrictModel):
    decision: Literal["answer", "insufficient", "conflict", "ambiguous"]
    claims: Annotated[tuple[Claim, ...], Field(max_length=3)]

    @model_validator(mode="after")
    def shape(self) -> "Proposal":
        if (self.decision == "answer") != bool(self.claims):
            raise ValueError("Only an answer contains claims")
        if len({c.chunk_id for c in self.claims}) != len(self.claims):
            raise ValueError("Duplicate source claim")
        return self


class Locator(StrictModel):
    kind: Literal["section", "page"]
    value: str | int

    @model_validator(mode="after")
    def bounded(self) -> "Locator":
        if self.kind == "page" and (type(self.value) is not int or not 1 <= self.value <= 200):
            raise ValueError("Invalid page")
        if self.kind == "section" and (
            not isinstance(self.value, str) or not 0 < len(self.value) <= 160
        ):
            raise ValueError("Invalid section")
        return self


class WireCitation(StrictModel):
    document_id: UUID
    version_id: UUID
    chunk_id: UUID
    locator: Locator
    source_url: Annotated[str, Field(pattern=r"^/ai/citations/[0-9a-f-]{36}$", max_length=70)]


Reason = Literal[
    "NO_SUPPORTED_EVIDENCE", "CONFLICTING_EVIDENCE", "OUTDATED_ONLY", "AMBIGUOUS_REQUEST"
]


class AskResponse(StrictModel):
    request_id: UUID
    status: Literal["answered", "abstained"]
    answer: Annotated[str | None, Field(max_length=8000)]
    reason: Reason | None
    citations: Annotated[tuple[WireCitation, ...], Field(max_length=10)]
    # Low means exact quote provenance was checked, not calibrated semantic confidence.
    confidence: Literal["unknown", "low"]
    provider_mode: Literal["fake", "live"]

    @model_validator(mode="after")
    def supported(self) -> "AskResponse":
        if self.status == "answered":
            if (
                not self.answer
                or not self.citations
                or self.reason is not None
                or self.confidence != "low"
            ):
                raise ValueError("Answer requires evidence")
        elif self.answer is not None or self.reason is None or self.confidence != "unknown":
            raise ValueError("Abstention cannot contain an answer")
        return self


class QAError(RuntimeError):
    def __init__(self, code: str, status: int) -> None:
        self.code, self.status = code, status
        super().__init__(code)


class RetrievalPort(Protocol):
    async def retrieve(self, actor: Actor, request: SearchRequest) -> SearchResult: ...
    def current(
        self, actor: Actor, scopes: tuple[UUID, ...], chunk_id: UUID
    ) -> Citation | None: ...


class BaselineProposal(StrictModel):
    decision: Literal["answer", "insufficient"]
    answer: Annotated[str | None, Field(max_length=2000)]

    @model_validator(mode="after")
    def shape(self) -> "BaselineProposal":
        if (self.decision == "answer") != bool(self.answer):
            raise ValueError("Baseline decision/answer mismatch")
        return self
