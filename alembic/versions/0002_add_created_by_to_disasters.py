"""add created_by to disasters

Revision ID: 0002_add_created_by
Revises: 0001_initial
Create Date: 2026-09-18 16:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_created_by'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('disasters', sa.Column('created_by_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_disasters_created_by_id'), 'disasters', ['created_by_id'], unique=False)
    op.create_foreign_key(
        'fk_disasters_created_by_id_users',
        'disasters',
        'users',
        ['created_by_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_disasters_created_by_id_users', 'disasters', type_='foreignkey')
    op.drop_index(op.f('ix_disasters_created_by_id'), table_name='disasters')
    op.drop_column('disasters', 'created_by_id')
