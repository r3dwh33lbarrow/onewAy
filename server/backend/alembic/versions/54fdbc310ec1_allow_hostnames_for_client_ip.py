"""allow hostnames for client ip

Revision ID: 54fdbc310ec1
Revises: ea3268ba52eb
Create Date: 2025-11-05 14:27:54.851524

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "54fdbc310ec1"
down_revision: Union[str, Sequence[str], None] = "ea3268ba52eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "clients",
        "ip_address",
        existing_type=postgresql.INET(),
        type_=sa.String(length=253),
        existing_nullable=True,
        postgresql_using="ip_address::TEXT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "clients",
        "ip_address",
        existing_type=sa.String(length=253),
        type_=postgresql.INET(),
        existing_nullable=True,
        postgresql_using="ip_address::INET",
    )
