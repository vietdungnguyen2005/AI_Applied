import hashlib
import json
import unicodedata
from datetime import date
from importlib.metadata import version
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel


class IngestionError(RuntimeError):
    """Safe error code only; source/provider exception text must not escape."""


class Actor(StrictModel):
    # Created by trusted local tooling, not accepted from an HTTP request/model.
    id: UUID


class Metadata(StrictModel):
    vendor: Annotated[str, Field(min_length=1, max_length=80)]
    owner: Annotated[str, Field(min_length=1, max_length=80)]
    source: Annotated[str, Field(min_length=1, max_length=120)]
    source_version: Annotated[str, Field(min_length=1, max_length=80)]
    language: Literal["ja", "en", "mixed"]
    effective_from: date
    effective_until: date | None = None
    status: Literal["current", "retired"] = "current"
    trust_level: Literal["curated_synthetic", "untrusted_fixture"] = "curated_synthetic"
    synthetic: Literal[True] = True
    license: Literal["CC0-1.0"] = "CC0-1.0"

    @model_validator(mode="after")
    def dates(self) -> "Metadata":
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("Invalid effective date interval")
        return self


class ChunkConfig(StrictModel):
    size: int = Field(default=320, ge=32, le=800)
    overlap: int = Field(default=48, ge=0, le=200)

    @model_validator(mode="after")
    def progress(self) -> "ChunkConfig":
        if self.overlap >= self.size:
            raise ValueError("Overlap must be smaller than chunk size")
        return self


class EmbedProfile(StrictModel):
    model: str
    dimensions: Literal[32, 384]
    mode: Literal["fake", "local"]

    @model_validator(mode="after")
    def known(self) -> "EmbedProfile":
        if (self.mode, self.dimensions, self.model) not in {
            ("fake", 32, "fake-sha256-32"),
            ("local", 384, E5_MODEL),
        }:
            raise ValueError("Unregistered embedding profile")
        return self


E5_REPO = "intfloat/multilingual-e5-small"
E5_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
E5_MODEL = f"{E5_REPO}@{E5_REVISION}:onnx-fp32-mean-l2-v1"
FAKE_PROFILE = EmbedProfile(model="fake-sha256-32", dimensions=32, mode="fake")
E5_PROFILE = EmbedProfile(model=E5_MODEL, dimensions=384, mode="local")
PARSER_VERSION = "bounded-docs-v1"


def pipeline_manifest(profile: EmbedProfile, config: ChunkConfig) -> dict[str, object]:
    return {
        "embedding": profile.model_dump(),
        "chunking": config.model_dump(),
        "parser": PARSER_VERSION,
        "normalization": "NFC-lines-v1",
        "unicode_version": unicodedata.unidata_version,
        "parser_packages": {name: version(name) for name in ("pypdf", "python-docx", "defusedxml")},
    }


def fingerprint(profile: EmbedProfile, config: ChunkConfig) -> str:
    value = pipeline_manifest(profile, config)
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class Section(StrictModel):
    locator: str
    text: str


class Extraction(StrictModel):
    sections: tuple[Section, ...]
    parser: str
    quality: Literal["extracted_text_only"] = "extracted_text_only"
    confidence: None = None
    ocr_performed: Literal[False] = False


class Part(StrictModel):
    ordinal: int
    locator: str
    start: int
    end: int
    text: str
    text_sha256: str


class Receipt(StrictModel):
    document_id: UUID
    version_id: UUID
    snapshot_id: UUID
    revision: int
    chunks: int
    unchanged: bool


class Citation(StrictModel):
    document_id: UUID
    version_id: UUID
    snapshot_id: UUID
    chunk_id: UUID
    source_version: str
    raw_sha256: str
    locator: str
    start: int
    end: int
    text: str
