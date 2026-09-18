"""add donations table

Revision ID: 0004_add_donations
Revises: 0003_add_volunteer_assignments_and_tasks
Create Date: 2026-09-18 16:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004_add_donations'
down_revision: Union[str, None] = '0003_add_volunteer_assignments_and_tasks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'donations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('donor_id', sa.Integer(), nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column(
            'donation_type',
            sa.Enum('MONEY', 'MATERIAL', name='donation_type'),
            nullable=False,
        ),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('item_name', sa.String(length=150), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PLEDGED', 'RECEIVED', 'CANCELLED', name='donation_status'),
            nullable=False,
            server_default='PLEDGED',
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(['donor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_donations_id'), 'donations', ['id'], unique=False)
    op.create_index(op.f('ix_donations_donor_id'), 'donations', ['donor_id'], unique=False)
    op.create_index(op.f('ix_donations_disaster_id'), 'donations', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_donations_donation_type'), 'donations', ['donation_type'], unique=False)
    op.create_index(op.f('ix_donations_status'), 'donations', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_donations_status'), table_name='donations')
    op.drop_index(op.f('ix_donations_donation_type'), table_name='donations')
    op.drop_index(op.f('ix_donations_disaster_id'), table_name='donations')
    op.drop_index(op.f('ix_donations_donor_id'), table_name='donations')
    op.drop_index(op.f('ix_donations_id'), table_name='donations')
    op.drop_table('donations')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS donation_status')
        op.execute('DROP TYPE IF EXISTS donation_type')
