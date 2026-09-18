"""initial create users and disasters

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-18 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create 'users' table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column(
            'role',
            sa.Enum('ADMIN', 'NGO_STAFF', 'VOLUNTEER', 'DONOR', name='user_role'),
            nullable=False,
            server_default='VOLUNTEER',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Create 'disasters' table
    op.create_table(
        'disasters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'CONTAINED', 'RESOLVED', name='disaster_status'),
            nullable=False,
            server_default='ACTIVE',
        ),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_disasters_id'), 'disasters', ['id'], unique=False)
    op.create_index(op.f('ix_disasters_name'), 'disasters', ['name'], unique=False)


def downgrade() -> None:
    # Drop disasters table and its indices
    op.drop_index(op.f('ix_disasters_name'), table_name='disasters')
    op.drop_index(op.f('ix_disasters_id'), table_name='disasters')
    op.drop_table('disasters')

    # Drop users table and its indices
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

    # Clean up PostgreSQL enum types if applicable
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS user_role')
        op.execute('DROP TYPE IF EXISTS disaster_status')
