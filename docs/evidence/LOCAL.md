# Owner-requested local LLM extension

Date: 2026-11-01 Asia/Bangkok. Base: `3770a8d53ed701008e64f7ef3285d315f3951583` (P07). Owner approved local-model implementation after requesting documentation/community/hardware research. [Setup and comparison](../local-llm.md).

## Delivered and executed

- Added explicit `local` provider mode with fixed loopback Ollama, two allowed local Q4_K_M tags, per-call local/quantization preflight, no download/cloud fallback/auth header/proxy/redirect, bounded response and deadline, request serialization, strict completion metadata and safe errors. It does not instantiate OpenRouter or its budget ledger.
- Native JSON Schema constrains QA decisions, chunk IDs and whole-source quotes. Local decoding also enforces decision/claims consistency; server citation/current-grant/source validation remains authoritative. Default service remains fake/QA-off; host-only launcher enables real PostgreSQL/E5/local chat on 8091.
- Installed 4B/9B model artifacts on D via Ollama 0.32.1, with full digests in retained run reports. Never committed weights or changed `.env`. Existing Qwen2.5 artifacts retained. E5 remains CPU.
- Real RAG evaluation uses real AI PostgreSQL corpus, real CPU E5, actual Ollama and ASGI routes; [4B predictions](../../evals/local/runs/4b-v1/predictions.jsonl), [9B predictions](../../evals/local/runs/9b-v1/predictions.jsonl). Each has 4/4 expected QA decisions, 2/2 positive anchors and four successful citation opens. The conflict case is guarded before inference. Four standalone mapping probes each matched the provisional train/dev labels; this does not implement P08 or save profiles.
- Both models tied on this small known development set. 4B is selected for full GPU placement, 3.13 GB measured model VRAM and 0.934-second median mapping probes. 9B used partial CPU offload (12%/88% CPU/GPU observed in tool output) and 1.249 seconds. API `/api/ps` loaded states are retained in both summaries; an additional [after-unload snapshot](logs/LOCAL-after-unload.log) correctly shows no model loaded. Warm-up/cold-E5 differences preclude a cold-load speed comparison.
- [Actual TCP launcher smoke](LOCAL-tcp-smoke.json): `/health` 200, `/ready` local/ready, English real answer 200, current citation GET 200. It used port 8091, leaving the existing Docker/default 8090 service alone.

| Check | Actual result | Evidence |
| --- | --- | --- |
| Full offline pytest | 222 passed, 4 skipped | [captured result](logs/LOCAL-tests.log) |
| Provider/QA after lint-only restructuring | 53 passed, 1 PG skipped | [raw log](logs/LOCAL-final-provider-qa.log) |
| Real QA PostgreSQL/current citation test | 1 passed, 26 deselected | [raw log](logs/LOCAL-postgres.log) |
| Ruff / format / strict mypy | PASS / 59 formatted files / 41 source files | [lint](logs/LOCAL-lint.log), [format](logs/LOCAL-format.log), [types](logs/LOCAL-types.log) |
| Contract examples | 76/76 | [raw log](logs/LOCAL-contracts.log) |
| P04 / historical P06 | 80 frozen files byte-identical / 84 saved predictions validated | [dataset](logs/LOCAL-dataset.log), [retrieval](logs/LOCAL-retrieval.log) |

Default tests block non-loopback sockets and use HTTP mocks, never download weights or infer through an actual model. Four skipped tests are not counted as passed. Only the QA PostgreSQL test was run against the existing database; budget tests use fresh CI storage instead of resetting the real blocked ledger. Existing Starlette HTTPX deprecation warning remains visible. No new package or lockfile change.

## Failures, provenance and boundaries

Initial model pull failed transient DNS resolution; a later explicit artifact download succeeded. No inference or paid fallback was retried. Progress was observed in execution-tool output; no reconstructed raw DNS log is claimed. Initial final lint found three long literals and a nested async-context style issue, retained in [initial lint log](logs/LOCAL-lint-initial.log); these were fixed. The async contexts keep the same entry order/deadline and final provider/QA tests pass. One reporting helper initially used the Windows default text encoding and failed decoding Japanese; rerunning that helper with explicit UTF-8 succeeded without changing predictions. No model response failure occurred in the final retained 4B/9B runs.

Run reports record the parent checkout SHA because implementation changes were not committed during measurement. Final source blobs are identified by [manifest](LOCAL-manifest.json); adapter changes after comparison are formatting/context-manager restructuring only, and evaluation prompt strings retain identical values. The mapping probe supplies only vendor, exact source headers and two sample rows; gold is compared after inference. These are known train/dev cases, not independent gold or fresh unseen results. Semantic accuracy, citation relevance, injection resilience under real adversarial inference, large contexts/concurrency and human review remain unverified. P08 and later phases are not completed by this extension.

[Ledger snapshot](LOCAL-provider-ledger.json) shows the prior uncertain reservation/control still blocked. Its eight historical external inference rows match P07's retained final ledger exactly. Other pre-existing mock/test ledger rows are not external API calls. No OpenRouter/VyceAI inference, ledger repair or provider-charge claim was made here. [Environment](LOCAL-environment.json) and [publication check](LOCAL-publication-check.json) identify hardware, unchanged Project2 and secret/frozen-data checks. No Project2 edit, business mutation, production deployment or new external data disclosure. Remote CI status belongs to the actual pushed commit, not the earlier local test run.
