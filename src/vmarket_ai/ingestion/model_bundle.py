"""Explicit public model download only; runtime inference never downloads anything."""

import argparse
import hashlib
import importlib
import json
import shutil
from pathlib import Path

from vmarket_ai.ingestion.spec import E5_REPO, E5_REVISION
from vmarket_ai.providers.local_e5 import FILES, PINNED_HASHES


def download(output: Path) -> None:
    if output.exists():
        raise ValueError("Destination must be new; preserve any existing bundle")
    hub = importlib.import_module("huggingface_hub")
    files = {}
    for name in FILES:
        source = Path(
            hub.hf_hub_download(repo_id=E5_REPO, revision=E5_REVISION, filename=name, token=False)
        )
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
        files[name] = digest.hexdigest()
        if files[name] != PINNED_HASHES[name]:
            raise ValueError("Pinned model checksum mismatch; bundle was not published")
    manifest = {
        "repo": E5_REPO,
        "revision": E5_REVISION,
        "files": files,
        "license": "MIT",
        "dimensions": 384,
        "pooling": "attention-mask-mean-l2",
        "prefixes": {"document": "passage: ", "query": "query: "},
    }
    (output / "bundle.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download pinned public E5 ONNX files, no API key")
    parser.add_argument("output", type=Path)
    download(parser.parse_args().output)
