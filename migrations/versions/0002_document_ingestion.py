"""Versioned synthetic documents and separate fixed 32/384-dimensional vectors.

384 is intfloat/multilingual-e5-small's documented output dimension.
32 is the explicitly fake SHA256 plumbing provider, not semantic inference.
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0002_document_ingestion"
down_revision = "0001_ai_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_grants",
        sa.Column(
            "collection_id",
            sa.Uuid(),
            sa.ForeignKey("ai.collections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("actor_id", sa.Uuid(), primary_key=True),
        sa.Column("role", sa.String(8), nullable=False),
        sa.CheckConstraint("role IN ('reader','writer')"),
        schema="ai",
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("collection_id", sa.Uuid(), sa.ForeignKey("ai.collections.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("active_snapshot_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("revision >= 1"),
        schema="ai",
    )
    op.create_index("ix_ai_documents_collection_id", "documents", ["collection_id"], schema="ai")
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("ai.documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("raw_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "source_version"),
        schema="ai",
    )
    op.create_table(
        "document_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id",
            sa.Uuid(),
            sa.ForeignKey("ai.document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pipeline_sha256", sa.String(64), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("extraction_json", sa.JSON(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("version_id", "pipeline_sha256"),
        sa.CheckConstraint("dimensions IN (32,384)"),
        schema="ai",
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("ai.document_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.UniqueConstraint("snapshot_id", "ordinal"),
        sa.CheckConstraint("start_offset >= 0 AND end_offset > start_offset"),
        schema="ai",
    )
    op.create_index(
        "ix_ai_document_chunks_snapshot_id", "document_chunks", ["snapshot_id"], schema="ai"
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column(
            "chunk_id",
            sa.Uuid(),
            sa.ForeignKey("ai.document_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "vector_fake",
            Vector(32).with_variant(sa.JSON(none_as_null=True), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "vector_e5",
            Vector(384).with_variant(sa.JSON(none_as_null=True), "sqlite"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "(vector_fake IS NOT NULL AND vector_e5 IS NULL) OR "
            "(vector_fake IS NULL AND vector_e5 IS NOT NULL)"
        ),
        schema="ai",
    )
    op.create_table(
        "document_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        schema="ai",
    )
    if op.get_bind().dialect.name == "postgresql":
        exists = (
            op.get_bind()
            .execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_app')"))
            .scalar_one()
        )
        if exists:
            tables = (
                "documents, ai.document_versions, ai.document_snapshots, "
                "ai.document_chunks, ai.chunk_embeddings, ai.document_audit"
            )
            op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ai." + tables + " TO ai_app")
            # App cannot grant itself access. Only the local migration/curator role provisions ACLs.
            op.execute("GRANT SELECT ON ai.collection_grants TO ai_app")


def downgrade() -> None:
    for table in (
        "document_audit",
        "chunk_embeddings",
        "document_chunks",
        "document_snapshots",
        "document_versions",
        "documents",
        "collection_grants",
    ):
        op.drop_table(table, schema="ai")
