# Cloud mapping refinement — 2026-11-04

This changes the online Cloudflare mapping adapter, keeping the existing
`@cf/qwen/qwen3-30b-a3b-fp8` model, temperature 0, 512 output-token cap and shared
60-attempt/day budget. It does not replace the historical local 4B P13 result.

The supplier-onboarding problem addressed here is losing already known mappings
when one header changes, and proposing a plausible but wrong quantity/product-key
column when source semantics differ. These are mapping proposals; no supplier
profile activation or import happens automatically.

Runtime source: `2ef2d20508e269c4dff1db162a8095b145182170`.
The deployed baseline is `a9381635c4ae89ba5a86e2cd0dc11e9decec3386`, Worker
`b1f79f3d-6f29-472f-9efe-1084557e0aed`. The temporary candidate is Worker
`40ec8537-b1c8-46e5-94ef-f3d3968f173b`.

Promoted AI Worker version: `adc14e47-d3ae-47fd-b830-7ca198a93221` at
https://vmarket-ai-applied.vmarket-vietdung2005.workers.dev . V-Market's existing
BFF already uses this origin; no frontend or Java redeployment was required.
One Wrangler deployment request timed out; the subsequent deployment succeeded.
That administrative retry did not rerun any model diagnostic.

Changes:

- Retain each unambiguous signed-profile match independently. Case, width and
  separator comparison does not rename the original header; collisions stay
  unresolved. Known fields are locked in both decoding schema and validation.
- Describe columns using up to 50 evenly spaced rows, missingness/type/range
  ratios, lengths and representative bounded values instead of two initial rows.
- Give the same model explicit target definitions and two generic/train-only
  examples. Omit absent historical bindings from its evidence. Reject bare vendor
  identity as an unapproved product identifier.
- Before inference, propose a unique explicitly named physical-stock column with
  sampled valid quantities or a unique display-name column with sampled text.
  These remain high-uncertainty proposals requiring human review. An unresolved
  target with no unused source column does not trigger an inference request.

All-row validation, original-byte hashing, UTF-8/CP932 decoding, current Java
profile ownership checks and mandatory human acceptance remain in force. Samples
and names cannot establish business correctness. No additional provider, billing
upgrade or quota reset was used.

## Retained diagnostic history

Every label is provisional and developer-authored; cases are synthetic and small.
Neither supplier acceptance nor time saved was measured. Wrong proposals and
missing supported pairs describe comparison with those labels, not observed
operator corrections.

| Diagnostic | Baseline exact cases | Candidate exact cases | Wrong pairs, before → after | Missing supported pairs, before → after | Gate |
| --- | --- | --- | --- | --- | --- |
| Initial 12-case pilot, context v2 | 8/12 | 8/12 | 4 → 1 | 0 → 3 | Failed: complete mappings regressed from 8 to 5 |
| Same consumed 12 development cases, context v3 | 8/12 | 10/12 | 4 → 0 | 0 → 2 | Failed: complete mappings regressed from 8 to 6 |
| Six-case curl collection, final runtime | 3/6 | 6/6 | 2 → 0 | 2 → 0 | Passed: complete mappings remain 3/3 |

Those observations are preserved rather than replaced by the latest predictions.
The final runtime adds typed candidates after seeing V3's missing fields.

The additional six cases were frozen before successful inference on them. Node
transport failed before a service response in both `followup-v1` and
`verification-v1`; those aborted trials are retained. Collection then used curl
with the same cases, fixed runtime, model and scoring in
`transport-verification-v1`. Any service error in that collection is retained,
never retried. Finishing previously unobserved cases does not replace failures.
This repeated collection is not an independent holdout.

In that final collection, baseline HTTP success was 5/6 and candidate success was
6/6. The baseline's `new-money` response was HTTP 502 `OUTPUT_INVALID`, and was
not retried. Thus the exact-file gain includes recovering a failed response; it
is not solely an increase in semantic accuracy among successful responses.
Both arms correctly mapped all three fully resolvable files. The candidate also
kept supported fields while abstaining on ambiguous quantity, price-only quantity
and supplier-identity-as-SKU cases. All 15 proposed candidate pairs match the
provisional labels, compared with 13 of 15 baseline proposed pairs. No supported
candidate pairs are missing. This does not establish a zero-error production rate.

See [all raw observations, frozen inputs and reproduction instructions](../../evals/cloud-mapping/README.md).
CI recomputes reports offline and makes no model calls. Engineering checks:
58 edge tests pass, TypeScript checks pass and Wrangler dry-run succeeds.

## Production verification

[Three signed production smoke requests](../../evals/cloud-mapping/release-smoke-v1/outcome.json)
returned 200 with expected mappings and rule-only assignments: unchanged profile,
unique physical-stock proposal alongside reserved stock, and a file containing
only two known columns. All require human acceptance; the inferred physical-stock
proposal has `needs_review` status. These requests did not require inference.
Public health returned 200 and an unsigned mapping POST returned 401.

The temporary candidate Worker was deleted after production verification. Its
shared D1 database was retained for the primary service. The actual daily budget
counter was 53/60 for UTC 2026-11-03 after smoke checks (local date 2026-11-04).
This is a total reservation counter including other calls, not a mapping-only
cost measurement. V-Market uses the unchanged AI origin. Real production operator
login and timed supplier onboarding remain unmeasured, as in the previous release.

## Scope of claims

These diagnostics can support a narrowly scoped claim about mapping proposals on
these synthetic files. They cannot support a percentage reduction in supplier
onboarding time, real operator edits or customer error rate. Measuring those
requires a timed task with real or independently reviewed supplier files and
the same acceptance criteria in manual and assisted workflows.
