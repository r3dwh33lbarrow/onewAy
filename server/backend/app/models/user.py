from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, DateTime, String
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.services.password import pwd_context


class User(Base):
    """
    Represents an application user.

    Stores authentication details, administrative status, timestamps for
    account creation and last login, and an optional avatar path.
    Has a one-to-many relationship with clients (users can own multiple clients).
    Provides a method to verify a plaintext password against the stored hash.
    """

    __tablename__ = "users"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    last_login = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    avatar_path = Column(String)

    clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)
