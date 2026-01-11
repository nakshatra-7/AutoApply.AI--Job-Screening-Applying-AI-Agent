"""agent_runs_uuid_default

Revision ID: defcbcde8655
Revises: 7d7d63e92f2d
Create Date: 2025-12-27 14:54:32.268858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'defcbcde8655'
down_revision: Union[str, Sequence[str], None] = '7d7d63e92f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.alter_column(
        "agent_runs",
        "id",
        existing_type=postgresql.UUID(),
        server_default=sa.text("gen_random_uuid()"),
        existing_nullable=False,
    )

def downgrade():
    op.alter_column(
        "agent_runs",
        "id",
        existing_type=postgresql.UUID(),
        server_default=None,
        existing_nullable=False,
    )