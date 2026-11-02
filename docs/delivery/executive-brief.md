# Executive brief and solution proposal

## Customer context and discovery

V-Market is a fictional retailer. Supplier A sends CP932/Japanese headers;
Supplier B sends UTF-8/English headers. Operators need to understand supplier
procedures, propose mappings without altering original files, inspect import
failures and keep Java's existing approval/recovery rules authoritative.
Discovery artifacts are simulated questions, personas and a clearly labeled
[simulated transcript](../fde/discovery-transcript-simulated.md), not interviews
with a real customer. [Scope](../fde/scope-and-nongoals.md) and
[requirements](../fde/requirements.md) define the agreed engineering exercise;
repository-owner direction to implement is the only actual project authorization.

## Delivered local solution

A Python AI service provides scoped retrieval, extractive source quotes, draft
mapping and bounded read-only investigation through a signed Next BFF. Java keeps
OPERATOR authorization, immutable integration profiles, original-byte validation,
preview receipts, stock consistency, confirmation and recovery. Every business
write stays in the explicit operator flow. Default mode is fake/offline; the
optional local model is pinned Qwen4B with CPU multilingual E5. AI storage is separate.

## Measured value and limits

- New-question retrieval: dense/hybrid Recall@5 1.0 on seven relevant synthetic
  questions; lexical 0.857. Labels are provisional and questions share a known corpus.
- Final generator diagnostic: with sources 6/8 valid, provisional decision 6/8
  across all cases; without sources 2/8. This bypasses production guards equally
  and is a consumed-question regression, not independently reviewed answer quality.
- Original mapping test: rules 0/10 exact, local AI 2/10, with two unlabeled
  mapping targets excluded. Neither meets the proposed >=90% mapping target.
  Manual mapping and review remain necessary; no automatic rollout is proposed.
- Real local signed access/browser, dependency remediation and durable/fallback
  checks passed within documented cases. No universal security or uptime promise.

The benefit established is a functioning, bounded engineering integration and an
auditable way to discover its weaknesses. Labor saving, customer adoption, human
acceptance rate and financial return have not been measured.

## Alternatives and decision

| Option | When suitable | Decision |
| --- | --- | --- |
| Existing manual operations + exact rules | Highest business certainty, no model dependencies | Keep as default/fallback |
| Local model assistance | Private synthetic/local experiments, no provider quota | Implemented opt-in; retain explicit review |
| External free provider | Optional experiments under finite budget | Existing uncertain ledger remains blocked; no new calls |
| Paid cloud/model expansion or autonomous imports | Requires new evidence, governance and authorization | Out of scope; not deployed |

## Acceptance and next decision

Technical delivery is reviewable through clean-install tests, local demos, actual
raw evals and [UAT status](uat-and-acceptance.md). Production/customer acceptance
is **not granted**. Before a real pilot: obtain independently reviewed supplier
gold and policy ownership, meet quality thresholds on a fresh release, complete
human UAT, assign real incident ownership/retention and review the actual deployed
security/dependency posture. Stop AI features if a critical business invariant
fails; use existing manual operations. No assumed SLA, payment integration or
real supplier data is part of this exercise.
