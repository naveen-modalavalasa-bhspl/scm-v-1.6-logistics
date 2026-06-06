"""merge heads

Revision ID: 10fa46e83853
Revises: 2026_06_01_schema_drift_fixes, ab20260606_read_codes, b121d6b3f6c4
Create Date: 2026-06-06 18:43:14.530697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10fa46e83853'
down_revision: Union[str, Sequence[str], None] = ('2026_06_01_schema_drift_fixes', 'ab20260606_read_codes', 'b121d6b3f6c4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
