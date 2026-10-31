"""Offline verification of retained P08 runs, including source and original-byte provenance."""

import hashlib
import json
import statistics
import subprocess
from pathlib import Path

from vmarket_ai.datasets.release import load_mapping_input, verify_release
from vmarket_ai.mapping.csv_input import parse_original
from vmarket_ai.mapping.spec import MappingResponse


def verify(directory: Path) -> dict[str, object]:
    config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
    report = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    raw = (directory / "predictions.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == report["predictions_sha256"]
    for path, expected in config["implementation_sha256_lf"].items():
        source = subprocess.check_output(["git", "show", config["git_commit"] + ":" + path])
        assert hashlib.sha256(source.replace(b"\r\n", b"\n")).hexdigest() == expected
    root, lock = Path("data/v1"), Path("data/releases/v1.lock.json")
    verify_release(root, lock)
    label_raw = (root / "labels/mapping.jsonl").read_bytes()
    assert hashlib.sha256(label_raw).hexdigest() == config["labels_sha256"]
    gold = {r["case_id"]: r for r in map(json.loads, label_raw.splitlines())}
    rows = list(map(json.loads, raw.splitlines()))
    assert {(r["case_id"], r["method"]) for r in rows} == {
        (case, method) for case in config["case_ids"] for method in ("rule", "ai")
    }
    assert len(rows) == 2 * len(config["case_ids"])
    checked_outputs = 0
    for row in rows:
        assert row["partition"] != "test" and gold[row["case_id"]]["partition"] != "test"
        original = load_mapping_input(root, lock, row["case_id"])
        predicted = {}
        if "response" in row:
            result = MappingResponse.model_validate(row["response"])
            assert result.raw_sha256 == hashlib.sha256(original.raw_bytes).hexdigest()
            assert result.selected_vendor_code == original.selected_vendor_code
            assert result.declared_encoding == original.declared_encoding
            parsed = parse_original(original.raw_bytes, original.declared_encoding)
            predicted = {a.target_field: a.source_header for a in result.assignments}
            assert set(predicted.values()).issubset(parsed.headers)
            assert set(result.unmapped_headers) == set(parsed.headers) - set(predicted.values())
            checked_outputs += 1
        target = gold[row["case_id"]]["target_to_source"]
        assert row["exact_mapping"] == (predicted == target if target is not None else None)
        assert row["required_field_coverage"] == len(predicted) / 3
        assert row["required_field_edits_proxy"] == (
            sum(predicted.get(t) != h for t, h in target.items()) if target is not None else None
        )
    for key, saved in report["summary"].items():
        method, supplier = key.split("/")
        group = [
            r
            for r in rows
            if r["method"] == method and (supplier == "all" or r["fixture_supplier"] == supplier)
        ]
        eligible = [r for r in group if r["exact_mapping"] is not None]
        assert saved["cases"] == len(group)
        assert saved["mapping_labeled_cases"] == len(eligible)
        assert saved["exact_mapping_correct"] == sum(r["exact_mapping"] for r in eligible)
        assert saved["required_field_edits_proxy"] == sum(
            r["required_field_edits_proxy"] for r in eligible
        )
        assert saved["required_field_coverage_mean"] == statistics.mean(
            r["required_field_coverage"] for r in eligible
        )
        assert saved["abstained"] == sum(r["status"] == "abstained" for r in group)
        assert saved["input_rejected"] == sum(r["status"] == "input_error" for r in group)
        assert saved["model_output_rejected"] == sum(r["model_output_rejected"] for r in group)
        assert saved["p50_ms"] == statistics.median(r["latency_ms"] for r in group)
    assert report["local_adapter_attempts"] == sum(r["adapter_attempts"] for r in rows)
    return {
        "run": directory.name,
        "predictions": len(rows),
        "validated_draft_outputs": checked_outputs,
        "invalid_published_suggestions": 0,
        "invalid_published_rate": 0.0,
        "meaning": "structural/source-header validity only, not semantic correctness",
        "heldout_inference": "NOT_RUN",
    }


if __name__ == "__main__":
    for directory in sorted(Path("evals/mapping/runs").iterdir()):
        print(json.dumps(verify(directory)))
