# Online AI integration — 2026-11-03

This supersedes the initial QA-only scope recorded in `CLOUD-release.md`.
The existing V-Market now enables policy QA, citation reads, read-only import
investigations with durable runs, lexical SOP search, and mapping drafts.

Entry point: https://v-market.vmarket-vietdung2005.workers.dev/ops

| Component | Source / version |
| --- | --- |
| AI backend source | `codex/cloudflare-native-backend`, `725271a` |
| AI Worker | `vmarket-ai-applied`, `b1f79f3d-6f29-472f-9efe-1084557e0aed` |
| V-Market source | `codex/cloudflare-ai-release`, `1033705` |
| V-Market Worker | `v-market`, `1195219d-bfb6-4f7d-b7db-bd20889bec2d` |
| Java / business database | Existing Render deployment and database; no deploy or migration |

The runtime is independent of the personal PC: Cloudflare Workers + Workers AI
Qwen3 30B A3B + isolated D1 storage. No additional platform, Tunnel, billing
upgrade or paid-model fallback was introduced. The local Python/E5/Ollama stack
and its evaluation artifacts remain available; this is a separate edge profile.

Validation:

- 43 edge tests, TypeScript and Wrangler bundle checks pass. Tests execute real
  SQLite for revisions, leases, audit triggers, expiry and retention cleanup.
- 128 V-Market frontend tests, ESLint, TypeScript and OpenNext build pass.
- 54 affected local Python mapping tests pass. The mapping response type now
  accepts `live`, which the existing wire contract already allowed.
- [Live deployed AI](CLOUD-full-live-smoke.json): create → model plan → claim →
  record synthetic observation → finalize all return 200 and the run completes.
  Lexical knowledge reads, signed-profile mapping, model mapping, and original
  Japanese CP932 bytes return 200. Run/mapping outputs pass the original Python
  wire validator. The knowledge endpoint preserves the actual BFF `{hits}`
  projection used by the existing Python route and KnowledgeData schema.
- [Native Workers BFF harness](CLOUD-full-bff-harness.json): local workerd executes
  actual BFF code with synthetic Java-session/profile/import fixtures and calls
  the real deployed AI/D1. The BFF creates/resumes a run, observes one authorized
  fixture read and completes; its mapping response passes current profile/hash
  checks. The fixture harness is local-only and was never deployed.
- [Public deployment checks](CLOUD-full-public-smoke.json): runs and mapping
  require authentication (401); the storefront still returns eight products.
- [Desktop/mobile panel checks](CLOUD-full-panel-fixture.json): QA and investigation
  forms are visible and usable with browser fixtures, without horizontal overflow.
  These checks do not authenticate a real production operator.

No operator account was created, guessed or granted broader rights. The complete
production operator-login workflow still needs verification with an existing
authorized account. This limitation does not mean synthetic sessions were
accepted by the public service: public signed/session boundaries remain enforced.

Boundaries and limits:

- All AI routes require request-bound Ed25519 context and one-use D1 nonces.
  AI receives no Java session cookie or business trust secret.
- Model calls across features share 60 attempts per UTC day and four per actor
  per minute. Errors/timeouts consume the reservation; no automatic retries.
- Run state uses compare-and-swap revisions and atomic metadata audit triggers.
  One read lease can be claimed once; unknown outcomes wait for explicit recovery
  and are not redispatched. Eight active runs/actor, three read attempts/run,
  24 transitions, ten-minute expiry, one-day additional retention.
- D1 stores projected business observations and actor pseudonyms for runs.
  Knowledge excerpts are removed before checkpointing. Expiry scrubs the question
  and observations; scheduled cleanup removes retained runs and events.
- Mapping accepts up to 45,000 original bytes / 100 columns / 1,000 rows. Larger
  files use the existing manual/local flow. UTF-8/CP932 are strict, original-byte
  SHA-256 is retained, and exact signed-profile headers take precedence over AI.
  New model-selected headers are high-uncertainty drafts requiring human review.
  Raw CSV and drafts are not persisted by the edge adapter.
- Approvals, imports, profile publication/activation and job restarts remain
  explicit Java operator actions. The model only proposes read intents/mappings.
- Render's existing free Java service cold-started in about 121 seconds during
  verification. Login, catalog and other business reads may time out while it
  starts. The cloud AI itself remains independent of that process and the PC.

Rollback: disable `AI_RUNS_ENABLED` and `AI_MAPPING_DRAFTS_ENABLED` to retain the
earlier QA-only deployment, or restore the previous V-Market Worker version.
Git `main` in the original checkout remains unchanged; release branches are
pushed separately for review.
