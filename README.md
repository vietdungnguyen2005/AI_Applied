# V-Market AI Operations Copilot

Local, offline-first Python foundation for a fictional Japanese retailer using synthetic suppliers. **P03 foundation and P04 dataset tooling are implemented; RAG, CSV mapping, agent tools and V-Market integration are not implemented yet.** No production deployment or real customer outcome is claimed.

Current service exposes only `/health`, `/ready` and `/openapi.json`. Future contracts are in [architecture](docs/architecture.md), and are separate from the runtime OpenAPI. Integrated mode fails closed until the authenticated BFF gateway is implemented.

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

## Checks

```powershell
python -m uv run --frozen ruff check src tests migrations tools/validate_contracts.py
python -m uv run --frozen ruff format --check src tests migrations tools/validate_contracts.py
python -m uv run --frozen mypy
python -m uv run --frozen pytest -q
python -m uv run --frozen python tools/validate_contracts.py
```

On systems with Make, `make install lint typecheck test contracts` runs the equivalents. Default pytest skips the explicit PostgreSQL test; provider tests use HTTPX mocks and block non-loopback sockets. Fake embedding vectors prove deterministic plumbing only, not semantic retrieval quality. A Starlette compatibility deprecation for HTTPX TestClient is currently visible, not hidden.

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
python -m uv run --frozen pytest -q -m postgres
```

Stop your own demo using `docker compose down`; data volume is retained. Do not point migration settings at a business database. Supported PostgreSQL database names are `vmarket_ai` or `vmarket_ai_test`.

## Providers and limits

Fake chat/embedding implementations and typed interfaces are in `src/vmarket_ai/`. The optional OpenRouter adapter supports only `openrouter/free`: explicit live opt-in, API key, positive finite request/day budgets, current zero-price catalog preflight, bounded response/time and an atomic persisted usage ledger are required. No live provider call was made for P03. There is no live chat HTTP endpoint yet.

See [provider safety and configuration](docs/providers.md). Unknown outcomes retain reservation and stop further live use for manual review; requests are never automatically retried or switched to a paid model. Application budgets cannot undo a provider charge; any unexpected reported cost is recorded and blocks further calls. VyceAI and live embeddings are not runtime adapters in P03; the earlier connectivity script is retained separately.

## Status and evidence

- [P04 synthetic dataset](data/README.md): 51 CSV /17 document fixtures, frozen splits, provisional mapping/relevance labels and strict byte/metadata QA. Independent human review is pending; no model quality is claimed. Run `python -m uv run --frozen python -m vmarket_ai.datasets.generate --check` or `make dataset-check`.
- [P03 evidence](docs/evidence/P03.md): executed commands, results, failures, limits and reproducibility.
- [Roadmap](docs/roadmap.md): P00-P16 dependencies/status; [fictional discovery](docs/fde/README.md).
- [Source-of-truth boundaries](docs/source-of-truth.md), [threat model](docs/threat-model.md), [design review](docs/design-review-checklist.md).
- [Historical provider connectivity](docs/provider-connectivity-2026-10-31.md): a dated API snapshot, not RAG/product evaluation.

Project2 is unchanged in this phase. Its baseline dependency-audit advisories remain open; passing this Python service's tests does not resolve them. No AI-owned business write, integrated authentication, durable agent, document parser, retrieval index, actual customer UAT or public production rollout is claimed.
