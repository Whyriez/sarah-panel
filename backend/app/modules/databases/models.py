from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Database(Base):
    __tablename__ = "databases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Nama Database Asli (misal: user_alim_toko)
    name = Column(String, unique=True, index=True)

    # Username Database (misal: user_alim)
    db_user = Column(String)

    # Password Database (Disimpan plain text agar user bisa lihat/copas di panel)
    db_password = Column(String)

    type = Column(String, default="mysql")  # mysql / postgres

    owner = relationship("app.modules.users.models.User")