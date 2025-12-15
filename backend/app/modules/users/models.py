from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    # Role: admin, reseller, user
    role = Column(String, default="user")

    # System Username: User Linux yang akan dibuatkan (misal: user_alim)
    system_username = Column(String, unique=True, nullable=True)

    is_active = Column(Boolean, default=True)

    sites = relationship("Site", back_populates="owner")