# Synthetic document ingestion

P05 implements internal Python services and a local corpus CLI. HTTP upload, signed BFF actor construction and business tools remain disabled/pending P09. A caller cannot obtain an authenticated actor by posting an actor UUID to the health-only API. The following examples are curator-operated local demonstrations using frozen synthetic P04 data.

## Run offline

```powershell
python -m uv sync --locked
python -m uv run --frozen python -m vmarket_ai.ingestion.demo --report .local/ingestion-demo.json
```

This migrates an AI-only SQLite database `.local/p05-ingestion-demo.db`, provisions fixed synthetic collection grants and ingests the manifest. The fake provider produces 32-dimensional SHA256 plumbing vectors, not semantic embeddings. `make ingestion-demo` is the equivalent Make target. Repeated runs retain archived sources and reuse unchanged current snapshots. The CLI consumes the external P04 release pin before opening source paths; it never reads CSV rows or evaluation labels into an embedding prompt.

On this Windows workstation, final validation uses a fresh environment because an interrupted NumPy replacement left stale files in the older `.venv`. Use this isolated environment to reproduce the recorded local checks without changing that older environment:

```powershell
$env:UV_PROJECT_ENVIRONMENT = "$PWD/.local/p05-env"
python -m uv sync --locked
python -m uv run --frozen pytest -q
```

NumPy is bounded to `>=2,<2.3` so its installed stubs support the project's Python 3.11 typecheck target. No other existing package installation needs to be removed. CI uses a fresh environment with the default lockfile installation.

## Local real embedding

The optional provider runs the author's `intfloat/multilingual-e5-small` ONNX FP32 model on CPU, with **384 dimensions**, attention-mask mean pooling, L2 normalization and separate `passage: `/`query: ` prefixes. These choices follow the [author's model card](https://huggingface.co/intfloat/multilingual-e5-small). Revision `614241f622f53c4eeff9890bdc4f31cfecc418b3` and both model/tokenizer SHA-256 hashes are pinned in code and the downloaded bundle manifest. The MIT model license is separate from synthetic data's CC0 notice.

```powershell
python -m uv sync --locked --extra local-embeddings
python -m uv run --frozen --extra local-embeddings python -m vmarket_ai.ingestion.model_bundle .local/models/multilingual-e5-small
```

Download once into a new destination. This explicitly downloads roughly 450 MiB of public model/tokenizer files; no document, key or inference request is sent to Hugging Face. Runtime bundle loading verifies the registered revision and pinned hashes, refuses implicit downloads and fails closed if optional packages/files are missing. Bundles/cache/weights are ignored by Git. The download is optional; ordinary tests never fetch weights or need API keys. Inputs over 512 tokens fail rather than silently truncating text. Chunk size/overlap and fake/local profile are configurable; supporting a different real model requires registering its identity and a corresponding fixed-dimension migration.

For the separate local AI PostgreSQL instance from Compose:

```powershell
$env:AI_DATABASE_URL = 'postgresql+psycopg://ai_app:local-ai-app-only@127.0.0.1:5434/vmarket_ai'
$env:AI_MIGRATION_DATABASE_URL = 'postgresql+psycopg://ai_owner:local-ai-owner-only@127.0.0.1:5434/vmarket_ai'
python -m uv run --frozen --extra local-embeddings python -m vmarket_ai.ingestion.demo --postgres --model-bundle .local/models/multilingual-e5-small --report .local/real-ingestion.json
```

These are already documented disposable-local Compose credentials, not provider credentials. The curator connection provisions grants and migrations; the app connection performs ingestion/reads. The app role has SELECT-only access to `collection_grants`, so a service cannot grant itself access with app credentials. Integrated mode still refuses startup. [Actual local-model and pgvector evidence](evidence/P05-local-model-smoke.json) confirms Japanese/English inference and stored dimensions; it is not a retrieval-accuracy benchmark.

## Parsing and traceability

| Input | Implemented behavior and location |
| --- | --- |
| UTF-8 TXT/Markdown | Strict decode, no BOM/format mismatch/control characters; headings create `section:<heading>` locators, repeated headings receive occurrence suffixes |
| Text PDF | pypdf text extraction, `page:<one-based-page>`; encrypted, active-action/form, malformed, over-200-page or any empty/unextractable page rejected |
| DOCX | python-docx main-body paragraphs and tables, `paragraph:N` and `table:N:row:R:cell:C`; preflight expanded ZIP/entry bounds and XML entity checks |
| Unsupported DOCX content | Reject external relationships, macros/embedded objects, headers/footers/notes, tracked changes, content controls, drawings/text boxes and nested tables rather than claiming full extraction |
| Scanned/unsupported formats | Reject; no OCR engine, fabricated confidence, image interpretation or layout-fidelity claim |

Every parse runs in a new child process with a sanitized environment and disabled socket connection functions. Parent wall timeout is configurable up to 10 seconds and kills/reaps the child. Resource limits are applied before parser imports: 768 MiB per-process memory and eight CPU seconds, via a Windows nested Job Object or POSIX rlimits. Child limit setup failure rejects parsing. No arbitrary URLs, external relationship resolution, shell command, model or database credential is passed to the parser. Raw bytes are bounded to 5,000,000; extracted characters to 1,000,000; sections/chunks to 5,000. DOCX has at most 1,000 ZIP entries, 20,000,000 total expanded bytes and 10,000,000 per entry. Bounds do not constitute an antivirus/security certification; P14 adversarial hardening remains pending.

Normalization changes derived text only: NFC, CRLF/CR to LF, trailing-line whitespace and outer whitespace trimming. Section text is preserved in the snapshot; chunks store section-relative Unicode start/end offsets, ordinal, exact text hash and deterministic UUID. Default windows are 320 characters with 48-character overlap, contained within each section/page. This is character chunking, not a claimed tokenizer; the real provider separately checks its token limit. PDF reading order and DOCX paragraph locators are extraction-level references, not proof of visual layout or Word page numbering. See [pypdf's OCR/extraction limits](https://pypdf.readthedocs.io/en/6.21.1/user/extract-text.html).

P04 document UUIDs and declared source-version strings are preserved. The database derives its own version UUID from that pair; this is distinct from P04's fixture-version UUID. Demo reports include an explicit `source_version_crosswalk` between them. Future relevance evaluation must resolve that crosswalk plus `section:<P04-section-id>` rather than comparing unrelated UUID namespaces or silently substituting a current version.

## Version publication and deletion

```mermaid
erDiagram
    collections ||--o{ collection_grants : scopes
    collections ||--o{ documents : contains
    documents ||--o{ document_versions : preserves
    document_versions ||--o{ document_snapshots : derives
    document_snapshots ||--o{ document_chunks : splits
    document_chunks ||--|| chunk_embeddings : embeds
    documents }o--o| document_snapshots : active_pointer
```

The implementation stores bounded originals as SQLite BLOB/PostgreSQL BYTEA inside the same transaction as metadata. This deliberately replaces P02's proposed filesystem blob publication: it removes the database/filesystem atomicity gap and temp-blob cleanup for this small local corpus. A larger object-storage design would require a separate publication/outbox protocol.

`documents` has an immutable collection identity, a monotonically increasing revision and one active snapshot. Each immutable `document_versions` row binds a curator-declared source version, raw SHA-256, original bytes, media type and metadata. Reusing that version with different bytes **or metadata** conflicts. Same active version/pipeline/bytes is idempotent even after a response-loss retry using the earlier expected revision. A retry of an older inactive version must supply the current revision and is an explicit curator action, never an automatic version-label precedence rule.

The pipeline fingerprint includes model identity/dimensions/mode, parser implementation/package versions, Unicode normalization version and chunk settings. Changed chunk/model configuration builds a separate immutable snapshot and vector rows. Parsing and embedding happen before publication; only a successful transaction/CAS publishes all derived rows and the new active pointer. ACL is checked before expensive work and again at publication. Racing updates with the same expected revision yield one winner and one conflict. Failure halfway through storage rolls back raw/version/chunk/vector changes and leaves the previous snapshot active. Re-indexing keeps old snapshots for authorized citations/explicit rollback; current queries cannot see their stale chunks.

Deletion CAS-tombstones the stable document and removes **all** source bytes, snapshots, chunks and vectors via foreign-key cascades in one transaction. Old citations and source retrieval then return no authorized result. Tombstone identity/revision prevents stale create retries from resurrecting a deleted document. Audit IDs/timestamps remain; this is logical database deletion, not a secure physical-erasure/backup SLA.

## Collection authorization and audit

`Actor` is an internal trusted-context value. Local curator tooling grants reader/writer roles per collection using migration-role credentials. Write operations require writer; reads require reader/writer in the query's explicit collection intersection. Document collection membership is immutable. SQL joins and predicates apply the actor's grants, document state and requested collections **before** selecting text and applying LIMIT. Current reads also enforce active snapshot, curated/current status and effective date range. Archived citation/original reads recheck collection grants; a chunk UUID is not authority. No unauthorized text is loaded and then filtered in Python.

The P05 reader is a bounded authorized candidate/citation lookup, not lexical/dense/hybrid ranking. P06 will add retrieval methods over compatible embedding snapshots. A requested collection filter can only narrow grants; the signed gateway's request validation/identity enforcement is P09. Database app credentials remain trusted service credentials with table-level access; this does not claim database row-level security or a deployed multi-user authentication system. An already-authorized in-flight transaction is not synchronously cancelled by a later grant revocation; the commit recheck catches revocation completed before that check, and every subsequent read uses current grants.

Persistent audit rows contain actor/entity UUIDs, event, count and timestamp only. They record ingestion publication/reuse/rejection, successful deletion, candidate/citation/original reads. Empty candidate reads are recorded. A rejection audit failure emits a fixed safe event. No source text, query, row data, document filename, provider key or caught exception string is logged. Failed delete/original access currently raises a safe code; durable denied-event coverage and retention cleanup remain P14/P15 hardening.

P04's independent-human label review remains pending. None of the parser, model smoke, source-trace or authorization tests establishes mapping/retrieval quality or customer acceptance.
