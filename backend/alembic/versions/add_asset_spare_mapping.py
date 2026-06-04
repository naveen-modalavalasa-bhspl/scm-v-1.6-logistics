"""add asset spare mapping table

Revision ID: add_asset_spare_mapping
Revises: 4f3f127de2d2
Create Date: 2026-06-04 11:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_asset_spare_mapping'
down_revision: Union[str, Sequence[str], None] = '4f3f127de2d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_spare_mappings",
        sa.Column("id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("asset_id", sa.BigInteger(), nullable=False),
        sa.Column("spare_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_id"], ["items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spare_id"], ["items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("asset_id", "spare_id", name="uq_asset_spare")
    )


def downgrade() -> None:
    op.drop_table("asset_spare_mappings")
