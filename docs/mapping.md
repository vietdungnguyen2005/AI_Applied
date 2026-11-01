# P08: standalone supplier mapping drafts

Implemented: opt-in `POST /ai/mapping/suggest`, strict three-field drafts, original-byte storage/hash, exact-rule baseline, optional Ollama suggestions, authorized SOP context and profile differences. P10 adds a signed integrated request and a feature-OFF Project2 human review panel; [evidence](evidence/P10b.md). Only the authenticated human client calls the existing profile/preview/confirm workflow. Python has no business write client or operator cookies/secrets.

## Policy and input

Policy is copied from read-only Project2 source at `32d82862526754b46efb774327ccc4774a4decf7`: `IntegrationProfileService.requiredFields/publish`, `SupplierOnboardingService.prepare` and V14 seed profiles. Allowed targets are exactly `sku`, `name`, `on_hand`; Java profile direction is target -> source, while draft assignments display source -> target. Source names must be distinct, trimmed, nonblank, no ISO controls and at most 80 Java UTF-16 units. Supported declared encodings are UTF-8/CP932. The standalone fake business policy recognizes NAMI/RIVERBYTE and immutable seed profile candidates supplier-a/b version 1. `vendor_verification=standalone_fixture` means fixture lookup only, never a current production-vendor check. Integrated mode remains disabled.

Request contains `raw_base64` (base64 of the ORIGINAL byte stream), `declared_encoding`, `selected_vendor_code`, optional server-known `profile_ids`, `method` (`rule` default or `ai`) and mandatory `synthetic=true`. Caller-supplied mappings, target policy, actor/scope, paths, URLs and executable fields are rejected as extra fields. The synthetic flag is a caller declaration, not a detector of real data. This demo has fixed public synthetic access, not user authentication.

CSV bounds: 1–5,000,000 raw bytes, 1–100 columns, 1–1000 data rows, consistent widths and strict decoding/CSV syntax. Empty/header-only/duplicate/casefold-NFKC-colliding headers, padded/control/BOM names and bad encodings fail before inference. Casefold/NFKC is used only to reject ambiguous names, never to rewrite source bytes. Parser conservatively rejects fields beyond Python csv's runtime field-size bound; this is not a byte-for-byte Java parser emulator. The HTTP mapping envelope is bounded to 6,700,000 bytes (other routes remain 65,536), with a bounded receive deadline. Valid draft responses and the identical raw bytes/hash are atomically inserted in AI-only `ai.mapping_drafts`; malformed inputs are not stored there. The application role has SELECT/INSERT only on this table. Reusing a request ID is not business idempotency and may fail storage insertion. Storage retention/cleanup is a later operational concern.

## Draft behavior

- Rule baseline uses exact seed names and TRAIN-only aliases, frozen before evaluation. Missing fields remain missing; multiple recognized headers for one target abstain. It does not transliterate or mutate authoritative headers.
- `method=ai` sends only headers, at most two rows with cells capped at 160 characters, selected server profile candidates and at most two authorized current mapping SOP chunks. Scope is derived from the selected fixture vendor, never supplied by the model/caller. SOP citations are context, not proof that a proposed alias is correct. Current source/grant state is checked again after inference; revocation returns 409 without saving the draft.
- Native schema restricts each of the three values to a supplied header or null. Server validation rejects invented headers, duplicate source use, unknown targets/properties, scripts/SQL/vendor/version fields and malformed output. Such output becomes an explicit abstention. Provider failure yields an explicitly marked rule draft when available; no inference retry or cloud fallback.
- Every model-derived draft has high uncertainty and `needs_review` (or abstains). A complete rule draft may be `suggested`; **all responses require human acceptance**, and none is a Java-approved profile. `missing_required_fields`, `unmapped_headers`, provenance and per-profile old/new differences support review. Inactive/encoding-mismatched candidates and simple quantity/duplicate-SKU/name warnings force review. These local checks cannot validate catalog ownership, active inventory, business freshness or expected versions.
- No request generates/imports stock values, prices, expected_stock_version, approval receipts or executable transformations. The service has no business write interface or Java credential. It only stores AI drafts. Fake/local are supported; enabling mapping with the live provider fails configuration validation.

## Run

Use the existing prepared local environment/corpus described in [local setup](local-llm.md). Apply AI-only migration `0004_mapping_drafts` with the AI migration role before serving; no business migration is needed. On this workstation migration and Docker rebuild have been performed.

```powershell
powershell -NoProfile -File scripts/start-local-qa.ps1
$bytes = [IO.File]::ReadAllBytes('D:\path\to\synthetic-original.csv')
$body = @{
  raw_base64 = [Convert]::ToBase64String($bytes)
  declared_encoding = 'CP932'
  selected_vendor_code = 'NAMI'
  method = 'rule' # explicitly choose 'ai' for an Ollama draft
  synthetic = $true
} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8091/ai/mapping/suggest -Method Post -ContentType application/json -Body $body
```

Default app/Docker still expose health/ready only; `AI_MAPPING_ENABLED=false` by default. The host launcher enables QA and mapping together on 8091. Citation links resolve on that same origin. There is no UI save/approval/import endpoint in this phase.

## Measured comparison and limitations

Three retained known-development runs each contain 38 cases and both methods (76 outputs): eight train, six dev and 24 regression fixtures; 26 have provisional mapping gold, 12 do not. Twelve mapping test cases received no inference. These are not independent human-reviewed results. Fixture specifications/gold were available during development; do not call this blind evaluation.

| Known cases with mapping gold | Exact rules | Initial 4B | Clarified 4B | Same prompt 9B |
| --- | --- | --- | --- | --- |
| All (26) | 20/26 (76.9%) | 3/26 (11.5%) | 19/26 (73.1%) | 16/26 (61.5%) |
| Supplier A (11) | 8/11 | 2/11 | 9/11 | 6/11 |
| Supplier B (15) | 12/15 | 1/15 | 10/15 | 10/15 |
| Required-field coverage | 76.9% | 60.3% | 73.1% | 61.5% |
| Required-field edit proxy | 18 | 31 | 21 | 30 |

The edit proxy counts missing/wrong target selections against gold; it is not observed human edit/time/acceptance data. Rule baseline is selected as default because neither model beats it overall on known data. The clarified 4B gets only 1/6 dev exact mappings (rules 0/6); it is unsuitable for a claim of reliable unseen-header automation. 4B remains the optional local model for speed/memory, not a quality guarantee.

Across all 38 cases, clarified 4B has 9 abstentions (23.7%), 10 input rejections, no dependency failures and one model output rejection (1/27 adapter attempts; 1/38 cases). Rules have 7 abstentions and 10 input rejections. 9B has 11 abstentions and 10 input rejections. Validated published source-header/schema violations are zero in the offline artifact verifier; semantic errors/omissions still exist. One negative-gold case has a partial rule draft (missing source column), and 9B also proposes a partial draft there; both remain incomplete and cannot be valid Java profiles.

Clarified 4B median/p95 across all cases: 1.192/1.424 seconds, including validation/retrieval/storage; rule median/p95 in that paired run: 0.006/0.046 seconds. 9B: 1.686/1.896 seconds. These include early rejected inputs, are single sequential development runs and do not establish load/cold-start/production latency. Provider billed cost is zero; electricity/hardware is unmeasured. Three full comparisons made 81 local adapter attempts, plus four train-only diagnostic calls and one real HTTP AI smoke. No external provider inference was performed.

Initial weak results are retained, not overwritten. A train-only diagnostic compared explicit typed null/string schema with the old prompt, then clarified prompt wording: selecting a quantity COLUMN does not generate a stock VALUE. Schema change alone still omitted stock on both seed probes; the clarification selected all three. A subsequent 4B and a fixed-prompt 9B comparison used the same known data; this is iterative development, not causal or held-out quality evidence. One rejected 4B model output is retained as a failure code/abstained response; raw model text was not logged, so its exact failure subtype is unclassified.

Regression limits: fixture inactive-profile metadata is intentionally not projected into model input or taken from labels; activity comes from the fake server policy. Accordingly the inactive fixture still selects a seed mapping unless policy is explicitly inactive (tested separately). Unknown catalog SKU/vendor-mismatch rows cannot be business-validated by three CSV columns; reports record those conditions as NOT EVALUATED. Header/BOM behavior is conservatively stricter than some frozen provisional status labels. [Evaluation inventory](../evals/mapping/README.md), [evidence](evidence/P08.md).
