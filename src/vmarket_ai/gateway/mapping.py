"""Request-scoped BFF profile evidence. No business client or mutation capability."""

import re
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel
from vmarket_ai.mapping.policy import StandalonePolicy
from vmarket_ai.mapping.spec import TARGETS, Candidate, MappingRequest


class SignedMapping(StrictModel):
    input: MappingRequest
    profile_candidates: Annotated[tuple[Candidate, ...], Field(min_length=1, max_length=1)]

    @model_validator(mode="after")
    def current_snapshot(self) -> Self:
        p = self.profile_candidates[0]
        if not (
            p.active
            and p.version > 0
            and re.fullmatch(r"[a-z][a-z0-9-]{0,47}", p.profile_id)
            and p.vendor_code == self.input.selected_vendor_code
            and p.encoding == self.input.declared_encoding
            and self.input.profile_ids == (p.profile_id,)
            and set(p.mapping) == set(TARGETS)
            and len(set(p.mapping.values())) == 3
        ):
            raise ValueError("Current active matching profile required")
        return self


class SnapshotPolicy(StandalonePolicy):
    verification: Literal["standalone_fixture", "bff_profile_snapshot"] = "bff_profile_snapshot"

    def __init__(self, snapshot: SignedMapping) -> None:
        self.snapshot = snapshot

    def profiles(self, vendor: str, ids: tuple[str, ...]) -> tuple[Candidate, ...]:
        return self.snapshot.profile_candidates
