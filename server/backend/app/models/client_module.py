from datetime import datetime, UTC

from sqlalchemy import Column, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClientModule(Base):
    __tablename__ = "client_modules"

    client_name = Column(String, ForeignKey("clients.username"), primary_key=True)
    module_name = Column(String, ForeignKey("modules.name"), primary_key=True)

    # Relationship-specific fields
    status = Column(String, nullable=False, default="installed")
    installed_at = Column(DateTime, default=lambda : datetime.now(UTC).replace(tzinfo=None))
    last_updated = Column(DateTime, onupdate=lambda : datetime.now(UTC).replace(tzinfo=None))

    # Relationships back to Client and Module
    client = relationship("Client", back_populates="client_modules")
    module = relationship("Module", back_populates="client_modules")
