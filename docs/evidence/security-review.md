# P14 security review — in progress

Started 2026-11-02 Asia/Bangkok at AI `e8d4c68`, Project2 local
`998c2ebf304aefd28b861cd34c9021cd4ebfb13e`. Project2 is clean and remains local
only. P13 technical measurement closeout is [here](P13.md); independent human
quality acceptance remains pending. P13 CI passed:
[run 41437027505](https://github.com/vietdungnguyen2005/AI_Applied/actions/runs/41437027505).
This opening inventory does not complete P14 or assert security against all attacks.

## Standards checked

Read the official [2026 canonical list](https://github.com/GenAI-Security-Project/GenAI-LLM-Top10/blob/main/2026/README.md)
and [publication page](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/)
on 2026-11-02. Use 2026 numbering when extending the existing threat model.
The [Agent Control Standard](https://genai.owasp.org/resource/agent-control-standard-acs/)
is a follow-up reference to inspect; its detailed requirements have not yet been
mapped or claimed compliant.

| 2026 category | Existing implementation/evidence to recheck | P14 disposition |
| --- | --- | --- |
| LLM01 Prompt Injection | Untrusted CSV/SOP/tool data, bounded strict proposals | New adversarial variants pending |
| LLM02 Sensitive Information Disclosure | Signed identities/scopes, current citation lookup, redaction | Cross-session/log/key tests pending |
| LLM03 Excessive Agency | Read-only tool registry, server-owned URL/job scope, human handoff | Forgery/revocation/business action review pending |
| LLM04 Supply Chain | Locked Python/npm/Java dependencies, pinned model bundle | npm audit failing; reachability and fixes pending |
| LLM05 Data and Model Poisoning | Version/hash-bound originals and ingestion | Poisoned source/update tests pending |
| LLM06 Unbounded Consumption | Byte/token/step/time quotas, ledger, cancellation | Giant input/outage/load review pending |
| LLM07 Misinformation | Extractive full quotes, source validation, abstention | P13 measured failures; no semantic accuracy assurance |
| LLM08 Hidden Context Exposure | No client-provided roles; secret separation | Prompt/history/metadata disclosure tests pending |
| LLM09 Vector and Embedding Weaknesses | SQL grants, current scope/version, pinned E5 | Cross-scope/version replay review pending |
| LLM10 Improper Output Handling | Strict model parser, server-owned intent compiler | Output-injection/browser sink review pending |

The existing 33 Python security/workflow gate results and P12 local browser
journeys are prior evidence, not newly executed P14 red-team tests. P14 must
add/review attacks and rerun both repositories' business/CSRF/import regressions,
record denials and any fixes, and assess residual risks. Any broken critical
business invariant blocks progression to P15.

## Actual opening dependency audit

Command: `npm.cmd audit --json` from `D:/CV/Project2`; exit **1**.
[Raw output](P14-npm-audit.json). npm reported **19** dependency entries:
17 moderate, 2 high, zero low/critical. Counts are dependency audit entries,
not 19 confirmed exploitable vulnerabilities in deployed business endpoints.

High entries are `body-parser` and `undici`. npm suggests an available compatible
fix for body-parser and Wrangler `4.156.1` for its undici dependency path. Exact
advisory URLs/ranges and suggested fixes are retained in the raw report.
Reachability, affected deployment modes and fix compatibility have not yet been
assessed. No automatic package upgrade was performed in this opening audit.
Project2 remained clean afterwards. No provider inference or business mutation.

R08 stays OPEN. Next: trace dependency paths/runtime exposure, make a reviewable
compatible dependency change, run frontend/unit/build/Worker and backend
regressions, then rerun audit. Audit counts alone do not establish exploitability.
