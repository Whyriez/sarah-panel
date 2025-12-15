from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class CronJob(Base):
    __tablename__ = "cron_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String(255))
    command = Column(String(500)) # Command cron bisa panjang

    schedule = Column(String(100)) # "0 0 * * *"

    is_active = Column(Boolean, default=True)
    last_run = Column(String(100), nullable=True)

    owner = relationship("app.modules.users.models.User")