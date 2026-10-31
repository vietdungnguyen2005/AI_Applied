"""Offline release verification and a gold-free mapping-input projection."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import Field, JsonValue

from vmarket_ai.contracts import StrictModel
from vmarket_ai.datasets.common import DatasetError, digest
from vmarket_ai.datasets.quality import Encoding


class Artifact(StrictModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int = Field(ge=0)
    synthetic: Literal[True]
    license: Literal["CC0-1.0"]


class Manifest(StrictModel):
    dataset: Literal["vmarket-synthetic-v1"]
    generator_version: Literal["1.0.0"]
    seed: Literal[20261031]
    spec_sha256: str
    contract_source_sha: str
    snapshot_date: date
    owner: str
    license: Literal["CC0-1.0"]
    review_status: dict[str, str]
    artifacts: tuple[Artifact, ...]
    counts: dict[str, JsonValue]


class ReleaseLock(StrictModel):
    version: Literal["v1"]
    manifest_sha256: str
    freeze_sha256: str
    independent_label_review: Literal["pending"]


class FrozenRelease(StrictModel):
    release: Literal["v1"]
    manifest_sha256: str
    heldout_csv_sha256: dict[str, str]
    mapping_labels_sha256: str
    relevance_labels_sha256: str
    policy: str


class InputRecord(StrictModel):
    id: str
    path: str
    supplier: Literal["a", "b"]
    partition: Literal["train", "dev", "test", "regression"]
    family: str
    declared_encoding: Encoding
    selected_vendor_code: str
    contract: Literal["supplier_three", "legacy_stock_v2"]
    raw_sha256: str
    size_bytes: int
    license: Literal["CC0-1.0"]
    synthetic: Literal[True]
    intentional_identity_group: str | None


def owned_path(root: Path, relative: str) -> Path:
    name = PurePosixPath(relative)
    if name.is_absolute() or ".." in name.parts or "\\" in relative:
        raise DatasetError("Fixture path is outside the owned release")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise DatasetError("Fixture path is outside the owned release")
    return path


def verify_release(root: Path, lock_path: Path) -> Manifest:
    lock = ReleaseLock.model_validate_json(lock_path.read_bytes())
    raw_manifest = (root / "manifest.json").read_bytes()
    if digest(raw_manifest) != lock.manifest_sha256:
        raise DatasetError("Manifest differs from the independently stored release lock")
    if digest((root / "freeze.json").read_bytes()) != lock.freeze_sha256:
        raise DatasetError("Frozen held-out inventory changed")
    manifest = Manifest.model_validate_json(raw_manifest)
    frozen = FrozenRelease.model_validate_json((root / "freeze.json").read_bytes())
    if (
        frozen.manifest_sha256 != digest(raw_manifest)
        or frozen.mapping_labels_sha256 != digest((root / "labels/mapping.jsonl").read_bytes())
        or frozen.relevance_labels_sha256 != digest((root / "labels/relevance.jsonl").read_bytes())
    ):
        raise DatasetError("Freeze metadata does not match the released artifact hashes")
    paths = [a.path for a in manifest.artifacts]
    if len(paths) != len(set(paths)):
        raise DatasetError("Duplicate artifact identity")
    expected = set(paths) | {"manifest.json", "freeze.json"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != expected:
        raise DatasetError("Release has missing or unregistered files")
    for artifact in manifest.artifacts:
        raw = owned_path(root, artifact.path).read_bytes()
        if len(raw) != artifact.bytes or digest(raw) != artifact.sha256:
            raise DatasetError("Original fixture bytes changed")
    inputs = [
        InputRecord.model_validate_json(line)
        for line in (root / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if frozen.heldout_csv_sha256 != {r.id: r.raw_sha256 for r in inputs if r.partition == "test"}:
        raise DatasetError("Held-out input inventory differs from the freeze record")
    return manifest


@dataclass(frozen=True)
class MappingInput:
    raw_bytes: bytes
    declared_encoding: Encoding
    selected_vendor_code: str


def load_mapping_input(root: Path, lock_path: Path, case_id: str) -> MappingInput:
    """For offline evaluation; returns no labels, partitions, case names or candidate mappings."""
    verify_release(root, lock_path)
    records = [
        InputRecord.model_validate_json(line)
        for line in (root / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    matches = [r for r in records if r.id == case_id]
    if len(matches) != 1 or matches[0].contract != "supplier_three":
        raise DatasetError("Unknown case or incompatible mapping contract")
    record = matches[0]
    raw = owned_path(root, record.path).read_bytes()
    if digest(raw) != record.raw_sha256:
        raise DatasetError("Input bytes differ from the registered original")
    return MappingInput(raw, record.declared_encoding, record.selected_vendor_code)


def summary(root: Path, lock_path: Path) -> str:
    manifest = verify_release(root, lock_path)
    return json.dumps(
        {
            "status": "integrity_verified",
            "counts": manifest.counts,
            "independent_label_review": "pending",
            "model_quality_metrics": "NOT_RUN",
        }
    )
