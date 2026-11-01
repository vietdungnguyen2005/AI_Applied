import base64
import binascii
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel
from vmarket_ai.datasets.quality import Encoding
from vmarket_ai.qa.spec import WireCitation

Target = Literal["sku", "name", "on_hand"]
Header = Annotated[str, Field(min_length=1, max_length=80)]
TARGETS: tuple[Target, ...] = ("sku", "name", "on_hand")
Warning = Literal[
    "AMBIGUOUS_HEADER",
    "UNMAPPED_HEADER",
    "FRESHNESS_UNVERIFIED",
    "VENDOR_NOT_VERIFIED",
    "ENCODING_DECLARED",
    "SOURCE_UNTRUSTED",
    "RULE_BASELINE",
    "MODEL_UNAVAILABLE",
    "MODEL_OUTPUT_INVALID",
    "BUSINESS_VALIDATION_REQUIRED",
    "PROFILE_MISMATCH",
    "SAMPLE_TRUNCATED",
    "ROW_REVIEW_REQUIRED",
    "NO_AUTHORIZED_SOP",
]


class MappingRequest(StrictModel):
    raw_base64: Annotated[str, Field(max_length=6_666_668)]
    declared_encoding: Encoding
    selected_vendor_code: Annotated[str, Field(min_length=1, max_length=32)]
    profile_ids: Annotated[tuple[str, ...], Field(max_length=5)] = ()
    method: Literal["rule", "ai"] = "rule"
    synthetic: Literal[True]

    def original(self) -> bytes:
        try:
            raw = base64.b64decode(self.raw_base64, validate=True)
        except (binascii.Error, ValueError):
            raise MappingError("INPUT_INVALID", 400) from None
        if not 1 <= len(raw) <= 5_000_000:
            raise MappingError("INPUT_TOO_LARGE", 413)
        return raw

    @model_validator(mode="after")
    def unique_profiles(self) -> Self:
        if len(set(self.profile_ids)) != len(self.profile_ids):
            raise ValueError("Duplicate profile reference")
        return self


class Candidate(StrictModel):
    profile_id: str
    version: int
    vendor_code: str
    encoding: Encoding
    active: bool
    mapping: dict[Target, Header]


class Choices(StrictModel):
    sku: Header | None
    name: Header | None
    on_hand: Header | None

    def selected(self) -> dict[Target, str]:
        return {t: h for t in TARGETS if (h := getattr(self, t)) is not None}


class Assignment(StrictModel):
    source_header: Header
    target_field: Target
    uncertainty: Literal["low", "medium", "high", "unknown"]
    basis: Literal["rule", "document", "model"]
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    citations: Annotated[tuple[WireCitation, ...], Field(max_length=5)] = ()


class Difference(StrictModel):
    profile_id: str
    version: int
    active: bool
    encoding_matches: bool
    changes: dict[Target, tuple[str, str | None]]


class MappingResponse(StrictModel):
    request_id: UUID
    raw_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    declared_encoding: Encoding
    selected_vendor_code: str
    vendor_code: str | None
    vendor_verification: Literal["standalone_fixture", "bff_profile_snapshot", "unverified"]
    status: Literal["suggested", "needs_review", "abstained"]
    assignments: Annotated[tuple[Assignment, ...], Field(max_length=3)]
    unmapped_headers: Annotated[tuple[Header, ...], Field(max_length=100)]
    missing_required_fields: tuple[Target, ...]
    warnings: Annotated[tuple[Warning, ...], Field(max_length=14)]
    reason: str
    profile_differences: tuple[Difference, ...]
    requires_human_acceptance: Literal[True] = True
    provider_mode: Literal["fake", "local"]

    @model_validator(mode="after")
    def invariants(self) -> Self:
        fields = [a.target_field for a in self.assignments]
        headers = [a.source_header for a in self.assignments]
        if len(set(fields)) != len(fields) or len(set(headers)) != len(headers):
            raise ValueError("Assignments must be one-to-one")
        if (self.status == "suggested" and len(fields) != 3) or (
            self.status == "abstained" and fields
        ):
            raise ValueError("Draft status inconsistent")
        if self.vendor_code is not None and self.vendor_code != self.selected_vendor_code:
            raise ValueError("Vendor cannot be inferred")
        if (self.vendor_verification != "unverified") != (self.vendor_code is not None):
            raise ValueError("Vendor verification inconsistent")
        if len(set(self.unmapped_headers)) != len(self.unmapped_headers) or (
            set(self.unmapped_headers) & set(headers)
        ):
            raise ValueError("Unmapped header list inconsistent")
        if self.missing_required_fields != tuple(t for t in TARGETS if t not in fields):
            raise ValueError("Missing field list inconsistent")
        return self


class MappingError(RuntimeError):
    def __init__(self, code: str, status: int) -> None:
        self.code, self.status = code, status
        super().__init__(code)
