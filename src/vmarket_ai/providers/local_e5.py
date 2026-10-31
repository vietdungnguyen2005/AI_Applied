"""Opt-in CPU inference from a pinned, already downloaded local ONNX bundle."""

import asyncio
import hashlib
import importlib
import json
from pathlib import Path

import numpy as np

from vmarket_ai.contracts import EmbeddingRequest, EmbeddingResult
from vmarket_ai.ingestion.spec import E5_MODEL, E5_REPO, E5_REVISION, IngestionError

FILES = ("onnx/model.onnx", "onnx/tokenizer.json")
PINNED_HASHES = {
    "onnx/model.onnx": "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665",
    "onnx/tokenizer.json": "0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39",
}


class LocalE5EmbeddingProvider:
    def __init__(self, bundle: Path) -> None:
        try:
            manifest = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
            if (
                manifest["repo"] != E5_REPO
                or manifest["revision"] != E5_REVISION
                or manifest["files"] != PINNED_HASHES
            ):
                raise ValueError("Unregistered bundle")
            for name in FILES:
                path = bundle / name
                if path.is_symlink() or not path.resolve().is_relative_to(bundle.resolve()):
                    raise ValueError("Unsafe bundle path")
                hasher = hashlib.sha256()
                with path.open("rb") as handle:
                    while block := handle.read(1024 * 1024):
                        hasher.update(block)
                if hasher.hexdigest() != manifest["files"][name]:
                    raise ValueError("Bundle checksum mismatch")
            ort = importlib.import_module("onnxruntime")
            tokenizers = importlib.import_module("tokenizers")
            self.tokenizer = tokenizers.Tokenizer.from_file(str(bundle / FILES[1]))
            self.tokenizer.no_truncation()
            self.tokenizer.enable_padding()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(
                str(bundle / FILES[0]), sess_options=options, providers=["CPUExecutionProvider"]
            )
        except Exception:
            raise IngestionError("local_embedding_bundle_unavailable") from None

    def _encode(self, texts: tuple[str, ...], prefix: str) -> EmbeddingResult:
        encoded = self.tokenizer.encode_batch([prefix + text for text in texts])
        if any(len(e.ids) > 512 for e in encoded):
            # Reject rather than silently truncate source/query meaning.
            raise IngestionError("embedding_token_limit")
        ids = np.asarray([e.ids for e in encoded], dtype=np.int64)
        mask = np.asarray([e.attention_mask for e in encoded], dtype=np.int64)
        types = np.asarray([e.type_ids for e in encoded], dtype=np.int64)
        feed = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
        selected = {i.name: feed[i.name] for i in self.session.get_inputs()}
        hidden = self.session.run(None, selected)[0]
        weights = mask[..., None]
        pooled = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
        normalized = pooled / np.linalg.norm(pooled, axis=1, keepdims=True)
        vectors = tuple(tuple(float(v) for v in row) for row in normalized)
        if any(len(row) != 384 or not all(np.isfinite(v) for v in row) for row in vectors):
            raise IngestionError("invalid_embedding")
        return EmbeddingResult(
            vectors=vectors, model=E5_MODEL, dimensions=384, provider_mode="local"
        )

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return await asyncio.to_thread(self._encode, request.texts, "passage: ")

    async def embed_queries(self, request: EmbeddingRequest) -> EmbeddingResult:
        return await asyncio.to_thread(self._encode, request.texts, "query: ")
