"""add agent run and step tables

Revision ID: 2e2ff0b5d0a6
Revises: d68eb88f1551
Create Date: 2025-12-13 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e2ff0b5d0a6'
down_revision: Union[str, Sequence[str], None] = 'd68eb88f1551'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('goal', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='planning'),
        sa.Column('fit_score', sa.Float(), nullable=True),
        sa.Column('selected_resume_id', sa.UUID(), nullable=True),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ),
        sa.ForeignKeyConstraint(['selected_resume_id'], ['resumes.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_runs_user_id'), 'agent_runs', ['user_id'], unique=False)

    op.create_table(
        'agent_step_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('step_num', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('tool', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_step_logs_run_id'), 'agent_step_logs', ['run_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_step_logs_run_id'), table_name='agent_step_logs')
    op.drop_table('agent_step_logs')
    op.drop_index(op.f('ix_agent_runs_user_id'), table_name='agent_runs')
    op.drop_table('agent_runs')
