"""Bounded owner-bound CAS run checkpoints and append-only transition metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0006_durable_runs"
down_revision = "0005_request_nonces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_ref", sa.String(64), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("initial_request_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(2000), nullable=False),
        sa.Column("collection_ids", sa.JSON(), nullable=False),
        sa.Column("history", sa.JSON(), nullable=False),
        sa.Column("summaries", sa.JSON(), nullable=False),
        sa.Column("pending", sa.JSON(), nullable=True),
        sa.Column("outcome", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(40), nullable=True),
        sa.Column("lease_id", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("purge_after", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "status IN ('started','waiting_for_operator','completed','failed',"
            "'cancelled','expired')"
        ),
        sa.CheckConstraint("phase IN ('idle','planning','ready','executing','terminal')"),
        sa.CheckConstraint("step BETWEEN 0 AND 3 AND revision >= 0 AND slot BETWEEN 0 AND 7"),
        schema="ai",
    )
    condition = sa.text("status IN ('started','waiting_for_operator')")
    op.create_index(
        "agent_run_active_slot",
        "agent_runs",
        ["actor_ref", "slot"],
        unique=True,
        schema="ai",
        postgresql_where=condition,
        sqlite_where=condition,
    )
    op.create_table(
        "agent_run_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("ai.agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("at", sa.BigInteger(), nullable=False),
        schema="ai",
    )
    op.create_index(
        "agent_run_event_revision",
        "agent_run_events",
        ["run_id", "revision"],
        unique=True,
        schema="ai",
    )
    if op.get_bind().dialect.name == "postgresql":
        exists = (
            op.get_bind()
            .execute(sa.text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='ai_app')"))
            .scalar_one()
        )
        if exists:
            op.execute("GRANT SELECT,INSERT ON ai.agent_runs TO ai_app")
            op.execute(
                "GRANT UPDATE(status,phase,revision,step,question,history,summaries,pending,"
                "outcome,reason,lease_id,lease_until,updated_at) ON ai.agent_runs TO ai_app"
            )
            op.execute("GRANT SELECT,INSERT ON ai.agent_run_events TO ai_app")


def downgrade() -> None:
    op.drop_table("agent_run_events", schema="ai")
    op.drop_table("agent_runs", schema="ai")
