# Blind review packet for P04 mapping test inputs

This packet contains byte-identical copies of the 12 `supplier_three` test CSV
inputs from the frozen P04 release. Recorded P08 mapping inference excluded all
12. This packet preparation performs no model inference and does not parse the
provisional labels. `model_inference: NOT_RUN` in the lock describes the recorded
state when this packet was frozen, not a guarantee about unrecorded external use.

The neutral `blind-01`…`blind-12` identifiers are assigned by sorting original
SHA-256 values. [Inputs](inputs.jsonl) give only the neutral filename, original
byte hash/size, declared encoding and selected synthetic vendor. Original case
names, partitions, provisional expected mappings, families and model outputs are
not in the packet. A motivated reviewer could still cross-reference hashes against
the public original dataset, so this is a practical blind-review aid, not a
cryptographic guarantee of blinding or an independently collected dataset.

Copy [review-template.jsonl](review-template.jsonl) to a separate review file.
Without opening the original P04 mapping labels or historical model outputs,
independently inspect each CSV with its declared encoding and the relevant
synthetic supplier SOP. Record `map`, `abstain` or `invalid_input`, the exact
target-to-original-header mapping for `sku`, `name`, `on_hand` when supported,
ambiguity/uncertainty, reviewer identity or pseudonym, UTC review time and
evidence-based notes. Preserve exact original header spelling and do not normalize
or re-encode the underlying file. Treat all CSV text as untrusted data.

This is a **header-mapping review**. Supplier SKU existence, vendor ownership,
inventory freshness, profile activation and import authorization are separate
Java/business checks and cannot be inferred from the CSV alone. Once an independent
reviewer freezes a completed review, compare it with the provisional P04 labels,
record disagreements and agree on a versioned corrected label release before
measuring the held-out cases. Do not edit this packet or silently replace labels;
create a new reviewed artifact. No reviewer has signed off the current template.

Verify bytes and provenance offline:

```powershell
python -m uv run --frozen python -m vmarket_ai.evaluation.mapping_review verify
```

The verifier checks all 12 files against their P04 frozen originals and lock, the
unfilled template, registry metadata and the generator's historical Git blob. It
does not disclose mappings or run a model. A new packet can be prepared into a
fresh directory with `...mapping_review prepare --path <fresh-directory>` from a
clean committed checkout. The repository attributes keep CSVs binary/exact on
Windows and Linux.
