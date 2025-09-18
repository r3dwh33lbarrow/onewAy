from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ClientModule(Base):
    """
    Association table between clients and modules.

    Tracks which modules are installed on which clients, along with the
    current status and timestamps for installation and updates.
    """
    __tablename__ = "client_modules"

    client_name = Column(String, ForeignKey("clients.username"), primary_key=True)
    module_name = Column(String, ForeignKey("modules.name"), primary_key=True)

    status = Column(String, nullable=False, default="installed")
    installed_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    last_updated = Column(
        DateTime(timezone=True), onupdate=lambda: datetime.now(UTC)
    )

    client = relationship("Client", back_populates="client_modules")
    module = relationship("Module", back_populates="client_modules")
