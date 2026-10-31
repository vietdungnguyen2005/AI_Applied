"""AI-only collections and live-provider budget ledger; no business tables."""

import sqlalchemy as sa
from alembic import op

revision = "0001_ai_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "provider_controls",
        sa.Column("provider", sa.String(32), primary_key=True),
        sa.Column("pending_usage_id", sa.Uuid(), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        schema="ai",
    )
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint("synthetic = true"),
        schema="ai",
    )
    op.create_table(
        "provider_budget_days",
        sa.Column("provider", sa.String(32), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("requests_used", sa.Integer(), nullable=False),
        sa.Column("reserved_microusd", sa.BigInteger(), nullable=False),
        sa.Column("spent_microusd", sa.BigInteger(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.CheckConstraint("requests_used >= 0"),
        sa.CheckConstraint("reserved_microusd >= 0"),
        sa.CheckConstraint("spent_microusd >= 0"),
        schema="ai",
    )
    op.create_table(
        "provider_usage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("reserved_microusd", sa.BigInteger(), nullable=False),
        sa.Column("spent_microusd", sa.BigInteger(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["provider", "day"], ["ai.provider_budget_days.provider", "ai.provider_budget_days.day"]
        ),
        sa.CheckConstraint("state IN ('reserved','completed','uncertain')"),
        sa.CheckConstraint("reserved_microusd >= 0"),
        schema="ai",
    )
    if op.get_bind().dialect.name == "postgresql":
        # Local Compose init creates ai_app. Other environments may provision a different role.
        exists = (
            op.get_bind()
            .execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_app')"))
            .scalar_one()
        )
        if exists:
            op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA ai TO ai_app")
            op.execute(
                "GRANT INSERT, UPDATE, DELETE ON ai.collections, ai.provider_budget_days, "
                "ai.provider_usage, ai.provider_controls TO ai_app"
            )


def downgrade() -> None:
    op.drop_table("provider_usage", schema="ai")
    op.drop_table("provider_budget_days", schema="ai")
    op.drop_table("collections", schema="ai")
    op.drop_table("provider_controls", schema="ai")
    # Retain the extension/schema; never drop shared infrastructure implicitly.
