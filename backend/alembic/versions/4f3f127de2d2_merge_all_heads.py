"""merge all heads

Revision ID: 4f3f127de2d2
Revises: 4430e23d028d, add_vendor_users_table
Create Date: 2026-06-04 10:08:11.515100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f3f127de2d2'
down_revision: Union[str, Sequence[str], None] = ('4430e23d028d', 'add_vendor_users_table')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
