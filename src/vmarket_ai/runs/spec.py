from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel


class RunCommand(StrictModel):
    action: Literal["start", "inspect", "plan", "claim", "record", "recover", "cancel"]
    question: Annotated[str, Field(min_length=1, max_length=2000)] | None = None
    conversation_id: UUID | None = None
    collection_ids: Annotated[tuple[UUID, ...], Field(max_length=10)] | None = None
    expected_revision: Annotated[int, Field(ge=0, le=64)] | None = None
    lease_id: UUID | None = None
    observation: dict[str, Any] | None = None

    @model_validator(mode="after")
    def exact_command(self) -> Self:
        fields = {"action"}
        if self.action == "start":
            fields |= {"question", "conversation_id", "collection_ids"}
        elif self.action != "inspect":
            fields.add("expected_revision")
        if self.action == "record":
            fields |= {"lease_id", "observation"}
        if self.model_fields_set != fields or any(getattr(self, k) is None for k in fields):
            raise ValueError("Closed command fields required")
        if self.question is not None and not self.question.strip():
            raise ValueError("Empty question")
        if self.collection_ids is not None and len(set(self.collection_ids)) != len(
            self.collection_ids
        ):
            raise ValueError("Duplicate scopes")
        return self
