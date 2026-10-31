import csv
import io
import json
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pytest

from vmarket_ai.datasets.audit import MappingLabel, audit, records
from vmarket_ai.datasets.generate import DatasetError, digest, dump, render, write_snapshot
from vmarket_ai.datasets.quality import inspect_csv, inspect_text
from vmarket_ai.datasets.release import InputRecord, load_mapping_input, owned_path, verify_release

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/v1"
LOCK = ROOT / "data/releases/v1.lock.json"
SPEC = ROOT / "data/specs/v1.json"
INPUTS = records(DATA / "inputs.jsonl", InputRecord)
LABELS = {r.case_id: r for r in records(DATA / "labels/mapping.jsonl", MappingLabel)}


def candidate(tmp_path, tree):
    output = tmp_path / "release"
    write_snapshot(tree, output, False)
    lock = tmp_path / "test-only.lock.json"
    lock.write_bytes(
        dump(
            {
                "version": "v1",
                "manifest_sha256": digest(tree["manifest.json"]),
                "freeze_sha256": digest(tree["freeze.json"]),
                "independent_label_review": "pending",
            }
        )
    )
    return output, lock


def repack(tree):
    """Only for intentionally invalid temporary authoring candidates, never the real release."""
    manifest = json.loads(tree["manifest.json"])
    for item in manifest["artifacts"]:
        item.update(sha256=digest(tree[item["path"]]), bytes=len(tree[item["path"]]))
    tree["manifest.json"] = dump(manifest)
    frozen = json.loads(tree["freeze.json"])
    frozen.update(
        manifest_sha256=digest(tree["manifest.json"]),
        mapping_labels_sha256=digest(tree["labels/mapping.jsonl"]),
        relevance_labels_sha256=digest(tree["labels/relevance.jsonl"]),
    )
    tree["freeze.json"] = dump(frozen)
    return tree


def test_generator_reproduces_two_fresh_trees_and_committed_bytes(tmp_path):
    first, second = render(SPEC), render(SPEC)
    assert first == second
    assert write_snapshot(first, tmp_path / "one", False) == write_snapshot(
        second, tmp_path / "two", False
    )
    assert first == {
        p.relative_to(DATA).as_posix(): p.read_bytes() for p in DATA.rglob("*") if p.is_file()
    }
    assert write_snapshot(first, DATA, True)["files"] == 80


def test_locked_release_and_actual_inventory_counts():
    manifest = verify_release(DATA, LOCK)
    assert manifest.seed == 20261031
    report = audit(DATA, LOCK)
    assert report["counts"] == {
        "csv": 51,
        "documents": 17,
        "mapping_labels": 51,
        "relevance_labels": 28,
        "mapping_partitions": {"train": 8, "dev": 6, "test": 12, "regression": 25},
        "relevance_partitions": {"train": 8, "dev": 8, "test": 12},
    }
    assert report["independent_label_review"] == "pending"
    assert report["model_quality_metrics"] == "NOT_RUN"


@pytest.mark.parametrize("record", INPUTS, ids=lambda r: r.id)
def test_csv_structure_and_original_hash(record):
    raw = (DATA / record.path).read_bytes()
    before = digest(raw)
    result = inspect_csv(raw, record.declared_encoding)
    assert result.code == LABELS[record.id].expected_structure_code
    assert before == record.raw_sha256 == digest((DATA / record.path).read_bytes())


def test_cp932_roundtrip_is_strict_and_real_bytes_not_a_relabeled_utf8_file():
    valid = [
        r
        for r in INPUTS
        if r.declared_encoding == "CP932" and LABELS[r.id].expected_structure_code == "ok"
    ]
    assert valid
    for record in valid:
        raw = (DATA / record.path).read_bytes()
        assert raw.decode("cp932", errors="strict").encode("cp932", errors="strict") == raw
    raw = (DATA / "csv/regression/reg-a-original.csv").read_bytes()
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8", errors="strict")
    assert "商品コード" in raw.decode("cp932")


def test_unmappable_source_and_truncated_cp932_never_use_replacement():
    source = (DATA / "contexts/unmappable-cp932-source.txt").read_text(encoding="utf-8")
    with pytest.raises(UnicodeEncodeError):
        source.encode("cp932", errors="strict")
    with pytest.raises(UnicodeDecodeError):
        (DATA / "csv/regression/reg-a-truncated-cp932.csv").read_bytes().decode("cp932")


def test_global_raw_identity_examples_distinguish_copy_newlines_and_encoding():
    def read(name):
        return (DATA / f"csv/regression/{name}.csv").read_bytes()

    original, copy = read("reg-a-original"), read("reg-a-identical-copy")
    lf, utf8 = read("reg-a-lf"), read("reg-a-utf8-transcode")
    assert original == copy
    assert len({digest(original), digest(lf), digest(utf8)}) == 3
    assert original.decode("cp932").replace("\r\n", "\n") == lf.decode("cp932")
    assert original.decode("cp932") == utf8.decode("utf-8")


def test_header_variants_match_intended_fields_without_exposing_case_names():
    for record in INPUTS:
        if record.partition == "regression":
            continue
        raw = (DATA / record.path).read_bytes()
        rows = list(csv.reader(io.StringIO(raw.decode(record.declared_encoding), newline="")))
        assert record.id not in raw.decode(record.declared_encoding)
        assert not any(word in rows[1][1] for word in ["train", "test", "ambiguous", "dev"])
        mapping = LABELS[record.id].target_to_source
        if mapping:
            projected = {
                target: rows[1][rows[0].index(source)] for target, source in mapping.items()
            }
            assert projected["sku"] in {"VM-001", "VM-002"}
            assert 20 <= int(projected["on_hand"]) <= 80


def test_mapping_input_projection_excludes_gold_and_rejects_legacy_contract():
    item = load_mapping_input(DATA, LOCK, "map-b-test-reference-01")
    assert {f.name for f in fields(item)} == {
        "raw_bytes",
        "declared_encoding",
        "selected_vendor_code",
    }
    assert item.selected_vendor_code == "RIVERBYTE"
    for case_id in ["../../.env", "reg-legacy-stale-version"]:
        with pytest.raises(DatasetError):
            load_mapping_input(DATA, LOCK, case_id)


def test_stale_version_is_a_separate_legacy_precondition_not_a_mapping_target():
    record = next(r for r in INPUTS if r.id == "reg-legacy-stale-version")
    assert record.contract == "legacy_stock_v2"
    assert LABELS[record.id].target_to_source is None
    rows = list(csv.reader(io.StringIO((DATA / record.path).read_text(encoding="utf-8"))))
    assert rows[1][rows[0].index("expected_stock_version")] == "0"
    context = json.loads((DATA / "contexts/scenarios.json").read_bytes())
    assert context["legacy_stale_precondition"]["simulated_current_stock_version"] == 1
    assert context["runtime_database_observed"] is False


def test_rejected_documents_and_no_fabricated_ocr_confidence():
    corpus = [
        json.loads(line)
        for line in (DATA / "corpus.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for doc in corpus:
        actual = inspect_text((DATA / doc["path"]).read_bytes(), doc["media_type"])
        assert actual.extraction_confidence is None
        assert not actual.ocr_performed
        if (
            actual.status != "verified_text"
            or doc["trust_level"] == "untrusted_fixture"
            or doc["status"] == "retired"
        ):
            assert not doc["eligible_for_default_index"]
    assert sum(doc["eligible_for_default_index"] for doc in corpus) == 8


def test_label_authorship_is_honest_and_ja_queries_contain_japanese():
    for path in ["labels/mapping.jsonl", "labels/relevance.jsonl"]:
        for line in (DATA / path).read_text(encoding="utf-8").splitlines():
            label = json.loads(line)
            assert label["label_status"] == "provisional_agent_authored"
            assert label["independent_review"] == "pending" and label["rationale"]
    for line in (DATA / "queries.jsonl").read_text(encoding="utf-8").splitlines():
        query = json.loads(line)
        if query["language"] == "ja":
            assert any("\u3040" <= c <= "\u9fff" for c in query["question"])


def test_tampering_detected_and_generate_refuses_to_overwrite(tmp_path):
    tree = render(SPEC)
    root, lock = candidate(tmp_path, tree)
    path = root / "csv/test/map-a-test-reference-01.csv"
    path.write_bytes(path.read_bytes() + b"\n")
    changed = path.read_bytes()
    with pytest.raises(DatasetError, match="bytes changed"):
        verify_release(root, lock)
    with pytest.raises(DatasetError, match="never overwrite"):
        write_snapshot(tree, root, False)
    assert path.read_bytes() == changed


def test_cross_split_header_family_leak_detected_in_new_candidate(tmp_path):
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    spec["families"][4]["headers"] = spec["families"][0]["headers"]
    spec_path = tmp_path / "new-spec.json"
    spec_path.write_bytes(dump(spec))
    root, lock = candidate(tmp_path, render(spec_path))
    with pytest.raises(DatasetError, match="partition boundary"):
        audit(root, lock)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vmarket_ai.datasets.generate",
            "--check",
            "--spec",
            str(spec_path),
            "--output",
            str(root),
            "--lock",
            str(lock),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "partition boundary" in result.stderr
    assert "Traceback" not in result.stderr


def test_parse_failure_cannot_be_marked_indexable_even_with_consistent_candidate_hashes(tmp_path):
    tree = render(SPEC)
    docs = [json.loads(line) for line in tree["corpus.jsonl"].decode().splitlines()]
    next(d for d in docs if d["id"] == "empty.txt")["eligible_for_default_index"] = True
    tree["corpus.jsonl"] = b"".join(
        (json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n").encode() for d in docs
    )
    root, lock = candidate(tmp_path, repack(tree))
    with pytest.raises(DatasetError, match="Unparseable"):
        audit(root, lock)


def test_owned_paths_reject_traversal_and_absolute_files():
    for name in ["../.env", "/tmp/file", "..\\.env"]:
        with pytest.raises(DatasetError):
            owned_path(DATA, name)
