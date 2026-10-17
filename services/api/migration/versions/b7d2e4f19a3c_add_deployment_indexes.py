"""add deployment indexes and one in-progress deployment per project

Revision ID: b7d2e4f19a3c
Revises: 98a8731560b5
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e4f19a3c'
down_revision: Union[str, Sequence[str], None] = '98a8731560b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_deployments_project_id', 'deployments', ['project_id'])
    op.create_index('ix_deployments_status', 'deployments', ['status'])

    # Existing rows may already break the rule below: keep the newest in-progress
    # deployment of each project and fail the older ones.
    op.execute(
        """
        UPDATE deployments
        SET status = 'FAILED',
            failure_reason = 'Superseded by a newer deployment of this project.'
        WHERE status IN ('QUEUED', 'BUILDING', 'DEPLOYING')
          AND id NOT IN (
              SELECT MAX(id) FROM deployments
              WHERE status IN ('QUEUED', 'BUILDING', 'DEPLOYING')
              GROUP BY project_id
          )
        """
    )

    op.create_index(
        'uq_deployments_one_in_progress_per_project',
        'deployments',
        ['project_id'],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'BUILDING', 'DEPLOYING')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_deployments_one_in_progress_per_project', table_name='deployments')
    op.drop_index('ix_deployments_status', table_name='deployments')
    op.drop_index('ix_deployments_project_id', table_name='deployments')
