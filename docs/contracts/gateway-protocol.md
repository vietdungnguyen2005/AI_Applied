# Internal gateway protocol v1 — design contract

P11 extension: signed `/ai/runs/control` uses `run_control` and the closed
RunCommand/RunSnapshot schemas. Its browser surface is the separate BFF
start/inspect/resume/cancel API; [durable semantics](../runs.md) and
[SQL-controller decision](../adr/0007-durable-read-controller.md) define revision,
lease, current-auth, unknown-outcome and retention checks. This changes no Java
business contract and adds no mutation tool to ToolIntent.

Status: P09 implements signed agent-step/knowledge and the request-bound read-only BFF executor. P10 adds signed mapping drafts; see [runtime and limits](../gateway.md) and [mapping transport decision](../adr/0006-signed-mapping-snapshots.md). Other proposed operations remain disabled/design-only. Schemas: [OpenAPI](openapi.yaml), [gateway envelope](bff-tool-gateway.schema.json). JSON Schema checks syntax only; semantic/security enforcement requires runtime tests. Requirement trace: FR03, FR09–FR15, NFR01–NFR06/NFR09; invariants I01–I10.

## Entry and identity

Proposed browser routes under `/api/ops/ai/` are distinct from existing Java routes. Feature OFF returns 503 `AI_DISABLED`. Browser never calls Python directly or provides effective actor, role, scope, deadline, signature, provider/model, tool result or target URL. BFF accepts only endpoint-specific question/raw CSV/selection fields, ignores/rejects privileged extra fields, checks same origin, current Java session and ROLE_OPERATOR. Protected AI POSTs additionally verify the current CSRF token inside BFF with a maintained timing-safe comparison; no token crosses into Python. This uses existing session introspection, not an invented Java auth endpoint. A document citation GET still requires current session/scope.

BFF obtains `/api/auth/session` using only server-owned BFF credential and the current request's VMARKET_SESSION cookie. A valid response must explicitly say authenticated with ROLE_OPERATOR. Discard csrfToken except the current BFF-local request check. No session/cookie/CSRF response is logged, cached in Python or passed to an LLM. Keep any trusted Java session-cookie refresh only in a request-local cookie jar and propagate legitimate Set-Cookie to the browser; never copy it to Python. Account invalidation stops the loop. Before each tool execution and before returning a protected final response, BFF rechecks the current Java session. The actual Java GET independently applies current account and role checks. Revocation can race a completed read; this is a per-request recheck boundary, not a distributed instantaneous revocation guarantee.

BFF assigns actor_ref = lowercase hex HMAC-SHA256 over a domain-separated stable account identity using a BFF-only pseudonymization key. Use the verified account username only inside BFF; it never becomes prompt/log data. A key rotation invalidates ownership references and old runs; it is not silently remapped. Request/run IDs are new opaque UUIDs. Server config maps verified actor to readable collection IDs and optional document-author permissions. Default demo policy may grant all synthetic collections to all OPERATORs; this is shared-store access, not multi-tenancy. Vendor and collection selections can only narrow server policy. Document ingestion remains OFF by default and requires configured author permission in addition to OPERATOR.

## Signed Python request

Only BFF holds an AI-specific Ed25519 private key. Python receives the matching public key under an allowlisted key ID, not any Java secret. Use RFC 8032 library signing/verifying. For every AI request, BFF sets:

- `X-AI-Context`: unpadded base64url of compact UTF-8 JSON matching SignedContext in the gateway schema; max 4,096 ASCII characters.
- `X-AI-Signature`: unpadded base64url of the 64-byte Ed25519 signature; exactly 86 base64url characters.
- Signature message bytes: UTF-8 `vmarket-ai-context:v1.` concatenated with the literal ASCII X-AI-Context value. Strictly decode and parse bounded JSON, rejecting duplicate/unknown keys. Use the untrusted kid only to select a configured public key, then verify the exact message bytes before trusting any remaining claim. Reject malformed base64url, non-UTF-8, untrusted kid/issuer/audience and oversized headers. No alternate algorithm supplied by a caller is accepted.

Context contains version=1, issuer=`vmarket-bff`, audience=`vmarket-ai`, mode=`integrated`, kid, actor_ref, request_id, run_id, step, nonce, issued_at/expires_at Unix seconds, deadline_at RFC3339 UTC, one operation capability, readable document scope IDs and request_digest. It never contains raw user roles/cookies/CSRF/Java credentials. Context is transport metadata, not LLM context. Do not log it or return it to the browser. Service identity alone is not a user grant: BFF may sign only after the current user's operation/scope checks.

Request digest is lowercase SHA-256 over these **UTF-8 lines in exactly this order**, joined by LF and with one final LF:

```text
vmarket-ai-request:v1
UPPERCASE_HTTP_METHOD
EXACT_CANONICAL_PATH
LOWERCASE_MEDIA_TYPE_WITHOUT_PARAMETERS
X_SOURCE_ENCODING_OR_EMPTY
X_VENDOR_CODE_OR_EMPTY
X_DOC_COLLECTION_OR_EMPTY
X_DOC_ID_OR_EMPTY
X_DOC_VERSION_OR_EMPTY
X_DOC_LANGUAGE_OR_EMPTY
X_DOC_EFFECTIVE_FROM_OR_EMPTY
LOWERCASE_SHA256_OF_EXACT_BODY_BYTES
```

Reject query strings on these endpoints, percent-encoded/noncanonical paths, CR/LF/NUL in any included metadata and unexpected metadata for an operation. Path UUIDs use lowercase canonical UUID text. GET has the SHA-256 of empty bytes and empty media type. Metadata is exact header value after rejecting leading/trailing whitespace; no decoding/normalizing CSV bytes. Internal content-type headers must use the canonical media type without parameters; BFF sets it explicitly and parsers never infer CSV encoding from a charset parameter. This binds declared encoding/vendor/document identity/version as well as payload and route; changing a header must invalidate the signature. Context's operation must match method/path and body type. Duplicate header handling must fail closed, not join contradictory values.

Python verifies `0 <= now-issued_at <= 30`, `issued_at <= expires_at <= issued_at+30`, `now < expires_at`, `now < deadline_at`, and expiry not beyond outer deadline (2-second future clock skew at most, never extend expired deadlines). Both services need synchronized clocks; mismatch yields denied context, not a bypass. Claims bind request/run/step and operation to the JSON body where those fields exist. Read scopes in request bodies must be subsets of signed scopes. Capabilities contain exactly one endpoint operation; a model cannot request documents_ingest with an agent token.

Before side effects or model/provider work, atomically consume `(kid, nonce)` with expiry in AI-owned request_nonces. A duplicate fails 409 `CONTEXT_REPLAY`; no retry reuses a signed nonce. Re-authenticated transport retries, if needed, get a fresh nonce; document raw-hash idempotency prevents duplicate AI version ingestion. The gateway itself does not automatically retry calls with possible provider spend. These security checks are runtime semantics, not properties proven by UUID/date-time schema validation.

## Loop and current-request binding

1. BFF creates a live closure containing verified actor, narrowed scopes, request/run IDs, monotonic deadline, expected step=0 and no pending call. Send signed `/ai/agent/step` with question, `previous_results=[]` and `tool_result=null`. Python is stateless across these step calls; BFF retains the bounded result history inside the live request.
2. Python returns an exact matching request_id/run_id/step and either a final answer/handoff, or one ToolIntentEnvelope. The envelope has one closed tool intent and a call_id UUID. There are no URL/method/header/SQL/role fields. BFF does not accept a callback from Python or a browser-submitted envelope as execution authority.
3. BFF validates envelope schema, exact request/run/step, fresh call_id, remaining deadline/tool budget and tool argument domain. At step=3 another tool is rejected (max 4 model calls /3 tools). The model cannot extend limits or change actor/scope/deadline.
4. Recheck active Java OPERATOR session, then execute only the hardcoded GET with the same request's cookie and server-owned trust headers. Knowledge retrieval invokes only the internal AI corpus under a new signed request and current narrowed scope; model-selected scope may only narrow it. It also consumes one tool execution slot.
5. Validate upstream response shape and select the [sanitized projection](#sanitized-results). Set observed_at when receiving the result, not a model-supplied time. Bind call_id/tool_name to pending intent and next input. Increment step; sign the exact next request with a new nonce and same outer deadline. `tool_result` is the latest matched result; `previous_results` holds exactly step-1 earlier results (max 2). All results come from BFF's closure, with unique call IDs, never browser/model input. Recheck current scope before resending older observations and preserve their observed_at timestamps. No model-forged result is accepted. The combined JSON body must stay within 65,536 bytes; no truncated hidden history is invented.
6. Return final protected output only after one more session/scope recheck; log allowed metadata. Abort on expired auth, cancellation, exhausted budget or deadline; do not continue in a background callback. Discard transient privileged data when the HTTP request ends. A later resume must open a new authenticated request and treat cached results as stale observations, never current permission.

Python's answer is always a draft. Before rendering, BFF verifies citations against current scope and fixed routes, escapes text and prevents arbitrary model URLs/HTML. A blocked/failed tool cannot be rewritten as a successful business observation by final text. Persisted AI state cannot independently restart this loop.

## Tool registry

| Name / strict arguments | Fixed execution | Source and bounds |
| --- | --- | --- |
| get_integration_profiles / `{}` | Java GET `/api/ops/integration-profiles` | IntegrationProfileController, at most 100 |
| get_imports / `{}` | Java GET `/api/ops/imports` | MigrationController, latest 20 |
| inspect_import_job / `{job_id:UUID}` | Java GET `/api/ops/imports/{job_id}/inspection` | Bounded row errors; no direct DB read |
| get_reconciliation_report / `{job_id:UUID}` | Java GET `/api/ops/reconciliations`, filter exact migrationJobId, choose newest stored report | Latest 20 only; absence -> unavailable; never POST or invented by-ID GET |
| search_supplier_knowledge / `{query,collection_ids,top_k}` | AI-owned authorized retrieval only | Signed scope intersection; <=10 collections, top_k<=5; no URL/SQL/path |

Read-only registry excludes preview despite its read-only business transaction because the user's authoritative upload/receipt workflow remains human-owned. Profile create/activate, confirm, restart, reconciliation POST, inventory/checkout/fulfillment writes, code execution and arbitrary fetch are never tools.

## Sanitized results

The schema defines AI wire names, not Java's raw camelCase records. BFF adapters map explicitly and reject incompatible policy/unknown statuses rather than allowing arbitrary dictionaries. Tool result includes matched call_id/tool_name, status, observed_at and a typed data projection or bounded error code, plus `truncated` when applicable.

- Profiles: profile_id/version, vendor_code/encoding, exact three target->source mapping, normalization, active, fixed required_fields; omit createdBy/updatedBy and other account/audit details. Verify Java validation policy is the expected fixed target/range policy before adapting it.
- Imports: ID, observed status, counts, import mode and nullable profile identity. Omit source_name/raw filename and created-by data.
- Inspection: sanitized job, work state, recovery count, server restart_allowed and row number/allowlisted reason code. Never send claim token, receipt, raw source cells, Batch execution context/stack trace or lastRecoveryReason raw string. Parse known error reasons into a fixed code list; map unrecognized text to UNKNOWN_ROW_ERROR, do not echo it.
- Reconciliation: report/job IDs, observed status/counts and discrepancy type/SKU only; omit resolution notes and raw expected/actual values. Reject unexpected types, cap discrepancies at 100 and record truncation. Truncation never implies a complete report.
- Knowledge: authorized doc/version/chunk/locator IDs and bounded excerpts, no arbitrary URL. BFF-authorized collection constraints apply before lexical, vector, reranker and context construction.

Per tool result cap 16,384 encoded JSON bytes; up to 100 row errors/profile items or 20 import summaries with character bounds. If a valid bounded projection still exceeds this, truncate whole list items explicitly or fail `TOOL_RESULT_TOO_LARGE`; never clip JSON/text into false success. Combined JSON step request stays <=65,536 bytes. Rechecks and logs omit all raw auth data. Data fetched just before revocation cannot be made unread retrospectively; don't overclaim that property.

## Status/error and consent contract

| Condition | AI HTTP / code | Behavior |
| --- | --- | --- |
| Invalid schema/CSV/header/digest metadata | 400 INPUT_INVALID | Bounded reason, no repair or business write |
| Missing/invalid context signature | 401 CONTEXT_INVALID | No detailed key/signature oracle |
| Wrong operation/scope/user permission | 403 ACCESS_DENIED | No unauthorized document existence/content |
| No authorized document at citation address | 404 DOCUMENT_NOT_AVAILABLE | Same response for absent and forbidden document |
| Replay/out-of-order/stale run | 409 CONTEXT_REPLAY or STEP_CONFLICT | Stop; no implicit resume |
| File/JSON/extracted content too large | 413 INPUT_TOO_LARGE | Cancel intake; preserve business limits |
| Unsupported/scanned document | 415 DOCUMENT_UNSUPPORTED | Do not pretend extraction/OCR |
| Rate/cost/step budget exhausted | 429 BUDGET_EXCEEDED | No paid fallback/automatic retry |
| Malformed model/tool output | 502 OUTPUT_INVALID | Honest error, no business success |
| Provider/index/database unavailable | 503 DEPENDENCY_UNAVAILABLE | Manual workflow remains |
| Outer/subcall deadline | 504 DEADLINE_EXCEEDED | Abort waiting/loop; no ongoing privileged call |

Unknown policy/conflict/no relevant authorized evidence is HTTP 200 with typed abstained status, bounded reason and appropriate authorized citations. Proposed AI document ingest returns 201 for created/indexed synchronous version or 200 for identical replay; it does not return indexed until the transaction commits. No document queue/202 claim is needed initially. Existing Java missing-job 400 remains a sanitized `unavailable` tool result with `UPSTREAM_RESOURCE_UNAVAILABLE`, not an invented business 404. Preserve 401/403 denial; translate transport 5xx/unknown without leaking raw upstream text.

Human consent in chat cannot mint a business receipt or CSRF authorization. Operator uses current protected publication/activation/preview/confirm explicitly; same original bytes and valid receipt are mandatory. A Java 202, lost response or BFF 502/503/504 is not completed/rolled back. Inspect state; do not retry a business write in this protocol.

P12 enables signed integrated `/ai/ask` and POST `/ai/citations/read` when QA is
enabled. The latter uses `documents_read`, step zero and a strict chunk/scope body;
each access rechecks current grant, active/effective version and deletion state.
The standalone unsigned citation GET is never installed in integrated mode.
Project2 chooses scope from a current actual Java profile reference and removes
internal source URLs from browser responses. See [runtime/UI](../operator-copilot.md).
