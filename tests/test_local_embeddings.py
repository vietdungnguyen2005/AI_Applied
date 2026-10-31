import json

import numpy as np
import pytest

from vmarket_ai.contracts import EmbeddingRequest
from vmarket_ai.ingestion.spec import E5_REPO, E5_REVISION, IngestionError
from vmarket_ai.providers.local_e5 import PINNED_HASHES, LocalE5EmbeddingProvider


class Encoding:
    def __init__(self, ids):
        self.ids = ids
        self.attention_mask = [1] + [0] * (len(ids) - 1)
        self.type_ids = [0] * len(ids)


class Tokenizer:
    def __init__(self):
        self.inputs = []

    def encode_batch(self, texts):
        self.inputs = texts
        return [Encoding([1, 2]) for _ in texts]


class Session:
    def get_inputs(self):
        return [type("Input", (), {"name": n}) for n in ("input_ids", "attention_mask")]

    def run(self, _, feed):
        result = np.zeros((len(feed["input_ids"]), 2, 384))
        result[:, 0, 0] = 3
        result[:, 0, 1] = 4
        result[:, 1, 5] = 999  # Must be masked out of mean pooling.
        return [result]


async def test_masked_mean_normalization_and_task_prefixes():
    # Unit test numerical adapter behavior; not a real-model quality test.
    provider = LocalE5EmbeddingProvider.__new__(LocalE5EmbeddingProvider)
    provider.tokenizer = Tokenizer()
    provider.session = Session()
    request = EmbeddingRequest(texts=("日本語", "English"))
    output = await provider.embed(request)
    assert provider.tokenizer.inputs == ["passage: 日本語", "passage: English"]
    assert output.dimensions == 384 and output.provider_mode == "local"
    assert output.vectors[0][:2] == (0.6, 0.8)
    assert output.vectors[0][5] == 0
    await provider.embed_queries(request)
    assert provider.tokenizer.inputs == ["query: 日本語", "query: English"]


async def test_oversized_token_input_rejected_without_truncation():
    provider = LocalE5EmbeddingProvider.__new__(LocalE5EmbeddingProvider)
    provider.tokenizer = type(
        "TooLong", (), {"encode_batch": lambda self, texts: [Encoding([1] * 513)]}
    )()
    provider.session = Session()
    with pytest.raises(IngestionError, match="embedding_token_limit"):
        await provider.embed(EmbeddingRequest(texts=("long",)))


def test_modified_or_self_declared_model_bundle_rejected(tmp_path):
    (tmp_path / "onnx").mkdir()
    for name in PINNED_HASHES:
        (tmp_path / name).write_bytes(b"substituted-model")
    manifest = {"repo": E5_REPO, "revision": E5_REVISION, "files": PINNED_HASHES}
    (tmp_path / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IngestionError, match="local_embedding_bundle_unavailable"):
        LocalE5EmbeddingProvider(tmp_path)
    manifest["revision"] = "unreviewed"
    (tmp_path / "bundle.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IngestionError, match="local_embedding_bundle_unavailable"):
        LocalE5EmbeddingProvider(tmp_path)
