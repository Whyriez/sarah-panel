from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CronJob(Base):
    __tablename__ = "cron_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String)  # Nama Tugas, misal: "Backup Harian"
    command = Column(String)  # Perintah, misal: "python3 /var/www/script.py"

    # Jadwal (Format Crontab simple)
    schedule = Column(String)  # "0 0 * * *" (Tiap tengah malam)

    is_active = Column(Boolean, default=True)
    last_run = Column(String, nullable=True)  # Waktu terakhir jalan

    owner = relationship("app.modules.users.models.User")