# AI-owned data model and migration plan

Implementation update: P05's actual schema, transaction boundary, ACL and source-retention behavior are documented in [ingestion](ingestion.md) and [ADR 0005](adr/0005-transactional-document-ingestion.md). In particular bounded raw sources now use transactional BYTEA/BLOB storage, replacing the filesystem proposal below. The remaining P02 text is retained as the original design, not a claim that every proposed table exists.

P02 design only. No SQL/migration executed in this phase. Separate PostgreSQL database `vmarket_ai`, schema `ai`, host port 5434 and own volume/credentials. No FK/query/driver credential into V-Market's business DB. Java UUIDs/profile references are observed opaque external references, not authority or foreign keys across databases.

## Proposed records

| Table | Key and essential fields | Constraints / retention |
| --- | --- | --- |
| collections | UUID, label, synthetic=true, vendor_code filter metadata | Vendor is not tenant ACL; IDs provisioned by curator, not model |
| documents | Stable document UUID, collection FK, opaque logical source label | Collection membership immutable; curator creates identity, never an arbitrary path/URL |
| document_versions | doc UUID + version UUID, collection FK, source_version label, raw_sha256, language, effective_from, supersedes, trust_level, parser/version, quality state | Unique collection/doc/source_version; same version+different raw hash conflicts; retain immutable source provenance; no auto-precedence from version label |
| document_chunks | chunk UUID, document version FK, ordinal, section/page locator, normalized text, text_sha256, tokenizer/version | Unique version+ordinal, deterministic ID/hash inputs; no unauthorized cross-version cache |
| embedding_indexes | index UUID, model ID/revision, dimension, normalization/chunk config hash, status | One compatible active manifest per collection/index configuration |
| chunk_embeddings | chunk FK + index FK, vector fixed dimension | Fixed-dimension table/index per supported dimension; never mix fake/real models in one active manifest |
| lexical index | tsvector/config + chunk FK | Explicit language/tokenization configuration; Japanese limits measured against held-out cases |
| request_nonces | kid+nonce, actor_ref, expires_at | Unique atomic insert before protected work; purge expired >skew window, no reusable user credential stored |
| mapping_drafts | UUID, actor_ref, request ID, raw_sha256, declared_encoding, chosen_vendor, structured draft, created_at, expires_at | AI suggestion only; no receipt/cookie, no automatic promotion; default TTL 24h |
| run_states (P11) | run UUID, actor_ref, collection scope snapshot, status, step_count, state_version, deadline/expires_at | Optimistic CAS; current BFF request reauthorizes every resume; not a durable grant |
| trace_events | UUID, request/run/call, pseudonymous actor_ref, enum event/code, latency/usage metadata | Default retention 7 days; no raw prompt/cell/header/result; local configurable explicit policy |
| provider_budgets | provider/model/day bucket, cap, reserved and charged USD/token units | Atomic reservation; unknown outcome retains reservation pending review; no negative free capacity |
| eval_runs / predictions | config/data/code SHA, mode/provider/model, measured outputs, error taxonomy, metrics | Synthetic only, immutable per-run output; version control approved reports; label developer-reviewed gold |

Raw document originals are stored in the isolated AI volume using generated IDs/hash-based internal keys, no user filename/path traversal or public access. The database stores the raw hash and owned object key, not arbitrary URL. An original CSV is handled as a bounded in-memory buffer for mapping and remains with the browser's authoritative upload path; default AI draft storage retains hash/encoding/header draft, not all source rows. Explicit synthetic eval fixtures are versioned separately. Original documents are immutable; normalized extracted text/chunks/embeddings are derived rebuildable data.

## Access and ingestion

Server-side BFF policy assigns read scopes and separately configured author capability. Scope is verified before lookup/query and citation open; embeddings/chunks inherit collection access. A user collection filter may narrow scope only. AI-level document scopes do not imply V-Market vendor tenancy. Standalone corpus is a fixed public-within-loopback synthetic demo scope and proves no real multi-user isolation.

Each source version has owner/provenance, synthetic license declaration, language, effective date, trust=`curated_synthetic` or `untrusted_fixture`, quality state, raw hash and parser version. Ingest declares X-Doc-Id (stable curator UUID), collection and source version; membership/author permission are checked before reuse or creation. License/curation status comes from the locally maintained synthetic-source manifest, not from model text or an arbitrary upload attestation. Effective date is metadata, not approval. Only curated current parseable versions enter the default policy index; unresolved current conflicts remain explicit and cause abstention. Old versions remain resolvable by authorized citation ID for reproducibility, never silently substituted as current policy.

Accepted raw media candidates: TXT/Markdown UTF-8, text PDFs and DOCX only after robust parser installation/tests in P05. Reject scanned/unextractable PDF (no pretend OCR), encrypted/unreadable/unsupported formats and media mismatch. Parser budget proposals: raw 5,000,000 bytes; extracted text 1,000,000 Unicode characters; 200 pages; DOCX expanded ZIP bytes 20,000,000, at most 1,000 entries and per-entry/total bounds; no external relationships/macros/network access. Time budget 10 seconds clipped to outer request deadline. Bounds are enforced while parsing, not after unbounded allocation. Oversize -> 413, unsupported extraction ->415; parsing errors ->400. These are future tests, not P02 runtime proof.

Document ingest writes raw blob to temporary AI-owned storage, parses/validates, then commits metadata/chunks/index state transactionally and atomically publishes the owned blob; failed transactions leave no active version. Orphan temp blobs are removed by a bounded cleanup. Same declared version + same raw hash returns existing successful version; same version + different bytes is 409. Mark index state ready only after embedding/index commit. No automatic external-provider embedding call is permitted without the live budget gate.

## Migrations and rollback

1. P03 Alembic initial AI schema: collections/document metadata foundations, trace/budget/nonce records as features require. Use least-privileged app role; migration role owns DDL/pgvector extension. Do not create speculative unused tables just to match this plan.
2. P05 adds immutable version/chunk/ACL-aware retrieval records, fixed-dimension vector storage and lexical indexes. Fake embedding dimension 32 may be used for plumbing; real provider dimensions come from verified manifest. Explicit migrations choose each actual dimension; no dynamic SQL from model input.
3. P08 introduces draft persistence if needed; P11 adds durable state/version/TTL only after controller recovery design and tests. Eval records may initially be repository files rather than DB tables.
4. On model/dimension/chunk config change, build a new index manifest beside the old, validate access/quality/counts, switch active reference atomically and retain old manifest for rollback. Never reinterpret existing vectors at a new dimension/model. External cost must be budgeted before re-embedding.
5. Roll back by disabling AI or switching the active index manifest, not by modifying Java imports/stock or dropping business schema. Before destructive AI schema/data rollback, back up synthetic artifacts and inspect migration downgrade support; no destructive migration is authorized by this document.

## Proposed retention and state

Draft/run content expires after 24h by default, sanitized operational traces after 7 days, consumed nonces after expiry plus allowed skew, curated synthetic documents until curator deletion/version retirement, eval artifacts retained for reproducibility. TTL is a planned cleanup policy, not a verified precise-erasure SLA. No raw business tool payload is durable by default; any later safe summary must be actor-owned and treated as stale observation. Conversation TTL never extends Java authorization.

Future statechart: started -> waiting_for_operator/completed/failed/cancelled/expired. Waiting_for_operator is an informational AI pause, not an import approval token. A resume requires fresh BFF identity/scope and increments state_version by CAS; duplicate/stale resume 409, no repeated side effects. P11 must test actual process restart behavior before durability is claimed.
