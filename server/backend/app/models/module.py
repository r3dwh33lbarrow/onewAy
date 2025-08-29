from sqlalchemy import Column, String

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    name = Column(String, primary_key=True, index=True)
    description = Column(String)
    path = Column(String, nullable=False)
    version = Column(String, nullable=False)