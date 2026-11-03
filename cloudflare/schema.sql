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
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, actor_ref TEXT NOT NULL, revision INTEGER NOT NULL,
  status TEXT NOT NULL, slot INTEGER NOT NULL CHECK(slot BETWEEN 0 AND 7),
  expires_at INTEGER NOT NULL, purge_after INTEGER NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)),
  request_id TEXT NOT NULL, event_kind TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS active_run_slot ON runs(actor_ref,slot) WHERE status IN('started','waiting_for_operator');
CREATE TABLE IF NOT EXISTS run_events (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,revision INTEGER NOT NULL,
  request_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,phase TEXT NOT NULL,step INTEGER NOT NULL,at INTEGER NOT NULL,
  PRIMARY KEY(run_id,revision)
);
CREATE TRIGGER IF NOT EXISTS run_created AFTER INSERT ON runs BEGIN
  INSERT INTO run_events VALUES(new.id,new.revision,new.request_id,new.event_kind,new.status,
    json_extract(new.payload,'$.phase'),json_extract(new.payload,'$.step'),json_extract(new.payload,'$.updated_at'));
END;
CREATE TRIGGER IF NOT EXISTS run_changed AFTER UPDATE ON runs BEGIN
  INSERT INTO run_events VALUES(new.id,new.revision,new.request_id,new.event_kind,new.status,
    json_extract(new.payload,'$.phase'),json_extract(new.payload,'$.step'),json_extract(new.payload,'$.updated_at'));
END;
