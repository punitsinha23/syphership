"""webhooks, auto deploy and env vars

Revision ID: d8a3e6f1b2c4
Revises: c4f1a9e2d7b8
"""
from alembic import op
import sqlalchemy as sa


revision = "d8a3e6f1b2c4"
down_revision = "c4f1a9e2d7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("webhook_id", sa.BigInteger(), nullable=True))
    op.add_column("projects", sa.Column("webhook_secret", sa.String(), nullable=True))
    op.add_column(
        "projects",
        sa.Column("auto_deploy", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column("projects", sa.Column("env_vars", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "env_vars")
    op.drop_column("projects", "auto_deploy")
    op.drop_column("projects", "webhook_secret")
    op.drop_column("projects", "webhook_id")
