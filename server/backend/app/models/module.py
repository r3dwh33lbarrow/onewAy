from sqlalchemy import Column, String

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    md5_hash = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    path = Column(String, nullable=False)
    version = Column(String, nullable=False)