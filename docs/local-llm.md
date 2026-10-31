# Local inference on the verified workstation

Selected default: **Qwen3.5 4B Q4_K_M through Ollama**. The 9B Q4_K_M tag is an explicit alternative. This implements local chat for P07 extractive QA. P08 now adds [mapping drafts](mapping.md), whose default uses exact rules after the larger comparison; the earlier eight-case local smoke below remains historical. No external provider inference was made for this extension.

## Hardware and measured development comparison

Verified 2026-11-01 Asia/Bangkok: i9-14900HX (24 cores/32 threads), 31.7 GiB RAM, RTX 5060 Laptop with 8151 MiB VRAM, driver 591.86, Windows, Ollama 0.32.1. Model artifacts are under `D:\Ollama_Model`, not Git. Existing Qwen2.5 7B/14B artifacts were retained. No runtime upgrade was performed.

| Measurement | Qwen3.5 4B Q4_K_M | Qwen3.5 9B Q4_K_M |
| --- | --- | --- |
| Downloaded artifact size | 3.32 GB | 6.55 GB |
| Ollama loaded memory / VRAM | 3.13 / 3.13 GB | 6.23 / 5.46 GB |
| Placement observed in `ollama ps` | 100% GPU | 12%/88% CPU/GPU |
| QA decisions | 4/4 | 4/4 |
| Positive answer anchor checks | 2/2 | 2/2 |
| Citation opens, including conflict sources | 4/4 | 4/4 |
| Mapping exact matches (standalone probes only) | 4/4 | 4/4 |
| Mapping median latency | 0.934 s | 1.249 s |
| Japanese positive QA latency | 1.294 s | 2.040 s |
| First English QA latency | 19.074 s | 2.231 s |
| Model-only warm-up | 23.577 s | 5.383 s |

Use decimal GB in this table. The first 4B QA includes cold CPU E5 setup; 9B ran second with warmed file caches. These measurements are not a controlled cold-load comparison. Conflict abstention is a deterministic server guard before inference, so 4/4 QA decisions do not mean four successful LLM calls. Latencies include retrieval and validation; this is not token-throughput measurement. No pressure/concurrency/long-context benchmark was run.

Results use four already-known P07 synthetic development questions and four P04 train/dev mapping cases. No fresh test split was consumed, no no-RAG baseline was run, and independent human review remains pending. Anchor checks/exact quotes do not establish semantic accuracy or citation relevance. Both models tied on this tiny set; 4B is selected for memory headroom and observed speed, not a claim of universal superiority. Raw outputs and full model digests: [4B](../evals/local/runs/4b-v1/summary.json), [9B](../evals/local/runs/9b-v1/summary.json).

## Run the existing local QA

Prerequisites on this workstation: AI-only PostgreSQL on loopback 5434 with migrations, P05/P06 indexed synthetic corpus and demo-reader grants; pinned CPU E5 bundle `.local/models/multilingual-e5-small`; Python environment `.local/p05-env` with `local-embeddings`; Ollama on `127.0.0.1:11434` with the selected model installed. The launcher does not provision a fresh corpus. See [ingestion](ingestion.md) and [retrieval](retrieval.md) for those steps.

```powershell
# Only when model artifacts are missing (downloads require internet):
D:\Ollama\ollama.exe pull qwen3.5:4b-q4_K_M
# From the repository, using the existing prepared environment:
powershell -NoProfile -File scripts/start-local-qa.ps1
# Alternative, after explicitly pulling the 9B model:
powershell -NoProfile -File scripts/start-local-qa.ps1 -Model qwen3.5:9b-q4_K_M
```

The launcher now enables both QA and draft mapping. Launcher runs in the foreground on port 8091; Ctrl+C stops it. It temporarily sets process environment and restores it on exit, preserving `.env`. If `AI_DATABASE_URL` is already set, that AI-only PostgreSQL URL is used. The default fake/QA-off service on 8090 is separate.

```powershell
$body = @{
  question = 'What original encoding does RIVERBYTE supply?'
  collection_ids = @('4aa83e9f-0a0a-5558-8f5e-0f87db27c923')
  language = 'en'
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8091/ai/ask -Method Post -ContentType application/json -Body $body
```

Readiness reports storage/mode, not model availability. Missing/stopped Ollama returns a safe provider error; there is no automatic download, inference retry or cloud fallback. A cold model may exceed the 25-second provider deadline; warm it explicitly (`ollama run qwen3.5:4b-q4_K_M`) and exit its interactive prompt before QA. Keep context 4096 initially, thinking off, temperature 0.2, seed 42 and QA output cap 512. E5 stays on CPU. Only one request per adapter runs at a time. Ollama can still have independent clients; do not run competing models while comparing.

To reproduce the small probe, set the launcher's environment in a separate shell and run:

```powershell
python -m uv run --frozen --offline --extra local-embeddings python -m vmarket_ai.local_evaluation --output .local/local-repeat --models qwen3.5:4b-q4_K_M
```

The output directory must be fresh. Models must already be installed. Reports call the external-provider counter `provider_api_calls`; this is zero external calls, not zero local inference requests. Source parent SHA records the checkout before the extension commit; [implementation manifest](evidence/LOCAL-manifest.json) records the final Git blobs.

## Documentation and community used in selection

[Qwen official 4B model card](https://huggingface.co/Qwen/Qwen3.5-4B) describes the multilingual model and Apache 2.0 license. [Ollama 4B Q4_K_M](https://ollama.com/library/qwen3.5:4b-q4_K_M) and [9B Q4_K_M](https://ollama.com/library/qwen3.5:9b-q4_K_M) provide the quantized distributions. Native [structured output](https://docs.ollama.com/capabilities/structured-outputs), [thinking controls](https://docs.ollama.com/capabilities/thinking) and [context memory guidance](https://docs.ollama.com/context-length) informed the bounded configuration.

Community reports vary by task and runtime: [4B structured-output anecdote](https://www.reddit.com/r/LocalLLaMA/comments/1rl1j07/yet_another_post_of_genuinely_impressed_with/), [same 5060 Laptop 8GB issue discussing 4B/9B limitations](https://github.com/astragenie/astramem-local/issues/434), and [9B on 5060 8GB with llama.cpp tuning](https://www.reddit.com/r/LocalLLM/comments/1ui1pj8/qwen359b_on_rtx_5060_8gb_vram_the_llamacpp/). These are anecdotes, not acceptance evidence. Our own measured placement and development probes determine the default above. Existing 14B is not selected for an 8GB GPU; 4B Q8 was considered but not benchmarked/downloaded.

The provider's token/request quota no longer constrains local chat. GPU memory, context size, latency and thermal/power limits still apply. Electricity/hardware cost is not measured. OpenRouter's prior uncertain reservation stays blocked and is not reconciled by enabling local inference.
