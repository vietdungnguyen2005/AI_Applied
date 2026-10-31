"""AI-only originals and immutable mapping draft responses; no business database."""

import sqlalchemy as sa
from alembic import op

revision = "0004_mapping_drafts"
down_revision = "0003_lexical_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapping_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("raw_sha256", sa.String(64), nullable=False),
        sa.Column("raw_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="ai",
    )
    if op.get_bind().dialect.name == "postgresql":
        exists = (
            op.get_bind()
            .execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_app')"))
            .scalar_one()
        )
        if exists:
            op.execute("GRANT SELECT, INSERT ON ai.mapping_drafts TO ai_app")


def downgrade() -> None:
    op.drop_table("mapping_drafts", schema="ai")
