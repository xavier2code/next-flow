"""add conversation agent_id

Revision ID: 9c7e8d2f1a3b
Revises: a8f3c912e7d2
Create Date: 2026-03-31 14:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c7e8d2f1a3b'
down_revision: Union[str, None] = 'a8f3c912e7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversations',
        sa.Column('agent_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_conversations_agent_id',
        'conversations', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_conversations_agent_id',
        'conversations',
        ['agent_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_conversations_agent_id', table_name='conversations')
    op.drop_constraint('fk_conversations_agent_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'agent_id')
