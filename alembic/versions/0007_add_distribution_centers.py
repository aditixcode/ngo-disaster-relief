"""add distribution centers table

Revision ID: 0007_add_distribution_centers
Revises: 0006_add_beneficiaries
Create Date: 2026-09-18 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0007_add_distribution_centers'
down_revision: Union[str, None] = '0006_add_beneficiaries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'distribution_centers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('contact_number', sa.String(length=50), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'INACTIVE', 'FULL', name='center_status'),
            nullable=False,
            server_default='ACTIVE',
        ),
        sa.Column('operating_hours', sa.String(length=100), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('disaster_id', 'name', name='uq_center_disaster_name'),
    )
    op.create_index(op.f('ix_distribution_centers_id'), 'distribution_centers', ['id'], unique=False)
    op.create_index(op.f('ix_distribution_centers_disaster_id'), 'distribution_centers', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_distribution_centers_name'), 'distribution_centers', ['name'], unique=False)
    op.create_index(op.f('ix_distribution_centers_status'), 'distribution_centers', ['status'], unique=False)
    op.create_index(op.f('ix_distribution_centers_created_by_id'), 'distribution_centers', ['created_by_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_distribution_centers_created_by_id'), table_name='distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_status'), table_name='distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_name'), table_name='distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_disaster_id'), table_name='distribution_centers')
    op.drop_index(op.f('ix_distribution_centers_id'), table_name='distribution_centers')
    op.drop_table('distribution_centers')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS center_status')
