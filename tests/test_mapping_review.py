import hashlib
import json
import shutil

import pytest

from vmarket_ai.evaluation.mapping_review import PACKET, verify


def test_frozen_packet_checks_original_bytes_without_model_inference():
    verify(PACKET)
    rows = [
        json.loads(line)
        for line in (PACKET / "inputs.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 12 and len({row["raw_sha256"] for row in rows}) == 12
    assert all(
        set(row)
        == {
            "blind_id",
            "path",
            "raw_sha256",
            "size_bytes",
            "declared_encoding",
            "selected_vendor_code",
        }
        for row in rows
    )


def test_changed_original_csv_byte_is_rejected(tmp_path):
    copy = tmp_path / "packet"
    shutil.copytree(PACKET, copy)
    with (copy / "inputs/blind-01.csv").open("ab") as handle:
        handle.write(b"x")
    with pytest.raises(ValueError, match="Packet bytes changed"):
        verify(copy)


def test_template_cannot_claim_a_review_even_when_its_hash_is_updated(tmp_path):
    copy = tmp_path / "packet"
    shutil.copytree(PACKET, copy)
    path = copy / "review-template.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    rows[0]["reviewer"] = "pretend-reviewer"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    lock_path = copy / "lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["files_sha256"]["review-template.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot claim human review"):
        verify(copy)
