"""add client platform column

Revision ID: 20241022_add_client_platform
Revises: 7637ae83c185
Create Date: 2025-10-22 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20241022_add_client_platform"
down_revision: Union[str, Sequence[str], None] = "7637ae83c185"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("platform", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "platform")
