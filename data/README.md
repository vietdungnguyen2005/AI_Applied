# Synthetic dataset release v1

All records are fictional, repository-authored and safe for a local portfolio demonstration. No supplier/customer data, credentials or observed live inventory is included. Data/SOP/label artifacts are associated with **CC0-1.0**; the repository code license is unchanged. See the [official CC0 reference](https://creativecommons.org/publicdomain/zero/1.0/) and [provenance](../docs/datasets/provenance-and-review.md).

| Inventory | Count / partition |
| --- | --- |
| Original CSV fixtures | 51: 8 train, 6 dev, 12 held-out test, 25 regression |
| Document fixtures | 17: 14 parseable UTF-8 MD/TXT plus empty/invalid/unsupported cases |
| Default policy corpus candidates | 8; retired, untrusted and restricted collections excluded |
| Provisional mapping labels | 51, including non-benchmark/legacy cases explicitly marked |
| Provisional relevance labels | 28: 8 train, 8 dev, 12 held-out test |
| Frozen artifacts | 80 files, 5,149,996 bytes; includes a real 5,000,001-byte negative fixture |

**Independent human review has not occurred.** Labels have `provisional_agent_authored` and `independent_review=pending`; they are not independently human-curated gold. No mapping accuracy, retrieval quality or Java integration result is claimed.

## Reproduce and check

From the repository root, after the P03 locked install:

```powershell
python -m uv run --frozen python -m vmarket_ai.datasets.generate --check
# Or: make dataset-check
```

The command regenerates expected bytes in memory, compares every registered file, verifies [external release lock](releases/v1.lock.json), frozen held-out hashes, structure/metadata/relevance links and split boundaries. It writes nothing. Ordinary generation into an empty owned directory is supported with `--output`; generation refuses to overwrite a differing existing snapshot. v1 is frozen for future experiments. New content/label corrections require an explicitly reviewed new release, not an automatic refresh of the lock.

## Artifact map and inference boundary

- [Authoring input](specs/v1.json): fixed seed 20261031, source contract SHA, header families and original synthetic documents. It is not an inference input.
- [Manifest](v1/manifest.json), [freeze](v1/freeze.json), [partitions](v1/partitions.json): exact bytes, provenance and release identities.
- [Mapping input registry](v1/inputs.jsonl) and `v1/csv/`: original bytes and declared encoding/vendor. IDs/partitions/families are evaluation metadata, not prompt text.
- [Document registry](v1/corpus.jsonl) and `v1/corpus/`: source version, collection, language, owner, trust, effective dates, quality and section locators.
- [Query inputs](v1/queries.jsonl): questions and synthetic document-scope selections; no expected outcome/answer.
- [Labels](v1/labels/): separate provisional expected mappings, source relevance/rationale and negative outcomes. Never index these or pass them to a model.
- [P01 fixture aliases](v1/fixture-aliases.json): maps data-related FX-* names to actual fixture IDs. Job/auth/provider-fault fixtures remain their own implementation-phase work.

The offline mapping-input loader returns only raw bytes, declared encoding and selected vendor. Neutral synthetic display names avoid revealing case IDs or expected decisions. Integrity verification hashes label files but does not return their content as model input. Future document ingestion must use the explicit corpus registry, never glob the entire dataset/labels directory.

## Important contract distinctions

Supplier A uses original CP932 with Japanese headers; supplier B uses UTF-8. Seeded Java mappings have targets sku/name/on_hand and JSON direction target->source. Alternative headers require a human-published, activated compatible immutable profile; a valid CSV template is not automatically compatible with the seeded profile. Candidate definitions are labels for human review, not authorized business actions.

Raw-byte identity examples distinguish exact copies, newline changes and transcoding. UTF-8 BOM is retained; it is not silently stripped. An actual unencodable source and truncated CP932 bytes exercise strict failures. Extra columns and duplicate normalized SKU cases distinguish file structure from authoritative row validation.

Stale expected_stock_version is in a **separate seven-column legacy stock snapshot**, with an explicitly simulated current version. Three-column supplier files do not invent that field. Profile inactivity is an explicit precondition, not an assumption that activating a newer version disables older versions. No receipt/session/Java DB is fabricated.

See [data contract](../docs/datasets/data-contract.md), [split/freeze policy](../docs/datasets/splits-and-freeze.md) and [P04 evidence](../docs/evidence/P04.md).
