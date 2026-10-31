# Synthetic provenance and independent-review status

Authored 2026-10-31 for a fictional Japanese retailer. Original synthetic CSV/SOP/query/rationale/label content is associated with [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/); this does not change the repository code license or claim rights over third-party materials. Each frozen artifact inherits original-synthetic provenance and carries a license/synthetic/hash/byte-size record in the manifest. There is no real client, supplier submission, private document or testimonial.

Contract facts were checked at Project2 SHA `32d82862526754b46efb774327ccc4774a4decf7`: V14 seeded Japanese/English source headers and immutable profile targets, V1 vendor/SKU/seed stock facts, SupplierOnboardingService strict encoding/header/width/row handling, and IntegrationProfileService constraints. Current Java data was not queried and no business writes/tests were initiated in Project2 for P04. Fictional SOP policies and regression state preconditions are clearly separated from those source facts.

## Label status — partial requirement

All **51 mapping labels and 28 relevance labels** are **provisional agent-authored**. Rationale was written from the intended synthetic case/source independently of any inference output, but **no independent human has reviewed it**. Automated structure/hash/source-link checks do not constitute human curation. P04's independent-human-gold requirement is therefore **PARTIAL / pending review**, not DONE. No fake reviewer, signature or review date is recorded.

Dataset authoring/byte gates can support P05 ingestion plumbing while this gap remains explicit. Human-curated-gold/model-quality/customer-acceptance claims remain blocked until genuine review is captured. The review cannot be inferred from a generic instruction to continue implementation. Keep P01 O01/P00 R13 open.

## Review procedure for a genuine independent reviewer

1. Pin the manifest/freeze hashes from the published release. Record reviewer identity/role and actual date only when review occurs; do not prefill an approval.
2. Decode A originals strictly as CP932 and B as UTF-8. Review each intended mapping against source headers, row meaning and the current three-target Java policy. Explicitly challenge aliases, Available/Reserved ambiguity, vendor/quantity warnings and candidate definitions.
3. Read each relevance query within its declared collection scope. Verify every section citation supports the expected outcome; identify missing relevant sources, conflicting precedence, unknown answers, outdated versions and forbidden-source conditions.
4. Record accepted/changed/disputed per-label results with rationale. Double-check a sample with another reviewer if available; otherwise report single-reviewer limits. Do not call an agent self-review independent human review.
5. Store a review record outside frozen v1. Any corrected label/content produces a new reviewed release rather than rewriting v1. Re-run release QA and keep data/code/experiment hashes.

[Review template](review-template.json) is an empty proposed form. It is not a signed review or evidence that a person participated. There are no mapping/retrieval/ROI results to approve in P04.
