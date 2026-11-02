import importlib.util
from pathlib import Path

import pytest


def test_delivery_hash_tampering_is_detected():
    spec = importlib.util.spec_from_file_location(
        "delivery", Path(__file__).resolve().parents[1] / "tools/delivery_manifest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = module.snapshot()
    assert any(r["path"].endswith(".png") for r in value["files"])
    value["files"][0]["sha256_git_blob_bytes"] = "0" * 64
    with pytest.raises(ValueError, match="digest differs"):
        module.verify(value)
