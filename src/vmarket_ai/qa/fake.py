from decimal import Decimal

from vmarket_ai.contracts import ChatRequest, ChatResult


class FakeEvidenceModel:
    """Conservative deterministic API plumbing, never claimed as semantic QA."""

    async def complete(self, request: ChatRequest) -> ChatResult:
        return ChatResult(
            text='{"decision":"insufficient","claims":[]}',
            model="fake-evidence-abstain-v1",
            provider_mode="fake",
            prompt_tokens=0,
            completion_tokens=0,
            cost_usd=Decimal("0"),
        )
