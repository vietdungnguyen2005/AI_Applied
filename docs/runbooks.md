# Operator runbooks — local synthetic environment

Use only resources started for this project. Check resolved names/ports before
stopping a service; never use broad Docker prune/volume deletion or process-name
kills. AI rollback means feature flags and service rollback, not reversing business
effects. Keep API/DB/signing secrets out of tickets and copied commands.

| Incident | Triage and bounded action | Verification / escalation |
| --- | --- | --- |
| AI service unavailable | Check `/health` then `/ready`, record correlation ID. Disable AI_COPILOT_PANEL_ENABLED/AI_RUNS_ENABLED/AI_QA_ENABLED/AI_MAPPING_DRAFTS_ENABLED in BFF runtime and restart the owned BFF; keep normal ops enabled | Open current profiles/jobs manually. Do not repeat an unknown Java write. P15 container drill proves profiles remain200 while AI inspect503 |
| Model outage/429/timeout | Stop new AI requests. Inspect static error and request/deadline budgets. Use manual procedure; start existing pinned Ollama only on loopback when appropriate | No automatic POST retry, provider/model switch or paid fallback. Browser fault suite checks503/504 and no auto retry; provider timeout tests are mocked |
| Bad/missing document index | Stop answering from affected collection; verify original hash, source version, grant, expiry and embedding fingerprint. Re-ingest immutable originals into AI storage with curator credentials only | Compare authorized citations and withheld sentinel checks. Do not change source text to improve an eval score; preserve previous snapshot if rebuild fails |
| Embedding model/dimension change | Freeze source/config/ACL inventory and back up AI schema. Build a separate fingerprint/snapshot using the new pinned bundle; validate dimensions and retrieval on dev before publishing | Do not overwrite vectors with incompatible dimensions or load an unpinned network model. Roll back to prior verified snapshot/config if gates fail |
| Expired/inactive profile | Read current immutable Java profile/version; return to explicit operator profile review. Re-preview original bytes under the intended active version | Never silently reinterpret CSV or activate from an AI response. Existing Java remains authoritative |
| Pending/unknown import | Inspect current job state and stored report with existing operator UI. For OUTCOME_UNKNOWN, inspect first, then use the explicit recovery control if eligible | A202 is pending, not completion. Do not redispatch confirm/restart blindly; durable run tests fence late/duplicate results |
| Operator role revoked/session expired | Stop current AI investigation; discard local visible result state and sign in again only if authorized | BFF rechecks Java role per action; source lookup rechecks grants. Do not reuse another user's run reference or bypass403 |
| Runaway/unexpected provider cost | Turn live provider OFF, retain ledger and unknown reservation, reconcile with provider record manually | Never zero ledger/reset day to bypass a block. Paid/unknown pricing rejects before inference; unexpected charge is retained and blocks |
| Provider disabled | Set AI_PROVIDER_MODE=fake and AI_LIVE_ENABLED=false for host demos, or disable AI UI flags completely. Keep keys out of container env | Fake mode is labeled; do not present fake output as real model evidence. Standalone fake-check makes zero external calls |
| Database not ready | Check AI-only DB and migrations, not Java DB. Restore the owned DB service; run `uv run vmarket-ai migrate` with explicit AI owner URL if migration is needed | `/health` may200 while `/ready`503. P15 DB-stop/restore drill measures both; preserve volume and snapshots |
| Roll back schema/image | Disable AI UI, stop owned AI process, back up AI schema/original bytes and restore the last tested code/schema pair into a fresh AI DB | No blind Alembic downgrade over incompatible durable data, no Java downgrade/row edits. Migration rollback is restore/rebuild, not a destructive command supplied by the model |
| Roll back all AI features | Disable all AI flags, restart owned BFF/AI as needed and use existing profile/preview/confirm/job tools | Manual workflow must still work; check active profiles and job inspection. Keep original files and business receipts untouched |

Drill evidence distinguishes actual service/container stops from mocked provider
and browser faults. Only P15's recorded DB/AI stops and restart/manual checks are
actual outage drills; remaining rows are tested mechanisms plus operator guidance,
not fabricated incident transcripts.
