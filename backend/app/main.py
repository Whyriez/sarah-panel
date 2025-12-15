from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.init_db import init_db

# Import Database & Models
from app.core.database import engine, Base
from app.modules.users import models as user_models
from app.modules.users.router import router as user_router
from app.modules.auth.router import router as auth_router
from app.modules.sites import models as site_models
from app.modules.sites.router import router as site_router
from app.modules.files.router import router as files_router
from app.modules.databases import models as db_models
from app.modules.databases.router import router as db_router
from app.modules.terminal.router import router as term_router
from app.modules.logs.router import router as logs_router
from app.modules.marketplace.router import router as market_router
from app.modules.git.router import router as git_router
from app.modules.backups.router import router as backup_router
from app.system.monitor import get_system_stats
from app.modules.cron import models as cron_models
from app.modules.cron.router import router as cron_router
from app.system.cron_manager import start_scheduler, reload_jobs_from_db
from app.core.database import SessionLocal # Perlu ini buat load awal
from app.modules.projects import models as project_models
from app.modules.projects.router import router as project_router

# --- AUTO MIGRATE (Buat tabel kalau belum ada) ---
user_models.Base.metadata.create_all(bind=engine)
cron_models.Base.metadata.create_all(bind=engine)
project_models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AlimPanel API", version="0.1.0")

# --- CORS ---
origins = [
    "http://localhost:3000",      # Frontend Localhost
    "http://127.0.0.1:3000",      # Frontend Localhost IP
    "https://sarahpanel.limapp.my.id" # GANTI INI dengan domain panel frontend nanti
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Jangan pernah pakai ["*"] di production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], # Batasi method juga kalau perlu
    allow_headers=["*"],
)

# Auto Migrate Tabel Sites
site_models.Base.metadata.create_all(bind=engine)
db_models.Base.metadata.create_all(bind=engine)
cron_models.Base.metadata.create_all(bind=engine)

# --- Register Router ---
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(site_router)
app.include_router(files_router)
app.include_router(db_router)
app.include_router(term_router)
app.include_router(logs_router)
app.include_router(market_router)
app.include_router(git_router)
app.include_router(backup_router)
app.include_router(cron_router)
app.include_router(project_router)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()

    try:
        # 1. START SCHEDULER
        start_scheduler()
        reload_jobs_from_db(db)

        # 2. CREATE SUPERUSER (Auto Generate)
        init_db(db)

    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "SarahPanel API is Ready!"}

@app.get("/monitor")
def get_monitor_data():
    data = get_system_stats()
    return {"status": "success", "data": data}