"""merge heads

Revision ID: a5a1e0f6680e
Revises: 7f866b0ca1e7, ab20260622_indent_bom
Create Date: 2026-06-25 18:48:22.339246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5a1e0f6680e'
down_revision: Union[str, Sequence[str], None] = ('7f866b0ca1e7', 'ab20260622_indent_bom')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
