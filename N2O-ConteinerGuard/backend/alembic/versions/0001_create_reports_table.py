from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_create_reports_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=False),
        sa.Column("commit", sa.String(length=128), nullable=False),
        sa.Column("project", sa.String(length=128), nullable=False),
        sa.Column("pipeline_id", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.Enum("allow", "deny", name="decision"), nullable=False),
        sa.Column("status", sa.Enum("pass", "warn", "medium", "high", name="status"), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("jira_issue_key", sa.String(length=64), nullable=False),
        sa.Column("recommendations_url", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS status")
