import secrets

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    type = Column(String)  # node, python, php

    # [BARU] Simpan versi PHP (misal: "8.1", "7.4"). Nullable jika type != php
    php_version = Column(String, nullable=True)

    app_port = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="sites")

    # Info Git
    repo_url = Column(String, nullable=True)  # https://github.com/alim/my-project.git
    branch = Column(String, default="main")  # main / master
    auto_deploy = Column(Boolean, default=False)

    startup_command = Column(String, nullable=True)
    webhook_token = Column(String, default=lambda: secrets.token_urlsafe(16))
    framework = Column(String, default="native")  # native, laravel, wordpress, spa, proxy