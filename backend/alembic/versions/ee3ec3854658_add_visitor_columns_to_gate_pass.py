"""add_visitor_columns_to_gate_pass

Revision ID: ee3ec3854658
Revises: ab20260616_uw_role
Create Date: 2026-06-23 13:42:11.218583

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee3ec3854658'
down_revision: Union[str, Sequence[str], None] = 'ab20260616_uw_role'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('gate_passes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('visitor_type', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('visitor_details', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('gate_passes', schema=None) as batch_op:
        batch_op.drop_column('visitor_details')
        batch_op.drop_column('visitor_type')
