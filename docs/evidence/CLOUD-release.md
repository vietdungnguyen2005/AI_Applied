# Independent Cloudflare policy QA — 2026-11-03

Initial online capability is supplier policy QA and citation reading. This is
**not a cloud port of every P00–P16 feature**. Import investigations, durable
agent runs and mapping suggestions remain disabled online; their local Python
implementation remains available.

Public operations entry: https://v-market.vmarket-vietdung2005.workers.dev/ops

| Component | Source / deployed version |
| --- | --- |
| Edge AI adapter | AI_Applied branch `codex/cloudflare-native-backend`, source `0782367` |
| AI Worker | `vmarket-ai-applied`, version `4698b470-7ca6-4f2a-9f3d-38b789c887ea` |
| V-Market BFF | Project2 branch `codex/cloudflare-ai-release`, source `c657c0f` |
| Storefront Worker | `v-market`, version `9d19e79c-4861-4851-9fc0-a7368d281604` |
| Existing Java backend | Render main revision `32d8286`; no new backend deployment |

The runtime uses Cloudflare Workers, Workers AI and a separate D1 database with
18 approved public synthetic chunks. It needs no personal PC or Tunnel, no new
external platform account, no business database migration and no billing-plan
upgrade. Workers Free was checked before inference. Application quotas are
60 attempts per UTC day globally and four per actor per minute; failed attempts
are not refunded or retried. The model is Qwen3 30B A3B, with 512 output tokens
maximum. See [the adapter profile](../../cloudflare/README.md) for limits and
differences from the local E5/Ollama implementation.

Verification:

- 19 edge tests pass using real SQLite, with TypeScript and Wrangler bundle checks.
- 125 V-Market frontend tests, ESLint, TypeScript and OpenNext Worker build pass.
- AI repo CI passed: https://github.com/vietdungnguyen2005/AI_Applied/actions/runs/41492599523
- [Live AI probes](CLOUD-live-ai-smoke.json): liveness/readiness 200, unsigned
  requests 401, replay 409, exact current citation read 200. Actual Qwen calls
  answer approval/encoding questions, abstain for conflicting correction-window
  policies, and abstain for an unsupported gold-price question. Successful model
  responses also validate against the original Python AskResponse schema.
- [Public BFF probes](CLOUD-live-frontend-smoke.json): storefront and operator
  routes 200, eight catalog products, unauthenticated QA 401, runs/mapping disabled.
- [Browser checks](CLOUD-browser-smoke.json): desktop/mobile sign-in gate works,
  with no JavaScript page errors or operator-page horizontal overflow.
- [Panel layout checks](CLOUD-panel-fixture-smoke.json) use browser fixtures only:
  policy form appears with the QA-only configuration, while investigations stay
  disabled. These checks are **not** a production operator login or end-to-end
  authenticated business-session test.

An existing authorized operator must sign in to validate the complete live
session → active supplier profile → BFF → AI → source-dialog path. No production
user was created, no credentials were guessed and no roles were changed.

Native workerd exposed an integration bug hidden by Node fetch mocks: Workers
rejects `redirect: "error"`. The shared Java session reader and QA transport now
use `manual` and refuse non-OK upstream responses without following redirects.
This behavior has a regression test.

The existing Render free service took about 120 seconds to cold-start. Requests
during that interval timed out; afterward readiness, sessions and catalog
recovered. Cold starts remain a demo limitation of the existing free Java host.

All original storefront secret bindings remain secret bindings. The AI Worker
has only a public verification key. The original `Project_Frontend2/main` checkout
is unchanged; deployment code lives in its release worktree. Private rollback
inventory records the prior Worker version. Disabling AI_QA_ENABLED removes the
online feature without changing the manual workflow.
