"""Git-blob SHA-256 inventory for a specific snapshot; not a signature or live HEAD claim."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "docs/delivery/evidence-manifest.json"


def blob_hashes(objects):
    result = subprocess.check_output(
        ["git", "cat-file", "--batch"], input=("\n".join(objects) + "\n").encode(), cwd=ROOT
    )
    offset = 0
    hashes = []
    for oid in objects:
        end = result.index(b"\n", offset)
        actual, kind, size = result[offset:end].split()
        if actual.decode() != oid or kind != b"blob":
            raise ValueError("Unexpected Git object")
        start = end + 1
        finish = start + int(size)
        hashes.append(hashlib.sha256(result[start:finish]).hexdigest())
        offset = finish + 1
    return hashes


def snapshot():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(["git", "ls-tree", "-rz", "HEAD"], cwd=ROOT)
    records = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        header, path_bytes = entry.split(b"\t", 1)
        _, kind, oid = header.decode().split()
        path = path_bytes.decode("utf-8")
        if path == MANIFEST or kind != "blob":
            continue
        name = Path(path).name
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            raise ValueError("Private environment file cannot be delivered")
        records.append(
            {
                "path": path,
                "git_blob": oid,
                "url": f"https://github.com/vietdungnguyen2005/AI_Applied/blob/{commit}/{quote(path)}",
            }
        )
    for row, digest in zip(records, blob_hashes([r["git_blob"] for r in records]), strict=True):
        row["sha256_git_blob_bytes"] = digest
    return {
        "source_commit": commit,
        "scope": "specific committed snapshot; Git consistency, not independent attestation",
        "commands": [
            "make lint typecheck test contracts dataset-check p13-check",
            "docker compose up --build -d --wait",
            "uv run python tools/p15_integrated.py --project2 <path> --output <fresh-report>",
            "uv run python tools/delivery_manifest.py --check",
        ],
        "files": records,
    }


def verify(value):
    commit = value["source_commit"]
    tree = subprocess.check_output(["git", "ls-tree", "-rz", commit], cwd=ROOT)
    expected = {}
    for entry in tree.split(b"\0"):
        if entry:
            header, path = entry.split(b"\t", 1)
            _, kind, oid = header.decode().split()
            if kind == "blob" and path.decode() != MANIFEST:
                expected[path.decode()] = oid
    actual = {r["path"]: r["git_blob"] for r in value["files"]}
    if actual != expected or len(actual) != len(value["files"]):
        raise ValueError("Historical path/blob inventory differs")
    if any(
        r["url"]
        != f"https://github.com/vietdungnguyen2005/AI_Applied/blob/{commit}/{quote(r['path'])}"
        for r in value["files"]
    ):
        raise ValueError("Source link differs")
    hashes = blob_hashes([r["git_blob"] for r in value["files"]])
    if hashes != [r["sha256_git_blob_bytes"] for r in value["files"]]:
        raise ValueError("Delivery blob digest differs")
    print(json.dumps({"status": "PASS", "source_commit": commit, "files": len(hashes)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    path = ROOT / MANIFEST
    if args.check:
        verify(json.loads(path.read_text(encoding="utf-8")))
    else:
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
            raise ValueError("Commit the complete delivery snapshot before generating its manifest")
        value = snapshot()
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
        verify(value)
