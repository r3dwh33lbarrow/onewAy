"""split bucket data per client

Revision ID: ea3268ba52eb
Revises: 7eee33c80d0a
Create Date: 2025-10-28 14:39:57.946715

"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea3268ba52eb"
down_revision: Union[str, Sequence[str], None] = "7eee33c80d0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


module_bucket_table = sa.table(
    "module_bucket",
    sa.column("uuid", sa.UUID()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("data", sa.Text()),
    sa.column("remove_at", sa.DateTime(timezone=True)),
    sa.column("client_uuid", sa.UUID()),
)

module_bucket_entry_table = sa.table(
    "module_bucket_entry",
    sa.column("uuid", sa.UUID()),
    sa.column("bucket_uuid", sa.UUID()),
    sa.column("client_uuid", sa.UUID()),
    sa.column("data", sa.Text()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("remove_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(sa.text("DROP TABLE IF EXISTS module_bucket_entry"))
    op.create_table(
        "module_bucket_entry",
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", sa.Text(), nullable=False, server_default=""),
        sa.Column("remove_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bucket_uuid", sa.UUID(), nullable=False),
        sa.Column("client_uuid", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bucket_uuid"], ["module_bucket.uuid"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["client_uuid"], ["clients.uuid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_module_bucket_entry_uuid"),
        "module_bucket_entry",
        ["uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_module_bucket_entry_bucket_uuid"),
        "module_bucket_entry",
        ["bucket_uuid"],
        unique=False,
    )

    bind = op.get_bind()
    results = bind.execute(sa.select(module_bucket_table)).fetchall()

    for row in results:
        entry_uuid = uuid.uuid4()
        created_at = row.created_at or datetime.now(timezone.utc)
        data_value = row.data or ""

        bind.execute(
            module_bucket_entry_table.insert().values(
                uuid=entry_uuid,
                bucket_uuid=row.uuid,
                client_uuid=row.client_uuid,
                data=data_value,
                created_at=created_at,
                remove_at=row.remove_at,
            )
        )

    op.drop_constraint(
        op.f("module_bucket_client_uuid_fkey"),
        "module_bucket",
        type_="foreignkey",
    )
    op.drop_column("module_bucket", "client_uuid")
    op.drop_column("module_bucket", "remove_at")
    op.drop_column("module_bucket", "data")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "module_bucket",
        sa.Column(
            "data", sa.TEXT(), autoincrement=False, nullable=False, server_default=""
        ),
    )
    op.alter_column("module_bucket", "data", server_default=None)
    op.add_column(
        "module_bucket",
        sa.Column(
            "remove_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "module_bucket",
        sa.Column("client_uuid", sa.UUID(), autoincrement=False, nullable=True),
    )
    op.create_foreign_key(
        op.f("module_bucket_client_uuid_fkey"),
        "module_bucket",
        "clients",
        ["client_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )

    bind = op.get_bind()
    results = bind.execute(sa.select(module_bucket_entry_table)).fetchall()

    for row in results:
        bind.execute(
            sa.update(module_bucket_table)
            .where(module_bucket_table.c.uuid == row.bucket_uuid)
            .values(
                data=row.data,
                remove_at=row.remove_at,
                client_uuid=row.client_uuid,
            )
        )

    op.drop_index(
        op.f("ix_module_bucket_entry_bucket_uuid"),
        table_name="module_bucket_entry",
    )
    op.drop_index(op.f("ix_module_bucket_entry_uuid"), table_name="module_bucket_entry")
    op.drop_table("module_bucket_entry")
