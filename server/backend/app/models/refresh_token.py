from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, DateTime, ForeignKey, String

from app.db.base import Base


class RefreshToken(Base):
    """
    Represents a refresh token issued to a client.

    Stores the token UUID, client association, JWT ID (jti), issuance and
    expiration timestamps, and revocation status. Tokens are cascaded on
    client deletion.
    """
    __tablename__ = "refresh_tokens"
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jti = Column(String, nullable=False, unique=True)
    issued_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
