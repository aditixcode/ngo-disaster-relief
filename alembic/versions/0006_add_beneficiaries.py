"""add beneficiaries table

Revision ID: 0006_add_beneficiaries
Revises: 0005_add_inventory
Create Date: 2026-09-18 16:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0006_add_beneficiaries'
down_revision: Union[str, None] = '0005_add_inventory'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'beneficiaries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('contact_number', sa.String(length=50), nullable=False),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('household_size', sa.Integer(), nullable=False),
        sa.Column(
            'vulnerability_category',
            sa.Enum(
                'GENERAL',
                'CHILDREN',
                'ELDERLY',
                'DISABLED',
                'PREGNANT',
                'LOW_INCOME',
                name='vulnerability_category',
            ),
            nullable=False,
            server_default='GENERAL',
        ),
        sa.Column(
            'registration_status',
            sa.Enum(
                'PENDING',
                'VERIFIED',
                'INACTIVE',
                name='registration_status',
            ),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('registered_by_id', sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(['registered_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('disaster_id', 'name', 'contact_number', name='uq_beneficiary_disaster_name_contact'),
    )
    op.create_index(op.f('ix_beneficiaries_id'), 'beneficiaries', ['id'], unique=False)
    op.create_index(op.f('ix_beneficiaries_disaster_id'), 'beneficiaries', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_beneficiaries_name'), 'beneficiaries', ['name'], unique=False)
    op.create_index(op.f('ix_beneficiaries_registration_status'), 'beneficiaries', ['registration_status'], unique=False)
    op.create_index(op.f('ix_beneficiaries_registered_by_id'), 'beneficiaries', ['registered_by_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_beneficiaries_registered_by_id'), table_name='beneficiaries')
    op.drop_index(op.f('ix_beneficiaries_registration_status'), table_name='beneficiaries')
    op.drop_index(op.f('ix_beneficiaries_name'), table_name='beneficiaries')
    op.drop_index(op.f('ix_beneficiaries_disaster_id'), table_name='beneficiaries')
    op.drop_index(op.f('ix_beneficiaries_id'), table_name='beneficiaries')
    op.drop_table('beneficiaries')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS registration_status')
        op.execute('DROP TYPE IF EXISTS vulnerability_category')
