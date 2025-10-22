from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.services.password import pwd_context


class Client(Base):
    """
    Represents an enrolled client in the system.

    Stores authentication details, network identity, operational status,
    and metadata such as hostname, location, and client version.
    Linked to installed modules through the ClientModule association table.
    Provides a method to verify a plaintext password against the stored hash.
    """

    __tablename__ = "clients"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    ip_address = Column(INET, nullable=False)
    hostname = Column(String)
    alive = Column(Boolean, nullable=False, default=False)
    last_contact = Column(DateTime(timezone=True))
    last_known_location = Column(String)
    client_version = Column(String, nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)

    client_modules = relationship(
        "ClientModule",
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)
