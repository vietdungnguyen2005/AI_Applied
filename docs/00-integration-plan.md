# P00 — Integration plan

Status: proposed architecture, no product code implemented. Follow [source audit](00-repo-audit.md); P02 will freeze detailed schemas.

## Ownership and modes

AI_Applied owns Python API, prompts, fixtures, document metadata, embeddings, drafts, traces, evals and separate storage. Project2 owns business truth, sessions, authorization, stock, imports, reconciliation and audits. Default standalone demo uses fake LLM/embedding providers, synthetic supplier documents and a deterministic mock tool gateway; it must start without any real key or Java DB. Integrated local mode is opt-in and must retain manual operations when AI is unavailable.

```mermaid
sequenceDiagram
    participant U as Operator browser
    participant B as Next BFF
    participant J as Existing Java API
    participant A as Python AI service
    U->>B: Copilot request using existing session
    B->>J: Current session introspection with server trust
    J-->>B: Identity + roles (CSRF remains in BFF)
    B->>A: Bounded synthetic input + minimal request context
    A-->>B: Typed read-only tool intent
    B->>J: Reauthorize current session and execute allowlisted GET
    J-->>B: Authorized result
    B->>A: Sanitized request-correlated result
    A-->>B: Draft answer, citations or handoff
    B-->>U: Suggested output; no business mutation
```

## Concrete gateway direction

Add a dedicated feature-flagged BFF route in P09 after P02 contracts and tests. The existing proxy is a pass-through and does not itself implement the required AI orchestration/auth preflight. Keep that concern in a narrow new server-only gateway rather than rewriting unrelated proxy behavior.

At request entry, obtain current Java session with the incoming session cookie plus server BFF credential. Check authenticated and ROLE_OPERATOR. Discard csrfToken before building any AI payload; do not log the session result. Each intent requires the same live request context, strict argument validation, active authorization and Java's own security chain. Carry cookies/trust headers only between BFF and Java, never to Python. Prevent privileged work after deadline, cancellation or HTTP request completion. Multi-turn work uses bounded calls and correlation IDs, not retained cookies or reusable user assertions supplied by the model.

Initial business tool mapping:

| Intent | Existing Java route | Bounds / behavior |
| --- | --- | --- |
| get_integration_profiles | GET /api/ops/integration-profiles | Max 100, select necessary fields |
| get_imports | GET /api/ops/imports | Latest 20, no invented pagination |
| inspect_import_job | GET /api/ops/imports/{UUID}/inspection | UUID validation, bounded errors, actual missing-job semantics |
| get_reconciliation_report | GET /api/ops/reconciliations | Select an existing stored recent report; absence is unavailable, never run POST |
| search_supplier_knowledge | AI-owned authorized retrieval | Separate document ACL, no arbitrary fetch |

There is an actual read-only reconciliation GET: ReconciliationService.recent is readOnly and reads persisted reports/discrepancies. No by-ID route is assumed. All method/path/header choices are hardcoded by the BFF, never model-controlled. Strip claim tokens, receipts, account data and irrelevant source labels from results. Rate/step/response-size controls and fault statuses become contract tests before enabling integration.

## Human mapping handoff

P08 outputs a schema-checked draft using only sku/name/on_hand. It preserves raw bytes and hash, cannot supply canonical price/vendor identity/stock versions as invented facts. Operator edits and accepts the mapping in the existing protected flow; profile publication creates an INACTIVE immutable version. Human activation, preview and explicit confirm remain owned by Project2. A draft is neither approval nor receipt. Existing 600-second receipt, original bytes, dedupe, stock/product guards and 202/pending semantics remain authoritative.

## Order, gates and fallback

1. P00 source audit and baseline evidence, owner accepts this package before P01 per supplied prompt gate.
2. P01 simulated discovery and acceptance IDs; P02 schemas/threat model and identity gateway review.
3. P03 offline-first skeleton/CI; P04 deterministic datasets; P05 ingestion/ACL; P06 actual retrieval; P07 grounded QA; P08 mapping and rule baseline.
4. P09 narrow gateway, feature OFF, with real local operator/guest/expired/revoked/session/forged-header tests. If safe auth cannot be demonstrated, integrated mode is BLOCKED; standalone remains usable.
5. P10 human handoff and byte/receipt/DB rejection regressions; P11 durable state; P12 operator panel.
6. P13 measured evals, P14 security/regressions including R08 remediation, P15 operations/drills, P16 UAT and honest handoff.

No cloud deployment, real supplier data, unapproved provider spend, AI-owned business write or direct Java database access. Stop a phase at a critical unmet invariant, preserve logs and document a working offline path. Do not silently expand privileges to bypass integration blockers.
