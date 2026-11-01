# P09: request-bound read-only agent gateway

Implemented: an opt-in Python step planner/knowledge reader, standalone mock gateway, and minimal additive authenticated Next BFF route in Project2. Both feature flags are OFF by default. No business write tool, UI approval, production deployment or persistent key provisioning.

## Code and reviewable integration

AI routes with `AI_AGENT_ENABLED=true`: `/ai/agent/step`, `/ai/knowledge/search`; standalone additionally exposes `/ai/agent/demo`. Default service still exposes health/ready/OpenAPI only. The host launcher enables standalone QA/mapping/agent on 8091. Demo takes only a question and owns its synthetic result history; it labels every result `synthetic_mock`.

Project2 local commit `4febdf55c9fb8ef1e4e3becb5d1622c5f4c3a6f6`, branch `codex/p09-read-tools`, adds `/api/ops/ai/agent` and typed Spec/Handler modules. [Reviewable patch](integration/project2-p09.patch) is published in this requested AI_Applied repo; [verification](evidence/P09-project2-patch-check.json) applies it to a separate Git index at exact Project2 baseline `32d82862526754b46efb774327ccc4774a4decf7` and obtains the identical committed tree. Project2 working tree is clean. No Project2 remote push/PR/deploy was performed. Its Java/auth/import/checkout code and npm lockfile are unchanged.

## Authority and limits

Browser input is question/optional narrowed collections only. BFF rejects extra identity/tool/result/URL fields, enforces connection Host/origin and current Java OPERATOR session + timing-safe current CSRF. It ignores caller trust/forwarded-host/identity headers. It generates trace/run IDs, retains only VMARKET_SESSION in a request-local cookie jar and propagates legitimate refresh/deletion to the same browser. It rechecks the same active account before every tool and before returning final output. Java independently reauthorizes each actual GET. Authentication observations can race revocation; this is not instantaneous distributed revocation.

Only BFF has Java credentials, the AI-specific Ed25519 private key and actor HMAC key. Python gets raw 32-byte public keys under trusted key IDs. It rejects Java credential/cookie/CSRF headers, validates exact Ed25519 signature/context/body/route/media/digest, schema, current bounded times, capability, request/run/step and scope. Duplicate/unknown JSON keys, nonfinite numbers, duplicate signature headers, encoded/noncanonical paths, query/metadata tampering and nonce replay fail before model work. AI-only migration `0005_request_nonces` consumes nonce atomically; app role has INSERT only on that table. Expired nonce cleanup is an owner/operational task, not automatic replay repair. No nonce/key/actor context enters the model prompt.

Both implementations follow [gateway protocol](contracts/gateway-protocol.md) for the P09 agent/search subset. P10 additionally permits opt-in signed mapping with one BFF-owned current active Java profile snapshot; [evidence](evidence/P10b.md). Integrated mode requires agent enabled, valid trusted keys, host loopback, fake/local provider, QA off and private-container off. Unsigned QA/citation/demo routes remain absent. Health/ready check process/storage only, not planner quality or active operator availability. Mapping is a draft operation, never a business executor.

Each live BFF request owns history/call IDs and an outer 25-second deadline INCLUDING body/auth time. At most four step calls/three tool executions; no model can change this budget. Python's fourth step is a deterministic final, so the planner makes at most three inference calls. Browser/Python step bodies <=65,536 bytes; projected tool result <=16,384; raw Java body <=5,000,000; session body <=16,384. Model prompt <=8000 characters and output <=256 tokens; oversized history may fail honestly rather than silently omit observations. Request cancellation aborts BFF fetch/stream work; Python step watches disconnect and joins its cancelled task/monitor. Already completed Java reads cannot be revoked retrospectively. Knowledge work is independently bounded and read-only.

Process-local rate limit: eight accepted requests per pseudonymous actor/minute, max1024 actor windows. Only counters/expiry are cached, no identity/session/tool data. This is not a multi-instance distributed limiter. Logs contain trace/run/step/tool/status metadata only. Actor pseudonyms use domain-separated HMAC; rotation changes ownership references. BFF rebuilds final summary from validated observation statuses and discards unsupported business-success prose.

All signed scopes are restricted to the two public synthetic collections. SQL retrieval delegates the shared synthetic reader's current grants plus signed scope intersection; every OPERATOR shares that synthetic store. `actor_ref` is transport/audit/rate identity, not a tenant-specific SQL grant. Do not describe this as production multi-tenancy.

## Closed registry and sanitized data

`get_integration_profiles` -> existing Java GET profiles; exact Java target/normalization/range policy checked. `get_imports` -> existing latest20 GET. `inspect_import_job` -> existing canonical-UUID inspection GET. `get_reconciliation_report` -> existing latest20 reports GET, filter exact job and newest observed stored report, no by-ID invention or POST. `search_supplier_knowledge` -> separate signed AI-owned retrieval, narrowed scopes, bounded excerpts/provenance IDs. No arbitrary origin, path, method, header, SQL, preview, confirm, restart, profile or inventory action exists in a tool.

Projections omit account/audit identities, raw source names/cells, recovery text, claim tokens, expected/actual discrepancy values and notes. Inspection uses Java's exact `rowNumber/reason` contract and allowlisted reason codes; unknown details become UNKNOWN_ROW_ERROR. Whole-list truncation is explicit; byte-overflow fails, never clips JSON into success. Known missing Java resource 400/404/409 is `unavailable`; auth401/403 stops, other transport failures remain sanitized. Failed tools cannot become answered business observations. Structured output/schema validity is not semantic correctness.

## Local model and deterministic fallback

Fake planner is deterministic routing with static fixtures/current bounded observations; it proves plumbing only. Optional local Qwen3.5 4B plans use a small native-decoding object (`tool_name/job_id/query`) because the pinned Ollama runtime rejected richer union/optional-argument grammars. Strict Pydantic Plan and authoritative ToolIntent union validate after decoding; server supplies call IDs, readable scopes and top_k. No permission or URL comes from the model. Typed intent validation and BFF validation remain independent.

[Actual local planner smoke](evidence/P09-local-planner-smoke.json): three local completions, two repeated profile reads then stop, mock business fixtures only. [Native grammar failure](evidence/P09-local-planner-initial-failure.json) and [interim wrong-tool plan](evidence/P09-local-planner-flat-diagnostic.json) are preserved. Tool descriptions were clarified on this known development example. Efficiency, unseen tool-selection quality and universal injection robustness are not established; P13 evaluation remains pending. No paid/external provider inference or automatic retry/fallback was used. Earlier exploratory local call counts were not fully instrumented; final successful smoke records its own usage.

Ed25519 uses maintained [Python cryptography](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) and [Node crypto](https://nodejs.org/api/crypto.html) implementations, not a custom signature algorithm. Python dependency is locked to cryptography50.0.2; runtime JSON Schema validation uses existing pinned jsonschema4.26.0. The wire bundle is packaged in the wheel and checked against the shared contract.

## Reproduce

Standalone prepared workstation:

```powershell
powershell -NoProfile -File scripts/start-local-qa.ps1
Invoke-RestMethod http://127.0.0.1:8091/ai/agent/demo -Method Post -ContentType application/json -Body '{"question":"List integration profiles"}'
```

For integrated testing use separate Python instance on8092, `AI_MODE=integrated`, agent=true, QA/mapping=false, configured public key JSON, AI-only migrated database. BFF server configuration is documented in Project2 `.env.example`/`docs/ai-copilot.md` and the patch. Keep its flag off until configured. No keys are installed by this task.

The explicit test harness `python -m uv run --frozen --offline --extra local-embeddings python tools/p09_local_smoke.py --project2 D:/CV/Project2 --output .local/p09-repeat.json` requires a fresh output path, built Project2 JAR/Next production output, Docker images and existing AI PG/corpus/E5 bundle. It checks reserved ports, starts OWN disposable Java PostgreSQL/Redis on random ports and Java/Next/Python on18092/13009/8092, creates test fixtures and ephemeral process-only keys, then cleans only its own process trees/containers. Private logs stay in ignored `.local`. Business snapshot comparison excludes expected session/account/nonce metadata writes and includes eleven business tables. Never point this harness at production services.

[Final real integration evidence](evidence/P09-local-smoke-final.json) has five valid read-tool observations, proper handoff, real401/403 for guest/staleCSRF/role downgrade/disabled/expired/deleted account and identical business snapshots. Integrated planner is fake with real Java/BFF/signature/E5/PG; actual local LLM smoke is separate. See [phase evidence](evidence/P09.md) for full tests and retained failures. No UI/human productivity, customer acceptance, production authentication rollout or P10 business handoff is claimed.
