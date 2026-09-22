"""add clipper projects and job mode

Revision ID: 7ecbe3907e34
Revises: b3ed8ab7f4d1
Create Date: 2026-09-22 22:56:04.966536

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ecbe3907e34'
down_revision: Union[str, Sequence[str], None] = 'b3ed8ab7f4d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    clipper_projects = op.create_table(
        'clipper_projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Every ClipJob must belong to a project; existing jobs (if any) are
    # backfilled into a "Default" project created here.
    op.bulk_insert(
        clipper_projects,
        [{"id": 1, "name": "Default", "created_at": datetime.now(timezone.utc)}],
    )
    op.execute("SELECT setval(pg_get_serial_sequence('clipper_projects', 'id'), 1)")

    op.add_column('clip_jobs', sa.Column('project_id', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('clip_jobs', sa.Column('mode', sa.String(length=20), nullable=False, server_default='auto'))
    op.alter_column('clip_jobs', 'project_id', server_default=None)
    op.alter_column('clip_jobs', 'mode', server_default=None)
    op.create_foreign_key('fk_clip_jobs_project_id', 'clip_jobs', 'clipper_projects', ['project_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_clip_jobs_project_id', 'clip_jobs', type_='foreignkey')
    op.drop_column('clip_jobs', 'mode')
    op.drop_column('clip_jobs', 'project_id')
    op.drop_table('clipper_projects')
