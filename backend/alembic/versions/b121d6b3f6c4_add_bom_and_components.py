"""add_bom_and_components

Revision ID: b121d6b3f6c4
Revises: add_asset_spare_mapping
Create Date: 2026-06-05 17:05:59.380196

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b121d6b3f6c4'
down_revision: Union[str, Sequence[str], None] = 'add_asset_spare_mapping'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('boms',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('bom_code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('project_id', sa.BigInteger(), nullable=True),
    sa.Column('document_types', sa.JSON(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('bom_code')
    )
    op.create_table('bom_components',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('bom_id', sa.BigInteger(), nullable=False),
    sa.Column('item_id', sa.BigInteger(), nullable=False),
    sa.Column('qty', sa.Numeric(precision=15, scale=3), nullable=False),
    sa.Column('uom_id', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['bom_id'], ['boms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
    sa.ForeignKeyConstraint(['uom_id'], ['uom.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('bom_components')
    op.drop_table('boms')
