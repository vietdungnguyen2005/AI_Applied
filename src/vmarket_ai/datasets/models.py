from datetime import date
from typing import Literal, Self

from pydantic import Field, model_validator

from vmarket_ai.contracts import StrictModel
from vmarket_ai.datasets.quality import Encoding

Partition = Literal["train", "dev", "test", "regression"]
Target = Literal["sku", "name", "on_hand"]


class Supplier(StrictModel):
    id: Literal["a", "b"]
    vendor: Literal["NAMI", "RIVERBYTE"]
    encoding: Encoding
    sku: str
    headers: dict[Target, str]


class Family(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    supplier: Literal["a", "b"]
    partition: Literal["train", "dev", "test"]
    headers: tuple[str, ...]
    targets: tuple[Target, ...] | None
    orders: tuple[tuple[int, ...], ...]

    @model_validator(mode="after")
    def valid_shape(self) -> Self:
        if len(self.headers) != len(set(self.headers)):
            raise ValueError("Family headers must be distinct")
        if self.targets is not None and (
            len(self.targets) != len(self.headers)
            or set(self.targets) != {"sku", "name", "on_hand"}
        ):
            raise ValueError("Mapping targets must be exactly the three Java policy fields")
        for order in self.orders:
            if sorted(order) != list(range(len(self.headers))):
                raise ValueError("Each order must be a complete column permutation")
        return self


class Document(StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    logical_id: str
    supplier: Literal["a", "b"]
    version: str
    language: Literal["en", "ja"]
    status: Literal["current", "retired"]
    trust: Literal["curated_synthetic", "untrusted_fixture"]
    format: Literal["md", "txt"]
    effective_from: date
    restricted: bool = False
    sections: dict[str, str]


class DatasetSpec(StrictModel):
    version: Literal["v1"]
    seed: Literal[20261031]
    source_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    suppliers: tuple[Supplier, ...]
    families: tuple[Family, ...]
    documents: tuple[Document, ...]

    @model_validator(mode="after")
    def unique_inputs(self) -> Self:
        if {s.id for s in self.suppliers} != {"a", "b"} or len(self.suppliers) != 2:
            raise ValueError("Exactly two distinct suppliers are required")
        for items in (self.families, self.documents):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate authoring identity")
        return self
