"""add_ref_gate_pass_id_to_gate_passes

Revision ID: 7f866b0ca1e7
Revises: ee3ec3854658
Create Date: 2026-06-23

Add optional ref_gate_pass_id to gate_passes so an outward gate pass can
reference the originating inward gate pass (e.g. a vehicle that came in
under GP-IN-00000001 and is now leaving under GP-OUT-00000001 with the
inward pass linked for full traceability).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7f866b0ca1e7'
down_revision = 'ee3ec3854658'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('gate_passes', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('ref_gate_pass_id', sa.BigInteger(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_gate_passes_ref_gate_pass_id',
            'gate_passes',
            ['ref_gate_pass_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('gate_passes', schema=None) as batch_op:
        batch_op.drop_constraint('fk_gate_passes_ref_gate_pass_id', type_='foreignkey')
        batch_op.drop_column('ref_gate_pass_id')
