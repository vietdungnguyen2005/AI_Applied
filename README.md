# V-Market AI Operations Copilot

Local, offline-first Python service for a fictional Japanese retailer using synthetic suppliers. **Technical implementation through P11 includes extractive Q&A, signed mapping drafts, explicit human profile/preview/confirm handoff and durable read-only runs with real process-restart checks.** Model-quality evaluation and independent human acceptance remain partial. No production deployment or real customer outcome is claimed.

Default service exposes only `/health`, `/ready` and `/openapi.json`. P07 adds [opt-in host-loopback ask/citation routes](docs/qa.md). Future contracts are in [architecture](docs/architecture.md), and are separate from the runtime OpenAPI. Integrated mode fails closed until the authenticated BFF gateway is implemented.

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

On systems with Make, `make install lint typecheck test contracts` runs the equivalents. Default pytest skips seven explicit PostgreSQL tests; provider tests use HTTPX mocks and block non-loopback sockets. Fake embedding vectors prove deterministic plumbing only, not semantic retrieval quality. A Starlette compatibility deprecation for HTTPX TestClient is currently visible, not hidden. For the recorded clean Windows environment and NumPy setup, see [P05 reproduction](docs/ingestion.md#run-offline).

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
- [P08 mapping drafts](docs/mapping.md): original-byte hash/storage, server-owned three-field policy, bounded local AI or exact header rules, provenance and profile differences. Human acceptance remains required; no profile/import write. [Evidence](docs/evidence/P08.md).
- [P07 extractive QA](docs/qa.md): English/Japanese live quote/citation smoke passed; full live baseline comparison remains partial. One real request is unsettled, so the provider ledger remains blocked. Fake mode and offline checks remain usable. [Evidence](docs/evidence/P07.md).

- [P06 retrieval](docs/retrieval.md): PostgreSQL lexical, exact pgvector dense and RRF hybrid; shared authorized corpus and [84 actual query-method evaluations](evals/retrieval/README.md). Dense was selected using dev only. Results use provisional labels; human review is pending. `make retrieval-eval-check` verifies saved metrics/hashes offline without rerunning model inference.
- [P05 ingestion](docs/ingestion.md): bounded TXT/Markdown/text-PDF/DOCX parsers, source citations, versioned chunks, real local E5/pgvector, collection grants and transactional update/delete tests. [Evidence](docs/evidence/P05.md) separates real inference from fake CI checks. Run `make ingestion-demo` or the documented Python CLI.
- [P04 synthetic dataset](data/README.md): 51 CSV /17 document fixtures, frozen splits, provisional mapping/relevance labels and strict byte/metadata QA. Independent human review is pending; no model quality is claimed. Run `python -m uv run --frozen python -m vmarket_ai.datasets.generate --check` or `make dataset-check`.
- [P03 evidence](docs/evidence/P03.md): executed commands, results, failures, limits and reproducibility.
- [Roadmap](docs/roadmap.md): P00-P16 dependencies/status; [fictional discovery](docs/fde/README.md).
- [Source-of-truth boundaries](docs/source-of-truth.md), [threat model](docs/threat-model.md), [design review](docs/design-review-checklist.md).
- [Historical provider connectivity](docs/provider-connectivity-2026-10-31.md): a dated API snapshot, not RAG/product evaluation.

Project2 has additive feature-OFF P09–P11 integration in local commits/reviewable patches; Java/business code is unchanged. Its baseline dependency-audit advisories remain open; passing this Python service's tests does not resolve them. No AI-owned business write, independently validated answer quality, actual customer UAT or public production rollout is claimed.
