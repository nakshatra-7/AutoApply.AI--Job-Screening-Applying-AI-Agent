"""add user facts

Revision ID: 7d7d63e92f2d
Revises: 2e2ff0b5d0a6
Create Date: 2025-12-13 01:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d7d63e92f2d'
down_revision: Union[str, Sequence[str], None] = '2e2ff0b5d0a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_facts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False, server_default='user_confirmed'),
        sa.Column('last_confirmed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'key')
    )
    op.create_index(op.f('ix_user_facts_key'), 'user_facts', ['key'], unique=False)
    op.create_index(op.f('ix_user_facts_user_id'), 'user_facts', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_facts_user_id'), table_name='user_facts')
    op.drop_index(op.f('ix_user_facts_key'), table_name='user_facts')
    op.drop_table('user_facts')
