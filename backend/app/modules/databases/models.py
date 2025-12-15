from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Database(Base):
    __tablename__ = "databases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String(255), unique=True, index=True)
    db_user = Column(String(255))
    db_password = Column(String(255))

    type = Column(String(50), default="mysql")

    owner = relationship("app.modules.users.models.User")