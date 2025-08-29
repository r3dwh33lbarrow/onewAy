from sqlalchemy import Column, String, JSON

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    name = Column(String, primary_key=True, index=True)
    description = Column(String)
    version = Column(String, nullable=False)
    binaries = Column(JSON)