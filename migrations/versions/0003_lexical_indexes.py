"""Real PostgreSQL FTS expression indexes; no SQLite semantic-search emulation."""

from alembic import op

revision = "0003_lexical_indexes"
down_revision = "0002_document_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for config in ("simple", "english"):
            op.execute(
                f"CREATE INDEX ix_chunks_fts_{config} ON ai.document_chunks "
                f"USING gin(to_tsvector('{config}'::regconfig, text))"
            )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for config in ("simple", "english"):
            op.drop_index(f"ix_chunks_fts_{config}", table_name="document_chunks", schema="ai")
