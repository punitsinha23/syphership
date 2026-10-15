"""add STOPPED deployment status

Revision ID: 98a8731560b5
Revises: 0ca733e1ca04
Create Date: 2026-10-15 23:53:36.982362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98a8731560b5'
down_revision: Union[str, Sequence[str], None] = '0ca733e1ca04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate does not detect new values on an existing Postgres enum.
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'STOPPED'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres cannot drop a value from an enum type; the unused value is harmless.
    pass
