# ADR 0005 — Transactional synthetic document storage

Status: accepted for P05 local implementation. Supersedes P02's proposed file/blob publication mechanism for bounded demo documents; the business/AI database boundary is unchanged.

Store raw originals in AI-owned `document_versions.raw_bytes` (BYTEA/BLOB), bounded to five million bytes. This keeps raw source, immutable metadata, derived snapshot/chunks and vectors within one transactional publication boundary. It avoids pretending that a filesystem rename and database commit are atomically coupled. No external object store is introduced for this small synthetic corpus.

A stable document row owns the collection, revision and active-snapshot pointer. Source versions and pipeline snapshots are retained for authorized historical citations. New configuration builds a distinct snapshot; the document CAS atomically switches its active reference. Service validation binds snapshots to their document before publication; the active pointer has no circular SQL FK. Trusted app SQL credentials are not tenant credentials. Direct database access bypassing the service is outside the actor boundary.

Fixed pgvector columns `vector(32)` and `vector(384)` separate fake plumbing from the pinned real multilingual E5 model. Exactly one column is populated per chunk. SQLite JSON columns are test/development storage only, not claimed pgvector emulation or semantic ranking. P06 chooses ranking/index strategy; P05 has no ANN index or accuracy claim.

Local tooling provisions DB collection grants with curator/migration credentials. App credentials can read grants but cannot insert/update/delete them. Internal actor values are accepted only from trusted code until P09 supplies the signed BFF boundary. No new unprotected upload/query HTTP route is introduced.

Consequences: bounded originals consume database storage and old snapshots increase counts until deletion. Deleting a document purges originals/derived rows and retains a revisioned tombstone/audit. Large corpora, OCR, complex DOCX, remote blob retention and physical backup erasure need separately reviewed designs. Index/read consistency is proven by update/race/failure/delete tests, not by fabricated model metrics.
