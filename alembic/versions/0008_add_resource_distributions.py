"""add resource distributions and original quantity to inventory

Revision ID: 0008_add_resource_distributions
Revises: 0007_add_distribution_centers
Create Date: 2026-09-18 17:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0008_add_resource_distributions'
down_revision: Union[str, None] = '0007_add_distribution_centers'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add original_quantity to inventory_items
    op.add_column('inventory_items', sa.Column('original_quantity', sa.Float(), nullable=True))
    op.execute('UPDATE inventory_items SET original_quantity = quantity WHERE original_quantity IS NULL')

    # 2. Create resource_distributions table
    op.create_table(
        'resource_distributions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('inventory_item_id', sa.Integer(), nullable=False),
        sa.Column('beneficiary_id', sa.Integer(), nullable=False),
        sa.Column('distribution_center_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=False),
        sa.Column('item_name', sa.String(length=150), nullable=False),
        sa.Column('distributed_by_id', sa.Integer(), nullable=True),
        sa.Column('distributed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['disaster_id'], ['disasters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inventory_item_id'], ['inventory_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['beneficiary_id'], ['beneficiaries.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['distribution_center_id'], ['distribution_centers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['distributed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resource_distributions_id'), 'resource_distributions', ['id'], unique=False)
    op.create_index(op.f('ix_resource_distributions_disaster_id'), 'resource_distributions', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_resource_distributions_inventory_item_id'), 'resource_distributions', ['inventory_item_id'], unique=False)
    op.create_index(op.f('ix_resource_distributions_beneficiary_id'), 'resource_distributions', ['beneficiary_id'], unique=False)
    op.create_index(op.f('ix_resource_distributions_distribution_center_id'), 'resource_distributions', ['distribution_center_id'], unique=False)
    op.create_index(op.f('ix_resource_distributions_item_name'), 'resource_distributions', ['item_name'], unique=False)
    op.create_index(op.f('ix_resource_distributions_distributed_by_id'), 'resource_distributions', ['distributed_by_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_resource_distributions_distributed_by_id'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_item_name'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_distribution_center_id'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_beneficiary_id'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_inventory_item_id'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_disaster_id'), table_name='resource_distributions')
    op.drop_index(op.f('ix_resource_distributions_id'), table_name='resource_distributions')
    op.drop_table('resource_distributions')

    op.drop_column('inventory_items', 'original_quantity')
