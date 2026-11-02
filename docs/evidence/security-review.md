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

The opening counts above are preserved as the baseline. The first remediation
and rerun are recorded below; R08 remains OPEN for residual advisories and review.

## First hardening increment — actual results

### Dependency paths and local patch

`npm ls body-parser undici wrangler --all` traced body-parser through
`@opennextjs/cloudflare -> @opennextjs/aws -> express`, and undici 7 through
`wrangler -> miniflare`. These are observed OpenNext build/local-preview tool
paths. Whether every advisory is reachable in a deployed Worker or through an
untrusted application request has not been established; dependency reachability
is not asserted solely from the package tree. The separate dotenvx path uses
undici 6.29.1 and was not flagged by this audit.

In isolated Project2 worktree `.local/project2-p14`, the reviewable change pins
Wrangler **4.151.1 -> 4.156.1** and compatible transitive updates, including
body-parser **2.3.0 -> 2.4.0** and miniflare's undici **7.29.1 -> 7.30.1**.
No forced major upgrade or npm-suggested OpenNext downgrade was applied.

Actual commands: `npm install --package-lock-only --ignore-scripts --save-dev
--save-exact wrangler@4.156.1`, `npm audit fix --package-lock-only --ignore-scripts`,
then `npm install --ignore-scripts` and `npm ci --ignore-scripts`.
The first clean install rejected a missing optional WASI package in the generated
lock; normal install regenerated the complete lock and the subsequent clean
install succeeded. This intermediate failure was not hidden or called passing.

The new audit reports **15 moderate, zero high/critical**, exit **1**; therefore
the complete audit is still failing. The remaining entries involve glob/minimatch
and dependent build/lint packages. Their upgrade compatibility and runtime
exposure remain open. [After audit](P14-npm-audit-after.json).

Project2 local commit `c851ef9972757a3953b35e3da498c8889f224302` changes only
`package.json` and its lock. [Patch](../integration/project2-p14.patch) reproduces
the exact committed tree using an isolated Git index. The original Project2
checkout remains clean at its P12 commit. No Project2 remote push or deployment.

### Job identifier provenance defect and fix

**P14-F01, medium, fixed locally:** the Python agent previously searched the
entire serialized observation history for a proposed job UUID. A scripted model
could select a tool `call_id`, citation ID or ID embedded in supplier document
text as if it were an observed business job. This demonstrated incorrect intent
acceptance; it did not demonstrate Java authorization bypass or a business write.

The focused test first failed (`DID NOT RAISE GatewayError`). The implementation
now admits only explicit UUID tokens in the user question, or typed job fields
from successful get_imports/inspect_import_job/reconciliation results. Metadata
and source excerpts cannot introduce job references. Java authorization remains
mandatory for every actual read; this allowlist is not an authorization grant.

Seven new deterministic cases pass: direct metadata-ID rejection; explicit
question ID; three typed business-result variants; metadata rejection; malicious
knowledge excerpt/citation-ID rejection. Test names:
`test_observation_call_id_cannot_be_promoted_to_business_job_id` and
`test_job_reference_requires_explicit_or_typed_business_provenance`.
Scripted models test the enforcement boundary, not actual LLM attack resistance.

### Executed verification

- Project2 `npm run verify`: **124 frontend tests pass**, lint/typecheck/Next
  build pass; `npm run build:worker` passes. No public deployment.
- Project2 `backend/mvnw.cmd -B verify`: **115 tests**, zero failure/error/skip;
  build and formatting gates pass. This includes the existing business/security
  regressions, not a newly authored comprehensive red-team suite.
- AI `pytest -q`: **352 passed**, eight PostgreSQL opt-in skips; lint/format
  pass; mypy passes across 66 source files. An intermediate mypy local-name
  collision was corrected before final verification. CI runs the PG cases.
- `uv tool run --from pip-audit pip-audit --path .local/p05-env/Lib/site-packages
  --format=json --output .local/p14-python-audit.json`: pip-audit **2.10.1**, exit
  **0**, no known vulnerabilities in **73 audited dependencies**. One local
  package `vmarket-ai` is skipped because it is not on PyPI. This is the installed
  local Python environment, not proof for every deployment dependency set.
  [Raw result](P14-python-audit.json). An initial unsupported `--disable-pip`
  option failed and was corrected; only the successful command is scored.

[Machine-readable verification/patch proof](P14-verification.json). Raw build logs
remain in ignored `.local/p14-*.log`; generated business IDs and detailed local
test logs are not needed in the public report.

## Remaining P14 gates

R08 residual moderate advisories and deployment reachability are still open.
ACS detailed mapping, expanded adversarial matrix, giant/binary inputs, log/key
leakage, BFF SSRF/revocation, cross-session replay, source/index poisoning,
provider outage/load and current integrated browser re-verification remain to
review/run. Prior P12/P13 tests are evidence to reuse, not claims that these new
P14 gates have all passed. P14 is IN PROGRESS; no progression to P15 yet.
