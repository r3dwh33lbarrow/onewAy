from datetime import datetime, UTC, timedelta

from sqlalchemy import Column, UUID, DateTime, Text, String, ForeignKey
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.base import Base


class ModuleBucket(Base):
    __tablename__ = "module_bucket"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), default=datetime.now(UTC))
    data = Column(Text, nullable=False, default="")
    remove_at = Column(DateTime(timezone=True), nullable=True)

    module_name = Column(
        String,
        ForeignKey("modules.name", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    module = relationship("Module", back_populates="bucket")

    def consume(self) -> None:
        self.remove_at = datetime.now(UTC) + timedelta(days=3)
