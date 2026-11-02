# V-Market AI Operations Copilot

Local, offline-first AI Operations Copilot for a **fictional Japanese retailer and synthetic suppliers**. Technical implementation and evidence through P16 include extractive QA, signed read-only tools, operator mapping/profile/preview/confirm handoff, durable runs, local Docker/outage drills and an English delivery pack. **Independent quality/customer acceptance remains partial:** the original mapping test achieved AI2/10 exact versus rules0/10. No production deployment, paid client, autonomous import or observed productivity ROI is claimed.

[Start the reviewer path](docs/delivery/technical-handoff.md#fresh-reviewer-path): fresh clone → fake mode → tests → retained evaluation → integrated local demo. Read the [delivery pack](docs/delivery/README.md), [actual UAT](docs/delivery/uat-and-acceptance.md), [honesty report](docs/delivery/honesty-report.md), [operations](docs/operations.md) and [runbooks](docs/runbooks.md).

```mermaid
flowchart LR
  Browser[Operator browser] --> BFF[Signed Next BFF]
  BFF --> Java[Java authorization / business workflow]
  BFF --> AI[Python read-only AI]
  AI --> Store[(Separate AI storage)]
  AI --> Local[Optional loopback Qwen / CPU E5]
```

Default service exposes only `/health`, `/ready` and `/openapi.json`. Optional [host-loopback QA](docs/qa.md) and [signed integration](docs/gateway.md) are explicit modes. The fake-only private Docker gateway requires trusted signing keys and exposes no unsigned business routes. Java remains authoritative for all business changes.

## Quickstart: fake mode, no API key

Requirements: Python 3.11-3.13. Verified locally on Python 3.12 / Windows and in Docker. Preserve any existing `.env`; copying `.env.example` is optional because defaults work without it.

```powershell
python -m pip install uv==0.13.6
python -m uv sync --locked
python -m uv run --frozen vmarket-ai migrate
python -m uv run --frozen vmarket-ai fake-check
python -m uv run --frozen vmarket-ai serve
```

Open [health](http://127.0.0.1:8090/health) and [readiness](http://127.0.0.1:8090/ready). Health reports process liveness. Readiness is 503 before AI migrations and 200 after the expected migration is present; it does not call an external model or claim RAG is ready.

Default storage is `.local/ai.db`, an AI-only SQLite database. `serve` uses loopback; direct overriding of Uvicorn/network settings is outside the supported local launcher. API docs expose no model keys. No business database, operator cookie or Java trust secret is used.

## Local chat on this Windows workstation

[Ollama setup, model comparison and limits](docs/local-llm.md). With the existing AI PostgreSQL corpus, pinned E5 bundle and installed model:

```powershell
powershell -NoProfile -File scripts/start-local-qa.ps1
```

This enables host-only QA and draft mapping on port **8091**, using `qwen3.5:4b-q4_K_M` with 4096 context, thinking disabled and one adapter request at a time. Defaults outside this launcher remain fake/QA-off. Local chat never calls a provider API or changes its budget ledger. The opt-in 9B alternative is selected with `-Model qwen3.5:9b-q4_K_M`.

## Checks

```powershell
python -m uv run --frozen ruff check src tests migrations tools/validate_contracts.py
python -m uv run --frozen ruff format --check src tests migrations tools/validate_contracts.py
python -m uv run --frozen mypy
python -m uv run --frozen pytest -q
python -m uv run --frozen python tools/validate_contracts.py
```

On systems with Make, `make install lint typecheck test contracts p13-check` runs the equivalents. Default pytest skips eight opt-in PostgreSQL tests; the recorded final clean run enables them. Provider tests use HTTPX mocks and block non-loopback sockets. Fake embeddings prove plumbing, not semantic quality. A Starlette/HTTPX TestClient deprecation remains visible. See [clean operations proof](docs/evidence/P15-clean-proof.json) and [final qualification](docs/evidence/P16.md).

## Standalone Docker: own PostgreSQL + pgvector

```powershell
docker compose config --quiet
docker compose up --build -d
```

The stack creates only AI resources: PostgreSQL on host loopback **5434**, API on loopback **8090**, separate schema `ai`, separate volume, migration owner and restricted application role. It does not join or modify V-Market storage. Public local-demo passwords in Compose are disposable development values, not production credentials. Provider keys are not passed into the containers and `.env` is excluded from build context.

`ai-migrate` runs once before `ai-api`. The image runs as UID/GID 10001. Application role can use AI tables but cannot create tables or edit the migration ledger. SQLite offline mode does not implement pgvector. Docker base tags are mutable; actual verification versions/digests are recorded in phase evidence.

To run the optional PostgreSQL test against this disposable stack:

```powershell
$env:AI_TEST_DATABASE_URL='postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai'
$env:AI_TEST_OWNER_DATABASE_URL='postgresql+psycopg://ai_owner:local-ai-owner-only@127.0.0.1:5434/vmarket_ai'
python -m uv run --frozen pytest -q -m postgres
```

Stop your own demo using `docker compose down`; data volume is retained. Do not point migration settings at a business database. Supported PostgreSQL database names are `vmarket_ai` or `vmarket_ai_test`.

## Providers and limits

Fake chat/embedding implementations and typed interfaces are in `src/vmarket_ai/`. The optional OpenRouter adapter supports only `openrouter/free`: explicit live opt-in, API key, positive finite request/day budgets, current zero-price catalog preflight, bounded response/time and an atomic persisted usage ledger are required. No live provider call was made for P03. Live chat is now available only through the opt-in P07 host-loopback QA route; see its documented blocked-ledger state.

See [provider safety and configuration](docs/providers.md). Unknown outcomes retain reservation and stop further live use for manual review; requests are never automatically retried or switched to a paid model. Application budgets cannot undo a provider charge; any unexpected reported cost is recorded and blocks further calls. P05 adds an optional pinned [local multilingual E5 embedding provider](docs/ingestion.md#local-real-embedding); it uses CPU inference without provider API keys. VyceAI is not a runtime adapter; the earlier connectivity script is retained separately.

## Status and evidence

- [P09 read-only gateway](docs/gateway.md): signed context/replay protection, bounded intent loop, feature-OFF Project2 BFF patch and real disposable OPERATOR tests. [Evidence](docs/evidence/P09.md).
- [P10a human confirmation recovery](docs/evidence/P10a.md): first increment with server receipt expiry, no automatic confirm retry, explicit Import runs inspection and fresh review; production browser checks and an incremental Project2 patch.
- [P10b signed mapping and human handoff](docs/evidence/P10b.md): current Java profile snapshots, manual edit/create inactive/activate, real browser lost202 recovery and DB rejection/idempotency checks. Completes the P10 technical increment; human acceptance remains pending.
- [P11 durable read-only runs](docs/runs.md): owner-bound checkpoints, current-auth resume, lease/revision fencing, uncertain-read abstention and TTL/owner retention. [Actual restart evidence](docs/evidence/P11.md).
- [P12 Operator Copilot](docs/operator-copilot.md): signed policy/source access, bounded investigation conversation, current-auth results and manual fallback. [Executed browser and real integration checks](docs/evidence/P12.md).
- [P13 technical evaluation](docs/evidence/P13.md): raw local mapping/QA/routing/retrieval comparisons, negative rerank result and failure-driven fix. Labels are provisional; independent holdout/human quality gates remain pending.
- [P14 scoped security closeout](docs/evidence/P14.md): job-ID provenance fix, final dependency audit0, both-repo regressions and real/mocked browser checks with explicit limits.
- [P15 local operations](docs/evidence/P15.md): resource-bounded Docker AI, signed integration, actual outage/manual fallback/restart and health load measurements.
- [P16 delivery/qualification](docs/delivery/README.md): English handoff, actual acceptance matrix, demo/FAQ/CV preparation, screenshot/evidence manifest and honest remaining gates.
- [P08 mapping drafts](docs/mapping.md): original-byte hash/storage, server-owned three-field policy, bounded local AI or exact header rules, provenance and profile differences. Human acceptance remains required; no profile/import write. [Evidence](docs/evidence/P08.md).
- [P07 extractive QA](docs/qa.md): English/Japanese live quote/citation smoke passed; full live baseline comparison remains partial. One real request is unsettled, so the provider ledger remains blocked. Fake mode and offline checks remain usable. [Evidence](docs/evidence/P07.md).

- [P06 retrieval](docs/retrieval.md): PostgreSQL lexical, exact pgvector dense and RRF hybrid; shared authorized corpus and [84 actual query-method evaluations](evals/retrieval/README.md). Dense was selected using dev only. Results use provisional labels; human review is pending. `make retrieval-eval-check` verifies saved metrics/hashes offline without rerunning model inference.
- [P05 ingestion](docs/ingestion.md): bounded TXT/Markdown/text-PDF/DOCX parsers, source citations, versioned chunks, real local E5/pgvector, collection grants and transactional update/delete tests. [Evidence](docs/evidence/P05.md) separates real inference from fake CI checks. Run `make ingestion-demo` or the documented Python CLI.
- [P04 synthetic dataset](data/README.md): 51 CSV /17 document fixtures, frozen splits, provisional mapping/relevance labels and strict byte/metadata QA. Independent human review is pending; no model quality is claimed. Run `python -m uv run --frozen python -m vmarket_ai.datasets.generate --check` or `make dataset-check`.
- [P03 evidence](docs/evidence/P03.md): executed commands, results, failures, limits and reproducibility.
- [Roadmap](docs/roadmap.md): P00-P16 dependencies/status; [fictional discovery](docs/fde/README.md).
- [Source-of-truth boundaries](docs/source-of-truth.md), [threat model](docs/threat-model.md), [design review](docs/design-review-checklist.md).
- [Historical provider connectivity](docs/provider-connectivity-2026-10-31.md): a dated API snapshot, not RAG/product evaluation.

Project2 has additive feature-OFF P09–P12 integration and a verified dependency-only P14 patch in local commits/reviewable patches. Its final local npm audit reports0; transitive major overrides require compatibility review on future updates. Original checkout stays unchanged; no Project2 remote push/merge/deploy. No independently validated answer quality or actual customer UAT is claimed.
