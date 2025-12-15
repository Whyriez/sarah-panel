import secrets
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True)
    type = Column(String(50))  # node, python, php

    php_version = Column(String(10), nullable=True)

    app_port = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="sites")

    # Info Git
    repo_url = Column(String(255), nullable=True)
    branch = Column(String(100), default="main")
    auto_deploy = Column(Boolean, default=False)

    startup_command = Column(String(500), nullable=True) # Command bisa panjang
    webhook_token = Column(String(100), default=lambda: secrets.token_urlsafe(16))
    framework = Column(String(50), default="native")