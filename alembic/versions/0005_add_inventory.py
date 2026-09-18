"""add inventory items table

Revision ID: 0005_add_inventory
Revises: 0004_add_donations
Create Date: 2026-09-18 16:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0005_add_inventory'
down_revision: Union[str, None] = '0004_add_donations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('item_name', sa.String(length=150), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column(
            'status',
            sa.Enum('RECEIVED', 'STORED', 'DISTRIBUTED', name='inventory_status'),
            nullable=False,
            server_default='RECEIVED',
        ),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('stored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['disaster_id'], ['disasters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_inventory_items_id'), 'inventory_items', ['id'], unique=False)
    op.create_index(op.f('ix_inventory_items_disaster_id'), 'inventory_items', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_inventory_items_item_name'), 'inventory_items', ['item_name'], unique=False)
    op.create_index(op.f('ix_inventory_items_status'), 'inventory_items', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inventory_items_status'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_item_name'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_disaster_id'), table_name='inventory_items')
    op.drop_index(op.f('ix_inventory_items_id'), table_name='inventory_items')
    op.drop_table('inventory_items')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS inventory_status')
