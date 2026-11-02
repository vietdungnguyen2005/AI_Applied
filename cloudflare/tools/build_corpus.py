"""Build a separate, deterministic edge corpus from approved public synthetic sources only."""

import hashlib
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from vmarket_ai.ingestion.parsing import extract_in_worker

root = Path(__file__).resolve().parents[2]
base = root / "data/v1"
statements = ["-- Public CC0 synthetic corpus; cloud-full-context-v1, not the local E5 index."]
count = 0
scopes = {}
for line in (base / "corpus.jsonl").read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    if not row["eligible_for_default_index"]:
        continue
    assert row["synthetic"] and row["license"] == "CC0-1.0"
    assert row["trust_level"] == "curated_synthetic" and row["status"] == "current"
    path = (base / row["path"]).resolve()
    assert path.is_relative_to(base.resolve())
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["raw_sha256"], row["id"]
    for section in extract_in_worker(raw, row["media_type"]).sections:
        text = section.text
        assert 0 < len(text) <= 2000
        chunk_id = str(
            uuid5(
                NAMESPACE_URL,
                "vmarket-cloud-chunk:v1:"
                + row["version_id"]
                + ":"
                + section.locator
                + ":"
                + hashlib.sha256(text.encode()).hexdigest(),
            )
        )
        values = [
            chunk_id,
            row["collection_id"],
            row["document_id"],
            row["version_id"],
            section.locator.removeprefix("section:"),
            text,
            row["effective_from"],
            row["effective_until"],
            1,
        ]

        def sql(value):
            return (
                "NULL"
                if value is None
                else str(value)
                if isinstance(value, int)
                else "'" + value.replace("'", "''") + "'"
            )

        statements.append(
            "INSERT OR REPLACE INTO chunks VALUES(" + ",".join(map(sql, values)) + ");"
        )
        count += 1
        scopes[row["collection_id"]] = scopes.get(row["collection_id"], 0) + len(text)
target = root / "cloudflare/corpus.sql"
target.write_text("\n".join(statements) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "chunks": count,
            "scope_characters": scopes,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    )
)
