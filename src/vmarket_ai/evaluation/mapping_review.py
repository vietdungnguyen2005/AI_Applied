"""Prepare and verify a blind human review packet without model inference or label parsing."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from vmarket_ai.datasets.release import InputRecord, owned_path, verify_release

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/v1"
LOCK = ROOT / "data/releases/v1.lock.json"
PACKET = ROOT / "evals/p13/mapping-review-v1"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def input_records() -> list[InputRecord]:
    verify_release(DATA, LOCK)
    records = [
        InputRecord.model_validate_json(line)
        for line in (DATA / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    selected = [r for r in records if r.partition == "test" and r.contract == "supplier_three"]
    if len(selected) != 12 or len({r.raw_sha256 for r in selected}) != 12:
        raise ValueError("Expected 12 byte-distinct held-out inputs")
    return sorted(selected, key=lambda r: r.raw_sha256)


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def prepare(output: Path) -> None:
    if output.exists():
        raise ValueError("Review packet output must be a fresh directory")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise ValueError("Commit the packet generator before preparing its frozen output")
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    records = input_records()
    output.mkdir(parents=True)
    (output / "inputs").mkdir()
    registry, template = [], []
    for index, record in enumerate(records, 1):
        identifier = f"blind-{index:02d}"
        raw = owned_path(DATA, record.path).read_bytes()
        if digest(raw) != record.raw_sha256 or len(raw) != record.size_bytes:
            raise ValueError("Original input bytes differ from release")
        path = f"inputs/{identifier}.csv"
        (output / path).write_bytes(raw)
        registry.append(
            {
                "blind_id": identifier,
                "path": path,
                "raw_sha256": digest(raw),
                "size_bytes": len(raw),
                "declared_encoding": record.declared_encoding,
                "selected_vendor_code": record.selected_vendor_code,
            }
        )
        template.append(
            {
                "blind_id": identifier,
                "review_status": "PENDING_INDEPENDENT_REVIEW",
                "reviewer": None,
                "reviewed_at": None,
                "expected_decision": None,
                "target_to_original_header": None,
                "uncertainty_or_ambiguity": None,
                "notes": None,
            }
        )
    for name, content in (("inputs.jsonl", registry), ("review-template.jsonl", template)):
        (output / name).write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in content),
            encoding="utf-8",
            newline="\n",
        )
    files = [
        "inputs.jsonl",
        "review-template.jsonl",
        *[f"inputs/blind-{index:02d}.csv" for index in range(1, len(registry) + 1)],
    ]
    write_json(
        output / "lock.json",
        {
            "version": "p13-blind-mapping-review-v1",
            "cases": len(registry),
            "source_commit": source_commit,
            "generator_sha256_lf": digest(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
            "source_release_lock_sha256": digest(LOCK.read_bytes().replace(b"\r\n", b"\n")),
            "files_sha256": {name: digest((output / name).read_bytes()) for name in files},
            "review_status": "pending",
            "model_inference": "NOT_RUN",
        },
    )


def verify(packet: Path) -> None:
    records = input_records()
    lock = json.loads((packet / "lock.json").read_text(encoding="utf-8"))
    if (
        lock["cases"] != len(records)
        or lock["review_status"] != "pending"
        or lock["model_inference"] != "NOT_RUN"
    ):
        raise ValueError("Incorrect packet count or provenance")
    if lock["source_release_lock_sha256"] != digest(LOCK.read_bytes().replace(b"\r\n", b"\n")):
        raise ValueError("Source release lock changed")
    commit = lock["source_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid source revision")
    code = subprocess.check_output(
        ["git", "show", commit + ":src/vmarket_ai/evaluation/mapping_review.py"], cwd=ROOT
    )
    if digest(code) != lock["generator_sha256_lf"]:
        raise ValueError("Generator provenance changed")
    registry = [
        json.loads(line)
        for line in (packet / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    template = [
        json.loads(line)
        for line in (packet / "review-template.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    expected_files = {
        "inputs.jsonl",
        "review-template.jsonl",
        *[f"inputs/blind-{i:02d}.csv" for i in range(1, 13)],
    }
    if set(lock["files_sha256"]) != expected_files or len(registry) != 12 or len(template) != 12:
        raise ValueError("Packet inventory mismatch")
    for name, expected in lock["files_sha256"].items():
        path = (packet / name).resolve()
        if not path.is_relative_to(packet.resolve()) or digest(path.read_bytes()) != expected:
            raise ValueError("Packet bytes changed")
    for index, (row, review, record) in enumerate(zip(registry, template, records, strict=True), 1):
        identifier = f"blind-{index:02d}"
        expected = {
            "blind_id": identifier,
            "path": f"inputs/{identifier}.csv",
            "raw_sha256": record.raw_sha256,
            "size_bytes": record.size_bytes,
            "declared_encoding": record.declared_encoding,
            "selected_vendor_code": record.selected_vendor_code,
        }
        if (
            row != expected
            or review["blind_id"] != identifier
            or review["review_status"] != "PENDING_INDEPENDENT_REVIEW"
        ):
            raise ValueError("Blind input identity changed")
        if any(
            value is not None
            for key, value in review.items()
            if key not in {"blind_id", "review_status"}
        ):
            raise ValueError("Review template cannot claim human review")
    print(
        json.dumps(
            {
                "status": "PASS",
                "cases": len(records),
                "model_inference": "NOT_RUN",
                "review": "pending",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--path", type=Path, default=PACKET)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.path)
    verify(args.path)
