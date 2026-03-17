"""add must_change_password to users

Revision ID: a343a2d57177
Revises: 426cd8f53c26
Create Date: 2026-03-17 14:52:11.585193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a343a2d57177'
down_revision: Union[str, Sequence[str], None] = '426cd8f53c26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: add column as nullable with a server default
    op.add_column('users', sa.Column(
        'must_change_password',
        sa.Boolean(),
        nullable=True,
        server_default=sa.text('true')
    ))

    # Step 2: backfill any existing rows (server_default handles it, but explicit is safer)
    op.execute("UPDATE users SET must_change_password = true WHERE must_change_password IS NULL")

    # Step 3: now enforce NOT NULL
    op.alter_column('users', 'must_change_password', nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'must_change_password') 
