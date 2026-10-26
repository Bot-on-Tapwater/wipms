"""labourer gender and birth year

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply this migration."""
    with op.batch_alter_table('labourers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gender', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('birth_year', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Revert this migration."""
    with op.batch_alter_table('labourers', schema=None) as batch_op:
        batch_op.drop_column('birth_year')
        batch_op.drop_column('gender')
