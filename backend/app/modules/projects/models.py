from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(500), nullable=True) # Deskripsi bisa agak panjang
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    panels = relationship("Panel", back_populates="project", cascade="all, delete-orphan")


class Panel(Base):
    __tablename__ = "panels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    url = Column(String(255))
    username = Column(String(255))
    password = Column(String(255))

    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="panels")