# Independent Cloudflare deployment

This is a separate edge adapter for the existing signed V-Market BFF contract.
It runs without the developer's PC. The Python/PostgreSQL/Ollama implementation
and its P00–P16 evidence remain unchanged.

Initial edge scope: authenticated supplier policy questions and citation reads.
Agent runs and mapping suggestions return unavailable and must remain disabled
in the storefront configuration until their durable contracts are ported.
Never enable all feature flags merely because `/health` succeeds.

The public synthetic corpus is CC0. `tools/build_corpus.py` checks source hashes,
eligibility and trust metadata, and uses the existing bounded text extractor.
Its 18 chunks use separate deterministic cloud IDs. This is a bounded full-context
profile, **not the E5 dense/hybrid index**. Each request reads the entire current
authorized collection, capped at 100 chunks and 8,000 serialized characters;
oversized collections fail instead of dropping sources. No production business
records are copied into D1 or model context.

The only inference model is `@cf/qwen/qwen3-30b-a3b-fp8`. The service reserves
a durable maximum of 60 inference attempts per UTC day across all actors and
4 per actor per minute. Failures and timeouts retain their reservation; no retry,
alternate provider or paid-model fallback occurs. Output is capped at 512 tokens.
Deployment must verify Workers Free; there is no automatic billing upgrade.
Cloudflare's account-wide free allowance is shared with other Workers.

Signed requests bind method, route, exact body, operation, actor, scope, deadline
and one-use nonce. Raw cookies and business trust secrets are rejected. D1 only
stores public corpus, expiring replay keys and pseudonymous budget counters.
Scheduled cleanup deletes expired metadata in bounded batches. Request logging
is disabled. The Ed25519 private key belongs only in the BFF secret store; the AI
Worker receives its public verification key.

Model output is strict JSON and is validated again locally. Answers consist only
of exact complete source sentences with current authorized citations. Conflicting
current documents on a cited section force abstention. The entire collection is
rechecked after inference to reject withdrawn or changed evidence. Exact quotation
proves provenance, not semantic correctness; confidence remains `low`.

Checks: `npm ci --ignore-scripts`, `npm test`, `npm run typecheck`,
`npm run dry-run`. Tests use real SQLite through Node 24's `node:sqlite`.
Never copy an application's entire `.env` into this Worker. The configuration
contains a public verification key and a D1 resource ID, never a signing secret.
