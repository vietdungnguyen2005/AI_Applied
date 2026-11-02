# P13 security and workflow regression measurement

Date: 2026-11-02 Asia/Bangkok. Source: `1f7e1f2` (full SHA in run config).
Windows, Python 3.12, real local PostgreSQL 17/pgvector in disposable Compose
project `p13-gates-20261102`.

All **33 collected pytest cases passed**, zero skipped, zero failures/errors.
[Artifacts](../../evals/p13/runs/security-workflow-v1/) retain actual JUnit,
per-case CSV, report and test/source hashes. Pytest duration was 3.52 seconds;
this is suite execution time, not request/model latency. No inference was called.

The existing tests cover signed request binding, atomic replay rejection,
scope expansion denial, untrusted tool/URL/job intent rejection, credential
separation, durable owner/revision binding, cancellation fencing, interrupted
reads becoming `OUTCOME_UNKNOWN` with handoff, duplicate record prevention,
expiry, actual PostgreSQL nonce/run-claim concurrency and source scope/deletion.
Parameterized cases count separately, not as independent users or attacks.

These are previously authored deterministic regressions, not blind held-out
labels, a penetration test, an LLM attack-resistance measurement or end-to-end
Java approval tests. Workflow tests include mock tool execution. PostgreSQL cases
use the real database; other fixtures use SQLite. P13 independent review and
matched ablations remain open; this result does not complete P14.

## Reproduction

Use the recorded source revision with locked dependencies and free local port
5434. These credentials are only the existing disposable Compose AI credentials.

```powershell
docker compose -p p13-gates-repeat up -d --wait ai-postgres
$env:AI_DATABASE_URL='postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai'
$env:AI_MIGRATION_DATABASE_URL='postgresql+psycopg://ai_owner:local-ai-owner-only@127.0.0.1:5434/vmarket_ai'
python -m uv run --frozen vmarket-ai migrate
$env:AI_TEST_DATABASE_URL=$env:AI_DATABASE_URL
$env:AI_TEST_OWNER_DATABASE_URL=$env:AI_MIGRATION_DATABASE_URL
python -m uv run --frozen pytest -q tests/test_gateway.py tests/test_runs.py tests/test_signed_qa_postgres.py --junitxml=.local/p13-gates-repeat.xml
python -m uv run --frozen python tools/p13_gate_report.py --junit .local/p13-gates-repeat.xml --output .local/p13-gates-repeat
docker compose -p p13-gates-repeat down
```

The report output directory must be new. Skips/errors/failures produce
`INCOMPLETE_OR_FAILED`; empty or duplicate observations are rejected.
The measured container/network was removed afterwards; its isolated volume
remains for inspection. Unrelated `valentina-postgres` stayed healthy.
