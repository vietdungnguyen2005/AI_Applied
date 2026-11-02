"""Verify retained P13 report, input bytes, and recorded implementation provenance."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "evals/p13/runs/retrospective-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(run: Path, comparison: Path | None = None) -> None:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    if set(manifest["files_sha256"]) != {"config.json", "predictions.jsonl", "summary.csv"}:
        raise ValueError("Unexpected report file set")
    for name, expected in manifest["files_sha256"].items():
        if sha((run / name).read_bytes()) != expected:
            raise ValueError("Report bytes changed: " + name)
    config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    commit = config["source_commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid source revision")
    code = subprocess.check_output(
        ["git", "show", commit + ":src/vmarket_ai/evaluation/regression.py"], cwd=ROOT
    )
    if sha(code) != config["implementation_sha256"]:
        raise ValueError("Recorded implementation hash changed")
    for name, expected in config["input_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != expected:
            raise ValueError("Input missing, outside repository, or changed: " + name)
    predictions = (run / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
    if len(predictions) != manifest["records"]:
        raise ValueError("Prediction count changed")
    for line in predictions:
        json.loads(line)
    if comparison is not None:
        for name in ("predictions.jsonl", "summary.csv"):
            if (run / name).read_bytes() != (comparison / name).read_bytes():
                raise ValueError("Regenerated results differ: " + name)
    print(json.dumps({"status": "PASS", "records": len(predictions), "source_commit": commit}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare", type=Path, help="Freshly regenerated output directory")
    verify(RUN, parser.parse_args().compare)
