from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Tambahkan (255) atau panjang lain yang sesuai
    username = Column(String(255), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))

    # Role: admin, reseller, user
    role = Column(String(50), default="user")

    # System Username
    system_username = Column(String(255), unique=True, nullable=True)

    is_active = Column(Boolean, default=True)

    sites = relationship("Site", back_populates="owner")