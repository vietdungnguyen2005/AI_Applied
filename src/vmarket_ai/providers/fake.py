import hashlib
import math
from decimal import Decimal

from vmarket_ai.contracts import ChatRequest, ChatResult, EmbeddingRequest, EmbeddingResult


class FakeChatModel:
    async def complete(self, request: ChatRequest) -> ChatResult:
        digest = hashlib.sha256(request.model_dump_json().encode()).hexdigest()[:16]
        return ChatResult(
            text=f"FAKE_RESPONSE:{digest}",
            model="fake-sha256-v1",
            provider_mode="fake",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=Decimal("0"),
        )


class FakeEmbeddingProvider:
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        vectors = []
        for content in request.texts:
            digest = hashlib.sha256(content.encode()).digest()
            values = tuple((value - 127.5) / 127.5 for value in digest)
            norm = math.sqrt(sum(value * value for value in values))
            vectors.append(tuple(value / norm for value in values))
        return EmbeddingResult(vectors=tuple(vectors))
