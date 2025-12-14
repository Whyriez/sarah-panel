from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.cron import models
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from app.system.cron_manager import reload_jobs_from_db

router = APIRouter(tags=["Cron Jobs"])


class CronCreate(BaseModel):
    name: str
    command: str
    schedule: str  # "* * * * *"


@router.get("/cron")
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(models.CronJob).filter(models.CronJob.user_id == current_user.id).all()


@router.post("/cron")
def create_job(payload: CronCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_job = models.CronJob(
        name=payload.name,
        command=payload.command,
        schedule=payload.schedule,
        user_id=current_user.id
    )
    db.add(new_job)
    db.commit()

    # Reload Scheduler biar job baru langsung jalan
    reload_jobs_from_db(db)

    return new_job


@router.delete("/cron/{id}")
def delete_job(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(models.CronJob).filter(models.CronJob.id == id, models.CronJob.user_id == current_user.id).first()
    if not job: raise HTTPException(404, "Job not found")

    db.delete(job)
    db.commit()

    # Reload
    reload_jobs_from_db(db)

    return {"message": "Job deleted"}