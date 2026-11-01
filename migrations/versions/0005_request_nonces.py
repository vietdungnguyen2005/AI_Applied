"""Atomic BFF signed-context nonce consumption in AI-owned storage."""

import sqlalchemy as sa
from alembic import op

revision = "0005_request_nonces"
down_revision = "0004_mapping_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_nonces",
        sa.Column("kid", sa.String(32), primary_key=True),
        sa.Column("nonce", sa.Uuid(), primary_key=True),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        schema="ai",
    )
    if op.get_bind().dialect.name == "postgresql":
        exists = (
            op.get_bind()
            .execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_app')"))
            .scalar_one()
        )
        if exists:
            op.execute("GRANT INSERT ON ai.request_nonces TO ai_app")


def downgrade() -> None:
    op.drop_table("request_nonces", schema="ai")
