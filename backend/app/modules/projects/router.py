from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db # Ambil get_db dari core anda
from . import models, schemas

# Setup Router
router = APIRouter(
    prefix="/projects",
    tags=["Projects Management"]
)

# 1. Create Project
@router.post("/", response_model=schemas.ProjectResponse)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    db_project = models.Project(name=project.name, description=project.description)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

# 2. Get All Projects (Nested dengan Panel)
@router.get("/", response_model=List[schemas.ProjectResponse])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    projects = db.query(models.Project).offset(skip).limit(limit).all()
    return projects

# 3. Create Panel for specific Project
@router.post("/{project_id}/panels/", response_model=schemas.PanelResponse)
def create_panel(project_id: int, panel: schemas.PanelCreate, db: Session = Depends(get_db)):
    # Cek Project ada atau tidak
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Buat Panel
    db_panel = models.Panel(**panel.dict(), project_id=project_id)
    db.add(db_panel)
    db.commit()
    db.refresh(db_panel)
    return db_panel

# 4. Get Single Project
@router.get("/{project_id}", response_model=schemas.ProjectResponse)
def read_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project