"""add volunteer assignments and tasks

Revision ID: 0003_add_volunteer_assignments_and_tasks
Revises: 0002_add_created_by
Create Date: 2026-09-18 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_add_volunteer_assignments_and_tasks'
down_revision: Union[str, None] = '0002_add_created_by'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create volunteer_assignments table
    op.create_table(
        'volunteer_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('volunteer_id', sa.Integer(), nullable=False),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('ACTIVE', 'COMPLETED', name='assignment_status'),
            nullable=False,
            server_default='ACTIVE',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['disaster_id'], ['disasters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['volunteer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('volunteer_id', 'disaster_id', name='uq_volunteer_disaster'),
    )
    op.create_index(op.f('ix_volunteer_assignments_id'), 'volunteer_assignments', ['id'], unique=False)
    op.create_index(op.f('ix_volunteer_assignments_volunteer_id'), 'volunteer_assignments', ['volunteer_id'], unique=False)
    op.create_index(op.f('ix_volunteer_assignments_disaster_id'), 'volunteer_assignments', ['disaster_id'], unique=False)

    # 2. Create volunteer_tasks table
    op.create_table(
        'volunteer_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('disaster_id', sa.Integer(), nullable=False),
        sa.Column('volunteer_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', name='task_status'),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['disaster_id'], ['disasters.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['volunteer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_volunteer_tasks_id'), 'volunteer_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_volunteer_tasks_title'), 'volunteer_tasks', ['title'], unique=False)
    op.create_index(op.f('ix_volunteer_tasks_disaster_id'), 'volunteer_tasks', ['disaster_id'], unique=False)
    op.create_index(op.f('ix_volunteer_tasks_volunteer_id'), 'volunteer_tasks', ['volunteer_id'], unique=False)
    op.create_index(op.f('ix_volunteer_tasks_status'), 'volunteer_tasks', ['status'], unique=False)


def downgrade() -> None:
    # Drop volunteer_tasks
    op.drop_index(op.f('ix_volunteer_tasks_status'), table_name='volunteer_tasks')
    op.drop_index(op.f('ix_volunteer_tasks_volunteer_id'), table_name='volunteer_tasks')
    op.drop_index(op.f('ix_volunteer_tasks_disaster_id'), table_name='volunteer_tasks')
    op.drop_index(op.f('ix_volunteer_tasks_title'), table_name='volunteer_tasks')
    op.drop_index(op.f('ix_volunteer_tasks_id'), table_name='volunteer_tasks')
    op.drop_table('volunteer_tasks')

    # Drop volunteer_assignments
    op.drop_index(op.f('ix_volunteer_assignments_disaster_id'), table_name='volunteer_assignments')
    op.drop_index(op.f('ix_volunteer_assignments_volunteer_id'), table_name='volunteer_assignments')
    op.drop_index(op.f('ix_volunteer_assignments_id'), table_name='volunteer_assignments')
    op.drop_table('volunteer_assignments')

    # Drop enum types if Postgres
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS task_status')
        op.execute('DROP TYPE IF EXISTS assignment_status')
