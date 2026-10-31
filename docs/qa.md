# Evidence-constrained SOP question answering

P07 adds opt-in `POST /ai/ask` and `GET /ai/citations/{chunk_id}`. Default startup still exposes only health/readiness/OpenAPI. These routes are a **host-loopback synthetic demo**, with a fixed public demo actor and two supplier collections. They do not accept identity from JSON, cookies or headers. Integrated mode and signed BFF authentication remain disabled until P09. QA cannot be enabled in private-container/public-bind mode.

## Run fake chat with real local retrieval

Use the clean environment and real P04 corpus ingestion from [ingestion](ingestion.md). Keep the current local E5 index; fake chat does not require re-indexing documents as fake vectors.

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$PWD/.local/p05-env"
python -m uv sync --locked --extra local-embeddings
$env:AI_DATABASE_URL = 'postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai'
$env:AI_QA_ENABLED = 'true'
$env:AI_QA_EMBEDDING_MODE = 'local'
$env:AI_QA_MODEL_BUNDLE = "$PWD/.local/models/multilingual-e5-small"
$env:AI_PROVIDER_MODE = 'fake'
python -m uv run --frozen --extra local-embeddings vmarket-ai serve
```

Example body:

```json
{"question":"What encoding must the original RIVERBYTE supplier CSV use?","collection_ids":["4aa83e9f-0a0a-5558-8f5e-0f87db27c923"],"language":"en"}
```

Default fake chat always returns insufficient evidence. This is deterministic plumbing, not semantic QA. Tests inject explicitly scripted model completions for supported-answer and failure cases. Real PostgreSQL/local E5 plus fake chat was also exercised through actual loopback TCP HTTP: [four 200 abstentions](evidence/P07-fake-http-smoke.json), including the conflict guard, not four correct model answers.

Live additionally requires the existing explicit OpenRouter opt-in, key, finite positive request/day budgets and zero-price catalog preflight. Only `openrouter/free` is supported; no paid fallback. **Do not rerun live probes now:** the final P07 provider request is unsettled and the persisted real live ledger is blocked. [Usage state](evidence/P07-live-usage-final.json) records seven settled zero-cost requests and one unknown request with a 1,000-microusd reservation. No reset, retry or assumed refund was performed. Fake chat/local retrieval remain usable.

## Request and response

The request matches P02's question/collection_ids/language shape. Extra fields, empty question, duplicate scopes and malformed UUIDs fail with sanitized 400 errors that never echo bodies. Outside-demo collections fail 403. Multiple allowed collections produce `AMBIGUOUS_REQUEST` without retrieval/chat; choose one supplier. Foreign Host/Origin values are rejected. These are local-demo boundaries, not production authentication.

The response contains answered/abstained, reason, confidence, provider mode, request UUID and structured citations. P07 adds optional server-generated `Citation.source_url` and `AMBIGUOUS_REQUEST` to the shared contract. URLs are internal paths derived from validated chunk UUIDs; models cannot supply URLs. Citation GET repeats actor/scope/current-version/effective-date checks; stale/unauthorized chunks return 404. Historical P05 internal citation tooling remains separate.

Answers are **extractive quotes**, not model paraphrases/translations. The server checks supplied-context chunk ID, exact contiguous text bounded by sentence/line spans, and a freshly authorized unchanged current citation. It constructs the answer only from those quotes. Missing, altered, cut, forged or stale evidence fails closed. Sentence segmentation is a punctuation heuristic, not linguistic/NLI proof. Literal provenance does not establish source truth or semantic question relevance.

Confidence is `low` for extracts and `unknown` for abstention, never a calibrated probability or model self-assessment. English/Japanese questions are supported, while quoted text preserves the source language. Independent semantic/human review remains pending.

## Generation and failure handling

P06's selected dense config supplies top-five compatible current chunks. Server-owned supplier aliases accompany context so models can connect Supplier A/B to NAMI/RIVERBYTE without guessing. No labels, expected answers, partitions or supplied authority enter the prompt.

The fixed system message treats question/source content as untrusted data and permits no tools. Sources are JSON in a user message, never system/developer roles. Requests use `response_format=json_schema`, `require_parameters=true`, reasoning disabled and at most 512 output tokens. Available chunk IDs/quote spans are enumerated in the schema. Independent server validation remains necessary because [OpenRouter documents provider-dependent enforcement](https://github.com/OpenRouterTeam/docs/blob/main/guides/features/structured-outputs.mdx).

No evidence produces `NO_SUPPORTED_EVIDENCE` without chat. Differing current statements for the **top retrieved section topic** across documents trigger `CONFLICTING_EVIDENCE` with reauthorized references before chat. This conservative overlap guard can over-abstain and is not a general contradiction detector; other conflicts depend on model abstention/review. Retrieval/current checks exclude superseded, retired, untrusted and expired material. `OUTDATED_ONLY` is reserved; only-ineligible evidence currently gives no-supported-evidence.

Invalid model output returns 502, provider/storage/retrieval failures 503, deadlines 504 and budget denial 429. Evidence changes during generation return 409. No inference retry, JSON-repair call, paid fallback or streaming is implemented. UUID correlation/no-store headers persist; logs contain safe event/ID/mode/prompt-version/timing metadata, not question/source/key/exception text. Raw synthetic outputs are retained only by explicit development probes.

## Actual result and limits

The [final live transcript](evidence/P07-final-live-smoke.json) contains English UTF-8 and Japanese CP932 answers, exact quotes, routed model IDs and citation GET status 200. The unknown-tax case received 503/provider failure, not correct semantic abstention; the final conflict case was skipped after that error. The real-retrieval/fake-chat TCP demo separately exercised the conflict guard before chat.

Only one original prompt-only baseline case completed and abstained: 0/1 positive anchor passes, zero citations. Other baseline cases are NOT RUN. Earlier formatting/quote-validation failures and partial runs are preserved. Development debugging used these cases; free routing selected different models, so there is **no unseen-test or controlled causal improvement claim**.

[Evaluation summary](evidence/P07-evaluation-summary.json) records 2/2 final positive anchor passes and quote-supported answers/citation opens. These are small deterministic proxies, not human factual accuracy or semantic citation relevance. Both human measures are NOT RUN; independent review is pending; balanced four-case live baseline/RAG evaluation is **PARTIAL**. The P06 holdout remains consumed, with fresh reviewed data still required for later unseen-quality claims.
