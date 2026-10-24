"""timezone-aware timestamps and failed_stage on deployments

Revision ID: c4f1a9e2d7b8
Revises: b7d2e4f19a3c
Create Date: 2026-10-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c4f1a9e2d7b8'
down_revision: Union[str, Sequence[str], None] = 'b7d2e4f19a3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every naive timestamp column; all of them were written in UTC.
TIMESTAMP_COLUMNS = [
    ('users', 'created_at'),
    ('projects', 'created_at'),
    ('deployments', 'created_at'),
    ('deployments', 'updated_at'),
]


def upgrade() -> None:
    """Upgrade schema."""
    for table, column in TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    # Reuse the existing enum type instead of creating a new one.
    op.add_column(
        'deployments',
        sa.Column(
            'failed_stage',
            postgresql.ENUM(name='deploymentstatus', create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('deployments', 'failed_stage')

    for table, column in TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
