"""Offline data integrity/structure checks, not model evaluation or Java integration."""

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, JsonValue, TypeAdapter

from vmarket_ai.contracts import StrictModel
from vmarket_ai.datasets.common import DatasetError, digest
from vmarket_ai.datasets.quality import inspect_csv, inspect_text
from vmarket_ai.datasets.release import InputRecord, owned_path, verify_release


class MappingLabel(StrictModel):
    case_id: str
    partition: str
    family: str
    label_status: Literal["provisional_agent_authored"]
    independent_review: Literal["pending"]
    expected_suggestion: Literal[
        "suggested", "needs_review", "abstained", "input_error", "not_applicable"
    ]
    target_to_source: dict[str, str] | None
    expected_structure_code: str
    expected_business_condition: str
    candidate_definition_for_human_review_only: dict[str, JsonValue] | None
    rationale: str


class Section(StrictModel):
    document_id: UUID
    version_id: UUID
    section_id: str
    grade: Literal[2]


class RelevanceLabel(StrictModel):
    query_id: str
    partition: str
    family: str
    expected_outcome: Literal["answerable", "abstain_conflict", "abstain_unknown", "deny_access"]
    relevant_sections: tuple[Section, ...]
    forbidden_document_ids: tuple[UUID, ...]
    label_status: Literal["provisional_agent_authored"]
    independent_review: Literal["pending"]
    rationale: str


class Query(StrictModel):
    id: str
    partition: str
    family: str
    supplier: Literal["a", "b"]
    language: Literal["en", "ja"]
    question: str
    readable_collection_ids: tuple[UUID, ...]
    requested_collection_ids: tuple[UUID, ...]
    synthetic: Literal[True]


class CorpusRecord(StrictModel):
    id: str
    document_id: UUID
    version_id: UUID
    source_version: str
    collection_id: UUID
    vendor: Literal["NAMI", "RIVERBYTE"]
    path: str
    source: Literal["repository-owned-synthetic"]
    language: Literal["en", "ja"]
    owner: Literal["synthetic-curator"]
    effective_from: date
    effective_until: date | None
    status: Literal["current", "retired"]
    trust_level: Literal["curated_synthetic", "untrusted_fixture"]
    media_type: str
    sections: tuple[str, ...]
    quality: dict[str, JsonValue]
    raw_sha256: str
    eligible_for_default_index: bool
    license: Literal["CC0-1.0"]
    synthetic: Literal[True]


T = TypeVar("T", bound=BaseModel)


def records(path: Path, model: type[T]) -> list[T]:
    return [
        model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines()
    ]


def audit(root: Path, lock_path: Path) -> dict[str, object]:
    manifest = verify_release(root, lock_path)
    inputs = records(root / "inputs.jsonl", InputRecord)
    labels = records(root / "labels/mapping.jsonl", MappingLabel)
    corpus = records(root / "corpus.jsonl", CorpusRecord)
    queries = records(root / "queries.jsonl", Query)
    relevance = records(root / "labels/relevance.jsonl", RelevanceLabel)
    input_map = {r.id: r for r in inputs}
    label_map = {r.case_id: r for r in labels}
    query_map = {q.id: q for q in queries}
    if (
        len(input_map) != len(inputs)
        or len(label_map) != len(labels)
        or set(input_map) != set(label_map)
    ):
        raise DatasetError("Mapping labels and input IDs must be unique and aligned")
    if (
        len(query_map) != len(queries)
        or len({r.query_id for r in relevance}) != len(relevance)
        or {r.query_id for r in relevance} != set(query_map)
    ):
        raise DatasetError("Relevance labels and query IDs must be unique and aligned")
    family_splits: dict[str, set[str]] = defaultdict(set)
    header_splits: dict[tuple[str, ...], set[str]] = defaultdict(set)
    csv_counts: Counter[str] = Counter()
    duplicate_groups: dict[str, list[InputRecord]] = defaultdict(list)
    for item in inputs:
        label = label_map[item.id]
        raw_csv = owned_path(root, item.path).read_bytes()
        if digest(raw_csv) != item.raw_sha256 or len(raw_csv) != item.size_bytes:
            raise DatasetError("CSV input metadata disagrees with original bytes")
        csv_quality = inspect_csv(raw_csv, item.declared_encoding)
        if csv_quality.code != label.expected_structure_code:
            raise DatasetError("CSV structure outcome differs from declared fixture expectation")
        if (item.partition, item.family) != (label.partition, label.family):
            raise DatasetError("Input/label split metadata mismatch")
        if label.target_to_source is not None and (
            set(label.target_to_source) != {"sku", "name", "on_hand"}
            or len(set(label.target_to_source.values())) != 3
        ):
            raise DatasetError("Gold mapping is outside fixed target/source policy")
        if not label.rationale:
            raise DatasetError("Missing provisional label rationale")
        csv_counts[csv_quality.code] += 1
        duplicate_groups[item.raw_sha256].append(item)
        if item.partition != "regression":
            family_splits["mapping:" + item.family].add(item.partition)
            header_splits[tuple(sorted(csv_quality.headers))].add(item.partition)
    for group in duplicate_groups.values():
        if len(group) > 1 and (
            any(r.partition != "regression" for r in group)
            or len({r.intentional_identity_group for r in group}) != 1
            or group[0].intentional_identity_group is None
        ):
            raise DatasetError("Unexplained duplicate raw bytes or split leakage")
    doc_map = {(d.document_id, d.version_id): d for d in corpus}
    if len(doc_map) != len(corpus):
        raise DatasetError("Duplicate document-version identity")
    document_quality: Counter[str] = Counter()
    for doc in corpus:
        raw = owned_path(root, doc.path).read_bytes()
        text_quality = inspect_text(raw, doc.media_type)
        actual = TypeAdapter(dict[str, JsonValue]).validate_python(asdict(text_quality))
        if digest(raw) != doc.raw_sha256:
            raise DatasetError("Document original-byte hash disagrees with metadata")
        if doc.quality != actual:
            raise DatasetError("Document quality metadata disagrees with actual bytes")
        if text_quality.status != "verified_text" and doc.eligible_for_default_index:
            raise DatasetError("Unparseable fixture cannot enter default corpus")
        if doc.eligible_for_default_index and (
            doc.status != "current" or doc.trust_level != "curated_synthetic"
        ):
            raise DatasetError("Retired/untrusted fixture cannot be default policy authority")
        for section in doc.sections:
            text = raw.decode("utf-8")
            if f"## {section}\n" not in text and f"[section:{section}]\n" not in text:
                raise DatasetError("Source section locator does not exist")
        document_quality[text_quality.status] += 1
    for relevance_label in relevance:
        query = query_map[relevance_label.query_id]
        if (query.partition, query.family) != (relevance_label.partition, relevance_label.family):
            raise DatasetError("Query/label split metadata mismatch")
        family_splits["query:" + query.family].add(query.partition)
        for source_section in relevance_label.relevant_sections:
            source_doc = doc_map.get((source_section.document_id, source_section.version_id))
            if source_doc is None or source_section.section_id not in source_doc.sections:
                raise DatasetError("Relevance label refers to a missing source section")
            if source_doc.collection_id not in query.readable_collection_ids:
                raise DatasetError("Positive relevance label crosses the declared document scope")
        if (
            relevance_label.expected_outcome == "abstain_conflict"
            and len(relevance_label.relevant_sections) != 2
        ):
            raise DatasetError("Conflict case must identify both contradictory sources")
        if (
            relevance_label.expected_outcome in {"abstain_unknown", "deny_access"}
            and relevance_label.relevant_sections
        ):
            raise DatasetError(
                "Unanswerable/denied question cannot have authorized positive evidence"
            )
        if (
            relevance_label.expected_outcome == "answerable"
            and not relevance_label.relevant_sections
        ):
            raise DatasetError("Answerable question needs explicit source evidence")
        if relevance_label.expected_outcome == "deny_access" and set(
            query.requested_collection_ids
        ).issubset(query.readable_collection_ids):
            raise DatasetError("Denied fixture must request a different document scope")
    if any(len(splits) != 1 for splits in [*family_splits.values(), *header_splits.values()]):
        raise DatasetError("Benchmark family or header signature crosses partition boundary")
    aliases = TypeAdapter(dict[str, list[str]]).validate_json(
        (root / "fixture-aliases.json").read_bytes()
    )
    known_ids = set(input_map) | {d.id for d in corpus}
    if any(target not in known_ids for targets in aliases.values() for target in targets):
        raise DatasetError("P01 alias refers to a missing fixture")
    counts = {
        "csv": len(inputs),
        "documents": len(corpus),
        "mapping_labels": len(labels),
        "relevance_labels": len(relevance),
        "mapping_partitions": dict(Counter(i.partition for i in inputs)),
        "relevance_partitions": dict(Counter(q.partition for q in queries)),
    }
    if counts != manifest.counts:
        raise DatasetError("Manifest counts do not match the actual released records")
    return {
        "status": "integrity_and_structure_verified",
        "counts": counts,
        "csv_structure_counts": dict(csv_counts),
        "document_quality_counts": dict(document_quality),
        "default_index_candidates": sum(d.eligible_for_default_index for d in corpus),
        "independent_label_review": "pending",
        "model_quality_metrics": "NOT_RUN",
        "java_integration": "NOT_RUN",
    }
