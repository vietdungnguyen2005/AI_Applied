# P02 — Design review checklist

This is an agent self-review against source and contracts, not an independent security review. Checked design items mean the decision is documented/consistent; unchecked runtime gates must be executed in later phases.

## Design checks

- [x] Source baseline and Java/BFF ownership are pinned; no invented current Java endpoint or OPERATOR bypass.
- [x] BFF plans current session/role checks, CSRF for AI POST entry, and sanitization of `/api/auth/session` before Python.
- [x] Business tool registry includes only fixed GETs; absent reconciliation uses unavailable, never POST.
- [x] Context binds body plus declared metadata/route; BFF private key is distinct from Java secrets, Python public key only.
- [x] Correlation, one outstanding call, exact next step, nonce, expiry and outer deadline are specified.
- [x] Doc author/read scopes are server derived and distinct from vendor filters/shared-store business access.
- [x] Model/schema cannot mint authority; semantic/runtime checks are explicitly separated from contract syntax checks.
- [x] Original bytes, three-field mapping, 600-second human receipt, global dedupe, stock guards and pending 202 stay authoritative.
- [x] Raw docs/AI DB are isolated; parser expansion/byte/text/page limits and version/dimension migrations are described.
- [x] Fake default/live budget/no paid fallback and evaluation honesty boundaries are stated; HTTP eval job execution is excluded.
- [x] Official 2026 risk IDs and agentic risk controls are mapped to tests without claiming certification.
- [x] Error/status projections exclude cookies, CSRF, receipts, claim tokens, filenames, raw row errors and model URLs.

Schema/example validation and final link/secret/source checks are measured in [P02 evidence](evidence/P02.md), not inferred from these checkmarks.

## Runtime gates before integrated enablement

- [ ] P03/P09: Python/Next Ed25519 interoperability, nonce concurrency, header/body/path tampering and expired context rejection.
- [ ] P09: real local OPERATOR, guest, revoked role/account, expired session, forged headers, between-step revocation and final-response recheck.
- [ ] P05/P07: document access before all retrieval/context/rerank and citation reads; no forbidden sentinel at any sink.
- [ ] P08/P10: byte/encoding/row limits, wrong mapping, human receipt tamper/expiry, duplicate identity and DB rejection assertions.
- [ ] P09/P11: request cancellation, max-step/call binding, process restart, stale resume and no detached privileged work.
- [ ] P03/P15: finite reservation/usage accounting, model outage/manual fallback and live spend opt-in; no external cost in CI.
- [ ] P12: real browser keyboard/mobile/expired-session/unknown-outcome/manual-fallback behavior.
- [ ] P13: frozen held-out config/predictions and actual quality/latency/cost results, independent-human-label limits visible.
- [ ] P14: baseline advisories remediated/reviewed and both repository regressions rerun; no broken critical invariant.
- [ ] P15/P16: key/network provisioning, retention cleanup, isolated clean install, runbooks and actual UAT/qualification evidence.

Until these execute, integrated activation is BLOCKED. Standalone fixture mode can be implemented first without real keys or business access.
