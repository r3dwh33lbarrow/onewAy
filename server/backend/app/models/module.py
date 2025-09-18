from sqlalchemy import JSON, Column, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class Module(Base):
    """
    Represents a deployable module in the red-team system.

    Stores metadata about the module such as its name, description, version,
    startup command, and associated binaries. Modules can be linked to clients
    through the ClientModule association table.
    """

    __tablename__ = "modules"

    name = Column(String, primary_key=True, index=True)
    description = Column(String)
    version = Column(String, nullable=False)
    start = Column(String, nullable=False)
    binaries = Column(JSON)
    client_modules = relationship("ClientModule", back_populates="module")
