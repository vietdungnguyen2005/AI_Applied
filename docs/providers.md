# P03 provider configuration and safety

Fake chat produces a hash-labeled deterministic response without echoing a prompt. Fake embeddings produce normalized 32-dimensional hash vectors. Token counts are synthetic zero placeholders, not measured tokenizer statistics. Neither provider creates a network client or establishes model quality.

The optional live implementation is an internal library adapter, not a public endpoint. It supports only `openrouter/free` at the fixed official origin. `ChatRequest` cannot specify an API key, model, URL, tools or arbitrary headers. There is no live VyceAI/embedding adapter yet and no fallback to a paid model. Existing `.env` provider keys do not enable live use.

## Required live settings

| Setting | Default / behavior |
| --- | --- |
| AI_PROVIDER_MODE | fake; must explicitly be live |
| AI_LIVE_ENABLED | false; must explicitly be true |
| OPENROUTER_API | SecretStr, never rendered/logged |
| AI_LIVE_REQUEST_USD | 0; live requires positive cap <=1 USD |
| AI_LIVE_DAILY_USD | 0; positive cap >= request cap and <=10 USD |
| AI_LIVE_DAILY_REQUESTS | 10, bounded 1–100 |
| AI_PROVIDER_TIMEOUT_SECONDS | 5, bounded <=8 |
| AI_REQUEST_DEADLINE_SECONDS | 8, bounded <=30 |
| AI_DATABASE_URL | AI-only migrated storage; persistent ledger required |

Changing these settings alone does not initiate a provider call. Actual use requires an explicit programmatic `OpenRouterChatModel.complete` call; no live model call is included in quickstart/tests. Read the module and obtain an approved synthetic experiment/budget before later live quality evaluation. HTTP mock fixtures are marked synthetic and consume no external allowance.

## Enforcement and limitations

Each completion preflights the current catalog. The selected model must publish known zero prices for input/output and every supplied pricing field; unknown/positive/non-numeric fields fail closed. Unrelated models' pricing extensions do not affect the selected model. Fixed model/origin, redirect rejection, disabled environment proxies, identity content encoding, bounded body and explicit timeouts limit egress. Safe catalog GET may retry once; inference POST is sent at most once.

The AI ledger atomically reserves a finite request cap and counts an attempt before inference. A per-provider persisted control allows at most one unsettled reservation. A crash, timeout, malformed response, missing usage or uncertain charge leaves the grant reserved/blocked across process restart and day rollover until manual review. Known zero cost settles/reopens the grant; unexpected positive cost is recorded and blocks further calls. No automatic repair/reset command is provided. Inspect the AI-only provider_controls/provider_usage records and provider activity before any separately reviewed repair; never delete evidence to resume spend blindly.

The reservation is an application guard, not a hard vendor billing cap. A provider can misreport prices or charge unexpectedly; the application records observed cost and stops further calls but cannot refund/undo the original charge. No paid model or current-price assumption from a historical README is accepted. Failed attempts still count toward the configured request allowance; the provider's own quotas may differ.

Only usage metadata (IDs/state/tokens/cost) is persisted. Raw prompts, outputs, headers and API keys are not persisted in the ledger or request logs. Errors use static messages with suppressed sensitive exception context. Readiness validates migrated local storage, not provider connectivity or quota. No real provider response or budget behavior is claimed from tests using MockTransport.

## Host-local Ollama chat

`AI_PROVIDER_MODE=local` selects `OllamaChatModel` instead of the fake/OpenRouter adapter. See [local setup and measured comparison](local-llm.md). No cloud key, live opt-in or budget reservation is used. `AI_LIVE_ENABLED` must remain false. The existing real OpenRouter block remains in force.

Only `qwen3.5:4b-q4_K_M` and `qwen3.5:9b-q4_K_M` are accepted. Every call checks `/api/show` for Q4_K_M and rejects remote model aliases. Native `/api/chat` uses fixed `http://127.0.0.1:11434`, disabled environment proxies/redirects, a bounded response, JSON Schema, `think=false`, temperature 0.2, seed 42 and at most the requested output tokens. Missing models fail; the service never pulls them or falls back to cloud. Keep Ollama bound to loopback. This mode is host-only; private-container mode fails configuration validation.

The adapter serializes its own requests and includes queue time in its 25-second default timeout. The local launcher raises the total QA deadline to 30 seconds. Cold model loading can exceed these limits: warm the installed model first if needed. Runtime model tags are mutable; experiment reports record full digests, not an assertion that future pulls produce identical weights. Provider billed cost is zero for local inference; electricity/hardware costs are unmeasured. Existing quote/citation/current-access validators still apply. Schema-constrained output does not establish factual relevance.
