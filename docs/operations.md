# Local operations and support contract

This is a synthetic local portfolio system, not a hosted production service.
Python owns only AI storage. Java owns business truth and OPERATOR/CSRF approval.
Keep normal V-Market operations usable when the AI process, model or index fails.

## Supported modes

1. **Standalone fake, no credentials:** `uv sync --locked`, `uv run vmarket-ai
   migrate`, `uv run vmarket-ai fake-check`, `uv run vmarket-ai serve`. SQLite
   belongs only to AI. Docker equivalent: `docker compose up --build -d --wait`.
   Docker API publishes only `127.0.0.1:8090`, uses separate PG and migration owner.
2. **Integrated fake Docker AI:** build `docker build -t vmarket-ai:p15-local .`,
   then run `uv run python tools/p15_integrated.py --project2 <prepared-Project2>
   --output <fresh-report.json>`. The command owns disposable Docker AI/PG/Redis,
   real host Java/Next processes and ephemeral signing keys. It verifies actual
   login, signed read, denial, outage/manual fallback and durable restart, then
   cleans owned resources. Java/Next run on the host; this is not an all-app
   container deployment. No local model or external provider is used in this mode.
3. **Integrated semantic host mode:** `tools/p14_local_acceptance.py` uses the
   current built Project2, Docker databases, pinned CPU E5 and existing loopback
   Ollama 4B. Run Ollama locally first. It invokes the local model, signed sources
   and browser, plus separately labeled mocked browser faults. No model download
   or cloud fallback. Keep this mode host-loopback.

Do not load production data or publish these local Compose services publicly.
`AI_SIGNED_CONTAINER=true` is accepted only for integrated/private, fake
read-only mode with valid trusted Ed25519 keys and 0.0.0.0 container bind. It
does not enable unsigned QA/mapping/demo routes; missing signatures return 401.
The host publication remains loopback. The custom Docker bridge is not an egress
firewall: application transport restrictions and absent provider keys remain
required. Local Ollama/live modes are rejected in this container configuration.

## Budgets and failure behavior

| Resource | Enforced boundary / operational meaning |
| --- | --- |
| Standalone/Docker AI | 1 CPU, 512 MiB, 128 pids, read-only root, 64 MiB noexec tmp, dropped caps/no-new-privileges |
| Integrated Docker AI | 1 CPU, 512 MiB, read-only root/tmp and dropped caps; dedicated bridge and restricted app DB role |
| Generation | Qwen4B, 4096 context, seed42/temp0.2, thinking off; one local adapter slot, bounded 25-second timeout; endpoints bounded <=30 sec |
| Workflows | At most three read steps; owner-bound revisions/leases; explicit cancel and OUTCOME_UNKNOWN; active/TTL quotas in RunStore |
| Documents/CSV | Parser byte/page/memory/timeout limits, fixed 320/48 chunks; CSV bounds in mapping contract; no automatic encoding repair |
| External provider | OFF by default; explicit opt-in, current free catalog and finite ledger budgets required; current uncertain ledger remains blocked |
| POST retries | No automatic inference/business retry; redirects are refused; safe catalog GET retry is bounded |

429 means stop/slow down, inspect the error/correlation ID and budget, not switch
to another paid model. A timeout/unknown usage keeps the ledger reservation and
blocks further live calls. Cancellation joins in-flight work, but cannot undo a
provider charge or previously accepted Java operation. Never reset the blocked
ledger merely to rerun a demo. Local model outages offer manual fallback.

## Observability

Python JSON logs project only route template, status, elapsed time and request ID;
no raw question/source/body/header/token text by default. BFF propagates the
correlation ID across its Python/Java requests. AI-only audit retains bounded
metadata. OpenTelemetry/centralized dashboards are not installed or claimed.

`uv run python tools/ops_probe.py --base http://127.0.0.1:8090 --requests 100
--concurrency 4 --output .local/health-load.json` measures health/readiness
error rate, p50/p95 and correlation echo. Bounds: 1000 requests, concurrency16;
loopback HTTP only, no application payload/model invocation. Do not confuse
health readiness with model quality or index currency.

`uv run python tools/ops_report.py --report evals/p13/runs/completion-v1/report.json
--output .local/eval-ops.json` summarizes recorded request errors, quality proxies,
latency, tokens and returned cost observations. Missing cost is null, not free;
abstention success is separate from semantic exactness. Retained eval reports
also expose retrieval Recall/MRR. These are scripts, not a live telemetry store.

## Maintenance and incident ownership

The repository owner operates local services and decides business actions;
engineering handles code/index/model incidents. Start with [runbooks](runbooks.md).
Escalate a correlation ID, mode, versions, safe error code and reproduction;
exclude original files, cookies, API keys, signing keys, CSRF and raw logs until
sanitized. Disable AI flags while business integrity is in doubt. A critical
business invariant failure blocks release; never repair business rows with AI SQL.

No retention/availability/commercial SLA is promised. Default run payload TTL is
600 seconds with bounded owner maintenance; source/draft retention is operator
managed. Back up AI schema and immutable originals before maintenance. Rebuild
embeddings under a new fingerprint and verified ACL; never mix dimensions or
silently point the AI migration URL at Java storage.
