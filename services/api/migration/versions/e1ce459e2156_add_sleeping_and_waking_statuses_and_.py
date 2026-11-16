"""add sleeping and waking statuses and last_active_at

Revision ID: e1ce459e2156
Revises: e2b7c9d4f1a6
Create Date: 2026-11-16 20:07:03.084179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1ce459e2156'
down_revision: Union[str, Sequence[str], None] = 'e2b7c9d4f1a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate does not detect new values on an existing Postgres enum.
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'SLEEPING'")
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'WAKING'")

    op.add_column('deployments', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))

    # Apps already running count as active now, so none is put to sleep right away.
    op.execute("UPDATE deployments SET last_active_at = now() WHERE status = 'RUNNING'")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deployments', 'last_active_at')
    # Postgres cannot drop a value from an enum type; the unused values are harmless.
