from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from app.system.pm2_manager import start_app, delete_app, reload_app
from app.system.nginx_manager import create_nginx_config, delete_nginx_config
from app.core.database import get_db
from app.modules.sites import models, schemas
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from dotenv import dotenv_values
import subprocess
from pydantic import BaseModel
import shutil

# Konstanta Folder
SITES_BASE_DIR = "/var/www/sarahpanel"

router = APIRouter(
    prefix="/sites",
    tags=["Sites"]
)

class UpdatePortRequest(BaseModel):
    new_port: int


def get_available_port(db: Session, start_port=3000):
    """
    Mencari port yang belum dipakai di database.
    """
    used_ports_query = db.query(models.Site.app_port).filter(models.Site.app_port != None).all()
    used_ports = [p[0] for p in used_ports_query]

    current_port = start_port
    while True:
        if current_port not in used_ports:
            return current_port
        current_port += 1


# 1. GET ALL SITES
@router.get("/", response_model=list[schemas.SiteResponse])
def read_sites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # [FIX] Admin TIDAK BOLEH melihat punya orang lain.
    # Kita hapus pengecekan role admin. Semua user hanya lihat punya sendiri.
    return db.query(models.Site).filter(models.Site.user_id == current_user.id).all()


# 2. CREATE SITE
@router.post("/", response_model=schemas.SiteResponse)
def create_site(site: schemas.SiteCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    # Cek duplikasi domain (Global check, tetap harus unik satu server)
    existing_site = db.query(models.Site).filter(models.Site.domain == site.domain).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Domain already exists")

    assigned_port = None
    if site.type in ["node", "python"]:
        assigned_port = get_available_port(db)

    new_site = models.Site(
        domain=site.domain,
        type=site.type,
        user_id=current_user.id, # Milik user yang login
        app_port=assigned_port
    )

    db.add(new_site)
    db.commit()
    db.refresh(new_site)

    # 1. Buat Folder
    base_dir = os.path.join(SITES_BASE_DIR, new_site.domain)
    os.makedirs(base_dir, exist_ok=True)

    # 2. Buat File Dummy
    script_filename = "app.py" if new_site.type == "python" else "index.js"
    script_path = os.path.join(base_dir, script_filename)

    if not os.path.exists(script_path):
        with open(script_path, "w") as f:
            if new_site.type == "python":
                f.write("# Dummy Python App\nprint('Hello AlimPanel')")
            else:
                f.write("// Dummy Node App\nconst http = require('http');\nconst server = http.createServer((req, res) => { res.writeHead(200); res.end('Hello SarahPanel!'); });\nserver.listen(process.env.PORT || 3000);")

    # 3. Start PM2 & Nginx
    if new_site.type in ["node", "python"] and new_site.app_port:
        success, msg = start_app(
            domain=new_site.domain,
            port=new_site.app_port,
            script_path=script_path
        )
        if success:
            create_nginx_config(new_site.domain, new_site.app_port, new_site.type)
        else:
            print(f"⚠️ Failed to start app: {msg}")

    return new_site


# Helper untuk mencari site milik user (Mencegah IDOR)
def get_user_site(site_id: int, user_id: int, db: Session):
    site = db.query(models.Site).filter(
        models.Site.id == site_id,
        models.Site.user_id == user_id  # [FIX] Wajib filter by User ID
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.delete("/{site_id}")
def delete_site(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Gunakan helper secure
    site = get_user_site(site_id, current_user.id, db)

    # Cleanup System
    if site.type in ["node", "python"]:
        delete_app(site.domain)

    delete_nginx_config(site.domain)

    # Cleanup Files
    site_path = os.path.join(SITES_BASE_DIR, site.domain)
    if os.path.exists(site_path):
        try:
            shutil.rmtree(site_path)
        except Exception as e:
            print(f"⚠️ Failed to delete folder: {e}")

    db.delete(site)
    db.commit()

    return {"message": f"Site {site.domain} deleted successfully"}


@router.get("/{site_id}/env")
def get_site_env(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # [FIX] Secure Get (sebelumnya siapa saja bisa lihat env orang lain asal tau ID)
    site = get_user_site(site_id, current_user.id, db)

    env_path = os.path.join(SITES_BASE_DIR, site.domain, ".env")

    if not os.path.exists(env_path):
        return {"env": []}

    config = dotenv_values(env_path)
    return {"env": [{"key": k, "value": v} for k, v in config.items()]}


@router.post("/{site_id}/env")
def save_site_env(
        site_id: int,
        payload: dict,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # [FIX] Secure Get
    site = get_user_site(site_id, current_user.id, db)

    env_path = os.path.join(SITES_BASE_DIR, site.domain, ".env")

    with open(env_path, "w") as f:
        for item in payload['env']:
            if item['key']:
                f.write(f"{item['key']}={item['value']}\n")

    if site.type in ['node', 'python']:
        reload_app(site.domain)

    return {"message": "Environment variables saved & App restarted!"}


@router.post("/{site_id}/ssl")
def enable_ssl(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # [FIX] Secure Get
    site = get_user_site(site_id, current_user.id, db)

    import platform
    if platform.system() == "Windows":
        import time
        time.sleep(2)
        return {"message": "[SIMULATION] SSL Certificate issued for " + site.domain}

    try:
        cmd = [
            "sudo",
            "certbot", "--nginx",
            "-d", site.domain,
            "--non-interactive",
            "--agree-tos",
            "-m", "admin@alimpanel.com"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise HTTPException(500, detail=f"Certbot Error: {result.stderr}")

        return {"message": "SSL Certificate Installed Successfully!"}

    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.put("/{site_id}/port")
def update_site_port(
        site_id: int,
        payload: UpdatePortRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # [FIX] Secure Get (Admin juga tidak boleh edit port punya orang lain)
    site = get_user_site(site_id, current_user.id, db)

    # Cek bentrok port
    existing = db.query(models.Site).filter(models.Site.app_port == payload.new_port).first()
    if existing and existing.id != site.id:
        raise HTTPException(400, "Port already used by another site")

    old_port = site.app_port
    site.app_port = payload.new_port
    db.commit()

    # Update System
    create_nginx_config(site.domain, site.app_port, site.type)

    if site.type in ['node', 'python']:
        delete_app(site.domain)
        base_dir = os.path.join(SITES_BASE_DIR, site.domain)
        script = "app.py" if site.type == "python" else "index.js"
        start_app(site.domain, site.app_port, os.path.join(base_dir, script))

    return {"message": f"Port changed from {old_port} to {site.app_port}"}