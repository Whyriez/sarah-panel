from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    domain = Column(String, unique=True, index=True)
    type = Column(String)  # php, node, python, static
    app_port = Column(Integer, nullable=True)  # Khusus Node/Python (misal 3001)

    is_active = Column(Boolean, default=True)

    # Relasi balik ke User
    owner = relationship("app.modules.users.models.User")

    # Info Git
    repo_url = Column(String, nullable=True)  # https://github.com/alim/my-project.git
    branch = Column(String, default="main")  # main / master
    auto_deploy = Column(Boolean, default=False)