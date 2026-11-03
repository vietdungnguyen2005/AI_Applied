# Independent Cloudflare deployment

This is a separate edge adapter for the existing signed V-Market BFF contract.
It runs without the developer's PC. The Python/PostgreSQL/Ollama implementation
and its P00–P16 evidence remain unchanged.

Online scope: authenticated supplier policy questions, citation reads, lexical
knowledge search, bounded read-only investigations with durable runs, and mapping
drafts. Business changes still use explicit authenticated Java operator actions.
The Workers runtime is a separate adapter, not a deployment of the Python process.

The public synthetic corpus is CC0. `tools/build_corpus.py` checks source hashes,
eligibility and trust metadata, and uses the existing bounded text extractor.
Its 18 chunks use separate deterministic cloud IDs. This is a bounded full-context
profile, **not the E5 dense/hybrid index**. Each request reads the entire current
authorized collection, capped at 100 chunks and 8,000 serialized characters;
oversized collections fail instead of dropping sources. Knowledge search is a
bounded lexical profile; it does not claim dense/hybrid retrieval quality.

The only inference model is `@cf/qwen/qwen3-30b-a3b-fp8`. The service reserves
a durable maximum of 60 inference attempts per UTC day across all actors and
4 per actor per minute. Failures and timeouts retain their reservation; no retry,
alternate provider or paid-model fallback occurs. Output is capped at 512 tokens.
Deployment must verify Workers Free; there is no automatic billing upgrade.
Cloudflare's account-wide free allowance is shared with other Workers.

Signed requests bind method, route, exact body, operation, actor, scope, deadline
and one-use nonce. Raw cookies and business trust secrets are rejected. D1
stores public corpus, expiring replay keys, pseudonymous budget counters and
actor-owned investigation state with projected business observations. Questions
and observations expire after 600 seconds; expired payloads are scrubbed on access
or hourly cleanup. Runs and metadata audit events are purged after a further day.
Knowledge excerpts are never checkpointed as reusable authorization. CSV bytes
and mapping drafts are not stored on the edge; SHA-256 identifies original bytes.
Scheduled cleanup deletes expired metadata in bounded batches. Request logging
is disabled. The Ed25519 private key belongs only in the BFF secret store; the AI
Worker receives its public verification key.

Model output is strict JSON and is validated again locally. Answers consist only
of exact complete source sentences with current authorized citations. Conflicting
current documents on a cited section force abstention. The entire collection is
rechecked after inference to reject withdrawn or changed evidence. Exact quotation
proves provenance, not semantic correctness; confidence remains `low`.

Investigations use compare-and-swap revisions and one-use read leases. A timed-out
lease becomes OUTCOME_UNKNOWN; explicit recovery records an unavailable read
instead of redispatching it. Three read attempts and 24 transitions bound a run.
An actor can hold eight active runs. A model may select only five read tools; job
IDs must come from explicit question UUIDs or typed job observations. Final text
is derived from observed metadata. Repeated list reads finish from existing data.

Mapping accepts at most 45,000 original bytes, 100 columns and 1,000 data rows.
This is a demo edge limit; larger files stay in the manual/local workflow. UTF-8
and CP932 decoding is strict. Signed profile matches are reused per target,
including unambiguous comparison-only case/width/separator differences. Source
names and original bytes are preserved. Comparison collisions stay unresolved;
they never silently select one header. Known targets are locked in the decoding
schema and rechecked after inference; the model only resolves remaining targets.

`mapping-context-v3` supplies explicit target semantics and two generic/train-only
examples. At most 50 evenly spaced rows form column profiles (missingness,
distinctness, integer/range ratios, length, up to five representative values of
80 characters each). These ratios describe the sample, not confidence in a
mapping. Context remains subject to the existing 8,000-character model-input
limit. No extra model calls or provider are introduced. New AI assignments remain
high uncertainty and require human review. Freshness and real ownership still
require Java validation. A comparison-only formatting match is a proposal to use
the original header; it does not edit or activate the Java profile.
Absent historical bindings are omitted from model evidence; only current locked
matches are authoritative. Bare supplier/vendor identifiers are not accepted as
new product-key suggestions. Approved product-key bindings retain precedence.
Before inference, a unique explicitly named physical-stock column with valid
sampled quantities, or a unique display-name column with sampled text, can supply
a rule proposal. Reserved/available stock, vendor identities and conflicting
candidates are excluded. These new proposals remain high uncertainty and require
review; only unresolved targets reach the model. Sampling cannot prove that all
rows are valid; the existing full-file row checks still run.
See [paired diagnostics](../evals/cloud-mapping/README.md), including the retained
V2 result that reduced false suggestions but increased over-refusal.
Mapping model calls share the global quota with QA and investigations. `live`
identifies the cloud runtime, including rule-only signed-profile reuse.

Checks: `npm ci --ignore-scripts`, `npm test`, `npm run typecheck`,
`npm run dry-run`. Tests use real SQLite through Node 24's `node:sqlite`.
The [live operator browser benchmark](../docs/evidence/CLOUD-browser-mapping-time.md)
exercises actual signed-in mapping, profile review/create/activate and Java
preview. All raw timing failures are retained; no human time saving is claimed.
Never copy an application's entire `.env` into this Worker. The configuration
contains a public verification key and a D1 resource ID, never a signing secret.
