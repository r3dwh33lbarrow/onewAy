from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.services.password import pwd_context


class Client(Base):
    """
    Represents an enrolled client

    Tracks authentication info, IP address, hostname,
    last contact, last known location and the client version
    """
    __tablename__ = "clients"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    hostname = Column(String)
    alive = Column(Boolean, nullable=False, default=False)
    last_contact = Column(DateTime)
    last_known_location = Column(String)
    client_version = Column(String, nullable=False)

    client_modules = relationship("ClientModule", back_populates="client")

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)
