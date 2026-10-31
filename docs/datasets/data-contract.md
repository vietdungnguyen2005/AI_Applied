# P04 data contract and quality gates

Scope: offline synthetic release authoring/QA. These helpers are not production ingestion, an Apache Commons CSV replacement or Java business validation. Selected negative structures are checked using Python strict csv/encoding behavior; semantic equivalence for all inputs is not claimed. Original bytes remain unchanged while decoded QA views may be inspected.

## Supplier files

Source of contract: Project2 `32d82862526754b46efb774327ccc4774a4decf7`, IntegrationProfileService, SupplierOnboardingService, V1 and V14 migrations. Source was reread locally in P04; no running Java service/database was consulted.

| Field | Supplier A / NAMI / VM-001 | Supplier B / RIVERBYTE / VM-002 |
| --- | --- | --- |
| Declared encoding | CP932 | UTF-8 |
| Seeded sku source | 商品コード | SKU |
| Seeded name source | 商品名 | ProductName |
| Seeded on_hand source | 在庫数 | AvailableQuantity |

Only sku/name/on_hand are profile mapping targets. Unknown vendor/SKU, quantities outside 0–1,000,000, duplicate normalized SKU, wrong vendor, inactive profile, stale stock and missing seeded headers have separate declared business preconditions. This release does not execute those business guards. An injection-looking product name can be structurally valid and acceptable as ordinary Java text; it is **not** evidence that Java detects prompt injection. AI must treat it as data and preserve independent tool/approval boundaries.

Structural gate codes: ok, byte_limit (empty or >5,000,000 bytes), decode_error (strict declared encoding), missing_header, duplicate_header, width_mismatch, malformed_csv, no_rows and row_limit (>1,000 data rows). A structurally valid missing-domain-header/BOM/ambiguous file can still require rejection or clarification at the mapping/profile boundary. No replacement decoding, header repair, full-width conversion, newline/BOM rewrite or inferred vendor approval is performed.

## Registries and labels

`inputs.jsonl` registers exact original path/hash/size, declared encoding/vendor, contract, benchmark partition/family and explicit intentional duplicate group. These metadata fields support offline QA. `load_mapping_input` validates the release and projects **only** raw_bytes, declared_encoding and selected_vendor_code; do not serialize registry rows into model prompts. Legacy versioned snapshot is rejected by this three-column mapping loader.

Mapping label decisions are suggested, needs_review, abstained, input_error or not_applicable. All have rationale and provisional authorship. A target_to_source mapping is either absent or exactly the three approved fields with distinct sources. A proposed Java Definition in a label is never supplied to inference or executed; it requires current authorization, human review, publication/activation and existing preview/confirm later. Row name tags are deterministic neutral hashes, not case/family/partition names.

`queries.jsonl` holds only questions and synthetic declared document scopes. Relevance labels separately identify document_id/version_id/section_id, binary grade 2 direct support, expected answerability/conflict/denial and rationale. No chunk IDs are fabricated: P05 must preserve section provenance when creating chunks. P06/P13 may add chunk-level labels only through a versioned, reviewed transformation; do not tune on held-out answers. Label completeness/correctness is provisional pending independent review.

## Documents and access metadata

Every document has vendor, source, source version, language, owner, effective dates, trust, collection ID, original hash, license and synthetic flag. Current/retired versions share stable logical document identity with different version IDs. Current correction-window policies intentionally conflict; no precedence is invented. Restricted collection fixtures are synthetic access-test scopes, **not existing V-Market tenants or real accounts**.

14 source documents are readable UTF-8 Markdown/TXT. Three negative documents are empty text, malformed UTF-8 and a generic unsupported binary. `inspect_text` only verifies strict UTF-8/nonempty content for the supported text types. Extraction confidence remains null and OCR=false. There is no scanned-PDF/DOCX parser/OCR claim in P04. Binary media is rejected rather than guessed. Eight current curated unrestricted documents qualify for the default policy corpus; other records remain available as explicit negative/version/scope fixtures.

The QA pipeline checks byte hashes, structural expectations, metadata quality, section locator existence, source relevance references, positive-scope consistency, duplicate explanation and partition boundaries. It does **not** enforce live document authorization, prove provider security or measure retrieval/LLM accuracy. Corpus indexers must consume only allowed corpus records/source paths, never label/spec/context files.

## Provenance and limits

All fixture bodies and provisional labels are generated from repository-owned synthetic authoring material with fixed seed/hash inputs. Seeded SKUs/header constraints are public contract facts from the user's Project2 repository, not copied private business records. Context stock/version values are illustrative preconditions and explicitly `runtime_database_observed=false`. No real account, receipt, customer/supplier file, API secret, paid API call or productivity measurement is included. [Provenance/review](provenance-and-review.md) records the independent-human-label gap.
