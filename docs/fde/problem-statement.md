# Problem statement and evidence register

## Fictional setting

A hypothetical Japanese retailer operates one V-Market store. Supplier A uses Japanese headers and CP932; supplier B uses English headers and UTF-8. An operator wants help finding the relevant supplier procedure, understanding column meaning and explaining a failed import. The operator remains responsible for business meaning, source freshness and approval.

Repetitive header interpretation and policy lookup are plausible discovery hypotheses, not measured customer pain. Existing V-Market already offers versioned profiles, preview and inspection; the AI project should assist those operations rather than claim to introduce them. Quarantine can arise from invalid quantities, duplicate normalized SKUs, wrong vendor ownership or stale product/stock state. Recovery is controlled by the existing importer, not by an AI recommendation.

## Confirmed code facts

Sources below are at the pinned Project2 SHA; path/line references and existing test names are in the [source index](../evidence/P00-source-index.md).

| Fact | Confirmed behavior | Source |
| --- | --- | --- |
| F01 | Profile targets are exactly sku, name, on_hand; mapping JSON is target -> source header | IntegrationProfileService.java:35–60, publish validation |
| F02 | UTF-8/CP932 only; profile IDs/versions/headers constrained; active canonical vendor required | IntegrationProfileService.java:93 onward |
| F03 | New profiles are inactive, immutable versions; activation is separately audited | IntegrationProfileService.publish/activate; V14 migration |
| F04 | Read-only preview returns mapping/counts/row errors and at most 10 accepted rows | SupplierOnboardingService.preview |
| F05 | Confirm binds operator, raw bytes, profile/version, enrichment and 600-second expiry | SupplierOnboardingService.verifyReceipt/sign |
| F06 | Import accepted 202 is staged; actual completion requires inspection; global original-byte dedupe remains | SupplierOnboardingController.confirm; LegacyImportService |
| F07 | OPERATOR session, current account role/enabled status and Java security remain authoritative; mutations need CSRF | SecurityConfiguration; SessionAccountRefreshFilter; OpsAuthorizer |
| F08 | CSV 5,000,000 bytes /1,000 records, JSON 65,536 bytes; strict decoding and width/header checks | RequestBodyLimits; backend-proxy; LegacyImportService |
| F09 | Reports can be read by GET reconciliations; POST creates a report and is a mutation | ReconciliationController; ReconciliationService.recent/reconcile |
| F10 | Operators administer a shared store; supplier vendor binding is not a tenant authorization system | Existing contract and customer-problem; no tenant claims introduced |

## Simulated desires and engineering assumptions

| ID | Classification | Statement | How to validate later |
| --- | --- | --- | --- |
| D01 | Hypothetical operator desire | Explain the policy with an inspectable source/version | J1 evidence and a genuine future operator review |
| D02 | Hypothetical operator desire | Propose headers and expose uncertainty without writing stock | J2 mapping benchmark and review logs |
| D03 | Hypothetical support desire | Summarize current job errors before requesting a human action | J3 read-only traces and current state comparison |
| D04 | Hypothetical security desire | Preserve current permissions and clear human approval boundaries | J4/J5 denial and secret-propagation tests |
| A01 | Engineering assumption | A small bilingual synthetic corpus can exercise retrieval and conflicting policy cases | P04 corpus review; revise if inadequate |
| A02 | Engineering assumption | Header rules are a serious baseline; model suggestions may not improve them | P08/P13 fixed-case comparison; retain rule-only option if equivalent |
| A03 | Engineering assumption | Source age cannot be reliably inferred from three columns | Require explicit freshness warning; no invented approval |
| A04 | Engineering assumption | Integrated assistance can fit a bounded authenticated BFF request | P02 protocol and P09 timeout/revocation tests; fallback standalone if not |

## Problem to solve

Build an inspectable assistant that can answer from authorized synthetic SOPs, draft a schema-valid mapping and explain authorized import inspection results. Each answer must expose its evidence and limits. Unclear policy, invalid input and unknown outcomes must produce an honest no-answer or human handoff. Do not claim reduced labor, inventory correctness gains or model superiority until measured.

Open discovery questions: Who owns SOP updates? Which conflicts require escalation? Is Japanese answer generation required beyond retrieval? What constitutes a costly wrong mapping? Who supplies independent gold labels? These are tracked in the [decision log](decision-log.md), with conservative defaults rather than fictional stakeholder sign-off.
