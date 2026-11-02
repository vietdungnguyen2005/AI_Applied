# Engineering UAT report and acceptance decision

Executed: 2026-11-02 Asia/Bangkok, synthetic local environment only. Evaluator:
automated engineering tests/browser gestures directed by the coding agent.
There was **no independent customer or human UAT participant**. This report
updates the historical P01 specification; it does not silently rewrite it as approval.

## Actual execution

- Clean checkout `1c84710`: locked offline install, migrate/fake-check, **378/378
  tests including real PostgreSQL**, no skips; mypy66 and 76 contract checks pass.
- Project2 local `39fbf11`: frontend124, backend115, lint/types/Next/Worker build
  pass; final npm audit0. Backend source unchanged by dependency-only patch.
- [P14 real integration/browser](../evidence/P14-final-acceptance.json): actual
  login, signed Qwen/E5 QA/current source and revocation, unchanged11-table snapshot;
  separate browser faults are explicitly mocked.
- [P15 Docker AI drill](../evidence/P15-integrated-final.json): actual AI stop503,
  manual profiles200, durable restart/resume and unchanged11-table snapshot.
- [Fresh operator handoff repetition](../evidence/P16-handoff.json): real
  Java/BFF/Python, fake rule draft, automated browser review/create-inactive/
  activate/preview/confirm for UTF-8 and CP932, both completed. One lost202 was
  recovered by inspection. Completed replays returned the same jobs without
  changing the11-table snapshot. Tampered bytes/expired receipt/deactivation/
  stock/product changes rejected409, stale/missing CSRF403, guest401 and wrong
  mapping400. Expected business changes occurred only through these explicit
  operator test gestures in the disposable database.

## AC01–AC30 disposition

PASS means the referenced finite local assertions passed, not all possible cases
or independent semantic/customer acceptance. PARTIAL distinguishes those limits.

| AC | Result | Evidence and qualification |
| --- | --- | --- |
| 01 | PARTIAL | Actual grounded answer/source works; independent claim relevance pending; P13 proxy blind spot retained |
| 02 | PASS local | Signed current-source read, actual revocation404, version/ACL tests |
| 03 | PARTIAL | Unknown/outdated guards tested; fresh independently labeled abstention rates unavailable |
| 04 | PARTIAL | Production conflict guard tested; generic generator conflict output was invalid in final diagnostic |
| 05 | FAIL proposed quality gate | Mapping exact AI2/10 vs rules0/10, below proposed90%; byte/schema paths work |
| 06 | PASS automated UI | Explicit operator draft edit/review in handoff tests; no human acceptance-rate measurement |
| 07 | PARTIAL | Ambiguity/forbidden fields guarded; semantic over-refusal remains high |
| 08 | PASS local | Original UTF-8/CP932 bytes/hash binding and persistence assertions |
| 09 | PASS local | Wrong encoding rejects before model/staging in parser/API tests |
| 10 | PARTIAL | Structural negatives tested; known missing-header rule behavior differs from provisional expected input-error label |
| 11 | PARTIAL | Real allowlisted read and state projection; independently labeled tool-task correctness pending |
| 12 | PASS scoped | Pending202/state/stock invariants and explicit inspection tested |
| 13 | PASS scoped | Blocked/missing/unknown states preserved in backend/run recovery tests |
| 14 | PASS scoped | Stored-report fixed GET association and report absence assertions; no reconciliation POST tool |
| 15 | PASS scoped | Closed read-only union and handoff; actual read-only business snapshot unchanged |
| 16 | PASS automated UI | Fresh explicit profile/activation/preview/confirm for both encodings |
| 17 | PASS local | Controlled expired receipt409 and tampered-original409, no unintended writes |
| 18 | PASS local | Deactivated profile, changed stock/product rejection and backend regressions |
| 19 | PASS scoped | Guest/unknown scope denied; revoked source and missing source both404 |
| 20 | PASS scoped | Typed intent, job provenance, forbidden URL/write tests and key/sentinel projections; finite coverage |
| 21 | PASS scoped | Owner/replay/lease/revocation tests; browser role/expiry faults mocked where labeled |
| 22 | PASS local | File/row/envelope, parser expansion/page/memory/deadline boundaries |
| 23 | PASS local | Existing Java duplicate-SKU/width/extra-column regressions |
| 24 | PASS scoped | Unknown vendor/profile/catalog and freshness remain authoritative Java checks, no model-created catalog |
| 25 | PASS local | Fresh completed replay: same job IDs and unchanged11-table snapshot |
| 26 | PASS local | Lost202 browser inspection recovery and pending stock unchanged |
| 27 | PASS scoped | Missing stored report returns unavailable; no invented URL or mutating method |
| 28 | PASS scoped | Injection text remains data, schema/original-byte invariants tested |
| 29 | PASS local | Clean fake mode, labeled output, no provider calls/keys required |
| 30 | PASS scoped | Actual stopped AI/manual profiles200; modeled timeout/budget faults and no paid fallback |

## Proposed metric gates and decision

M01 human claim support, M03 independently reviewed abstention/over-refusal and
M06 real first-draft accept/edit rates are not established. M04 >=90% is **not met**.
M02 measured provisional dense/hybrid recall meets the numeric proposal on small
shared-corpus samples; this does not grant independent acceptance. M08 first-intent
labels11/11 are not end-to-end tool-task semantic quality. M07 automated latency
is measured, human time-to-accepted is not. M09–M12 have finite engineering tests,
not universal assurances. See the unchanged [measurement proposal](../fde/success-metrics.md).

**Decision: technical local demonstration accepted for reviewer inspection;
NO-GO for unattended mapping or real customer production rollout.** Outstanding
quality/human gates are carried into [honesty report](honesty-report.md), rather
than converted into an invented all-green UAT. Existing manual operations remain
the supported path. Repository-owner merge and independent acceptance are pending.
