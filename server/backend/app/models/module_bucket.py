from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import UUID, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class ModuleBucket(Base):
    __tablename__ = "module_bucket"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    module_name = Column(
        String,
        ForeignKey("modules.name", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    module = relationship("Module", back_populates="bucket")
    entries = relationship(
        "ModuleBucketEntry",
        back_populates="bucket",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ModuleBucketEntry(Base):
    __tablename__ = "module_bucket_entry"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    data = Column(Text, nullable=False, default="")
    remove_at = Column(DateTime(timezone=True), nullable=True)

    bucket_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("module_bucket.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.uuid", ondelete="SET NULL"),
        nullable=True,
    )

    bucket = relationship("ModuleBucket", back_populates="entries")
    client = relationship("Client", back_populates="bucket_entries")

    def consume(self) -> None:
        self.remove_at = datetime.now(UTC) + timedelta(days=3)
