"""add skill extended fields

Revision ID: a8f3c912e7d2
Revises: 75d214513e6f
Create Date: 2026-03-30 05:15:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8f3c912e7d2'
down_revision: Union[str, None] = '75d214513e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('skills', sa.Column('version', sa.String(length=50), nullable=False, server_default='0.0.1'))
    op.add_column('skills', sa.Column('permissions', sa.JSON(), nullable=True))
    op.add_column('skills', sa.Column('package_url', sa.String(length=500), nullable=True))
    op.add_column('skills', sa.Column('skill_type', sa.String(length=20), nullable=False, server_default='knowledge'))


def downgrade() -> None:
    op.drop_column('skills', 'skill_type')
    op.drop_column('skills', 'package_url')
    op.drop_column('skills', 'permissions')
    op.drop_column('skills', 'version')
