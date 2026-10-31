# P02 — Threat model and OWASP review

Status: design review, not executed penetration/security testing. Date: 2026-10-31. Scope: local synthetic standalone/integrated AI service, BFF and existing Java boundaries. Sources were read from official sites using the Agent Reach native-web route. No source text, retrieved document or model output grants runtime permissions.

## Reference edition

The official [2026 publication page](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/) and [canonical 2026 list](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/README.md) were checked. The archive landing page still displays 2025, so it is not used to assign 2026 IDs. The [official agentic release](https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/) supplies ASI01–ASI10. The mappings below are **our project-specific design analysis**, not an OWASP endorsement or completed control certification.

## Assets, attackers and boundaries

Assets: Java sessions/trust/CSRF/receipts; authoritative stock/import/catalog/audit; authorized document text/embeddings; raw byte identity; provider keys/budgets; AI signing private key; operator trust; reproducible eval data.

Attackers: unauthorized browser callers; a currently authenticated operator attempting out-of-scope access; malicious synthetic document/CSV/tool content; compromised or malformed model/provider output; replay/forged gateway messages; vulnerable dependencies or parser bombs. A compromised host/BFF can access its own secrets and is not solved by prompt defenses; isolate roles/processes, avoid business credentials in Python and preserve Java authorization.

Entry points: browser AI request, raw CSV/document bytes, citation route, model response, BFF tool result, run resume and server config/dependencies. Trust boundaries: browser->BFF; BFF->Java; BFF->Python; Python->AI storage/parser; provider input/output; text->rendered UI. All model-visible text is untrusted data. No model-produced role/URL/SQL/HTTP header is an authority.

## Risk -> control -> verification mapping

LLM codes below use the verified **2026 edition**. Control descriptions are original project design, not source quotations. All runtime verification remains pending.

| OWASP code | Project attack / asset | Required control | Evidence gate |
| --- | --- | --- | --- |
| LLM01:2026 | SOP/CSV/tool content redirects the assistant | Hardcoded tool registry, independent scope checks, data-only context, no executable actions | AC20,AC28; P07/P09/P14 injected-content tests |
| LLM02:2026 | Cookie/key/forbidden source leaks into model or browser | Select fields before crossing boundary, sentinel propagation checks, scope before retrieval and citation | AC19,AC20; NFR01/NFR09 |
| LLM03:2026 | Assistant gains business mutation authority | GET-only executor, human handoff, no Python business credential/DB route | AC15–AC18,AC25; I01/I04 |
| LLM04:2026 | Dependency/model/parser update compromises runtime | Pinned lockfiles, audits, model manifests and isolated parsers; R08 remains open | P03/P14/P15 supply-chain gate |
| LLM05:2026 | Poisoned SOP/index/labels corrupt answers | Curator-authored synthetic provenance, immutable versions, conflict review, gold separation | P04/P05/P13; AC03/AC04 |
| LLM06:2026 | Huge uploads, expensive inference or endless loops | Streaming caps, ZIP/text/page limits, finite steps/time/concurrency/USD reservation | AC22,AC29,AC30 |
| LLM07:2026 | Confident claim contradicts source or job state | Verified citations, abstention, observed state/time, no 202 success or guessed cause | AC01–AC04,AC11–AC13,AC26 |
| LLM08:2026 | Internal context/history is exposed on demand | Never put transport auth/secrets into prompt; log metadata only; no shared user result cache | AC19–AC21; P11 TTL/ownership tests |
| LLM09:2026 | Vector/index path bypasses document access | Apply scopes before lexical/dense/rerank/context; version/dimension manifest; recheck citation | AC02,AC19; P05/P06 |
| LLM10:2026 | Generated link/HTML/mapping is executed unsafely | Strict schemas, escaped text, ID-only citation routes, exact three target fields | AC05–AC10,AC20,AC28 |

## Agent-specific controls

The ASI code mapping is also our analysis against the official agentic list, not a claim of implemented resistance.

| Code | Relevant project risk | Control / planned test |
| --- | --- | --- |
| ASI01 | A document changes the run's goal | Fixed user request and code-defined capabilities; injected source stays data (AC20) |
| ASI02 | Legitimate tool invoked with harmful arguments | Closed tool+argument unions; exact UUID/scope/method/path; deny write names (AC15,AC20) |
| ASI03 | Cached/forged identity extends access | Fresh Java OPERATOR checks, asymmetric scoped context and nonce replay guard; expired/revoked tests (AC21) |
| ASI04 | Dynamic tool/provider dependency is swapped | No runtime tool/plugin discovery; server allowlist, version lock and model manifest (P14) |
| ASI05 | Model output reaches code execution | No shell/SQL/script evaluator; parser output is text, never executable mappings (AC20,AC28) |
| ASI06 | Saved text contaminates later runs | Actor-owned scoped summaries, TTL, raw tool payload not persisted by default (P11) |
| ASI07 | Forged orchestration message injects a result | Match signed request/run/step and pending call; peer-authenticated channel. No multi-agent architecture claimed (P09) |
| ASI08 | Provider/Java fault triggers a retry cascade | Outer deadline, one outstanding call, no write/inference replay, bounded errors/manual route (AC26,AC30) |
| ASI09 | Polished AI draft is mistaken for approval | Suggested/pending wording, visible evidence and exact human approval scope (AC16,AC26) |
| ASI10 | Controller continues outside its intended lifetime | No detached privileged work, deny exhausted steps/cancelled request; immutable registry (AC21,AC30) |

## Concrete abuse cases beyond schema syntax

| ID | Attempt | Expected runtime denial / proof |
| --- | --- | --- |
| TM01 | Send valid-shape context with forged Ed25519 signature or unknown kid | 401 before provider/document access; cross-runtime signature tests |
| TM02 | Replay a signed nonce concurrently | Exactly one atomic acceptance; other request 409 before side effects/spend |
| TM03 | Change declared CSV encoding/vendor/path/body after signature | Request digest mismatch, no parse/model/tool execution |
| TM04 | Browser sets OPERATOR/actor/collection claims or X-AI headers | Ignore caller claims; derive from actual current session/policy; forbidden fields rejected |
| TM05 | Disable account after first tool or while paused | Reauthorization denies next call/final response; no stale session stored in Python |
| TM06 | Inject another request's tool_result or duplicate call_id | Exact pending-call/run/step association fails; no result accepted |
| TM07 | Collection filter broadens signed scope; citation points to other doc version | Reject scope/citation before unauthorized data becomes visible |
| TM08 | ZIP bomb, scanned/encrypted PDF, malformed CSV, row/byte overflow | Bounded parse rejection; no unbounded memory, false OCR or Java budget bypass |
| TM09 | Unknown row reason contains HTML, filename or credential | Adapter maps to allowlisted code/UNKNOWN_ROW_ERROR; never forwards raw text |
| TM10 | Cost table unknown, provider 429 or uncertain charged outcome | Live fail-closed budget reservation, no automatic paid fallback/retry |
| TM11 | Ask to create reconciliation because report absent | Return unavailable from GET-only tool; zero reconciliation_run writes |
| TM12 | Chat says approve, then repeats original file under another profile | No tool execution; existing human receipt/dedupe/stock checks remain; DB invariants tested P10 |
| TM13 | Anonymous HTTP client hits standalone mode on exposed interface | Startup refuses unsafe bind/public configuration; loopback/container binding tests |
| TM14 | Long-running step or caller cancellation | Abort waiting/executor and discard request closure; no background privileged continuation |

Schema negatives can prove a field or malformed intent is rejected by that schema, not any of TM01–TM14 in a deployed handler. P02 example tests intentionally identify those limits. Byte/record budgets, signatures, raw hash matches, monotonic deadline/expiry, ACL membership, source support and actual DB nonmutation require runtime tests later.

## Residual risk and release blockers

R08: P00 dependency audit failed with 19 advisories including 2 high; no remediation occurs in this design phase. TLS/key provisioning, real session revocation races, parser sandbox limits, shared rate-limit enforcement and operator approval usability remain to be implemented and tested. Retrieved text can still mislead a model despite denied tools; factual/citation evaluation and human review remain necessary. Synthetic finite tests do not establish universal injection resistance, independent customer validation, live deployment parity or production readiness.
