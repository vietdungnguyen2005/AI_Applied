CREATE TABLE IF NOT EXISTS schema_meta (version INTEGER PRIMARY KEY CHECK(version=1));
INSERT OR IGNORE INTO schema_meta(version) VALUES(1);
CREATE TABLE IF NOT EXISTS nonces (
  kid TEXT NOT NULL, nonce TEXT NOT NULL, expires_at INTEGER NOT NULL,
  PRIMARY KEY(kid,nonce)
);
CREATE INDEX IF NOT EXISTS nonce_expiry ON nonces(expires_at);
CREATE TABLE IF NOT EXISTS chunks (
  chunk_id TEXT PRIMARY KEY, collection_id TEXT NOT NULL, document_id TEXT NOT NULL,
  version_id TEXT NOT NULL, section TEXT NOT NULL, text TEXT NOT NULL,
  effective_from TEXT NOT NULL, effective_until TEXT, active INTEGER NOT NULL CHECK(active IN(0,1))
);
CREATE INDEX IF NOT EXISTS chunk_scope ON chunks(collection_id,active);
CREATE TABLE IF NOT EXISTS budgets(bucket TEXT PRIMARY KEY,used INTEGER NOT NULL CHECK(used>=0));
