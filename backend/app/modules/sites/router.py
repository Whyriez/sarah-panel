from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from app.system.pm2_manager import start_app
from app.system.nginx_manager import create_nginx_config
from app.core.database import get_db
from app.modules.sites import models, schemas
from app.modules.auth.deps import get_current_user
from app.system.pm2_manager import delete_app
from app.modules.users.models import User
from dotenv import dotenv_values
import subprocess
from pydantic import BaseModel

router = APIRouter(
    prefix="/sites",
    tags=["Sites"]
)

class UpdatePortRequest(BaseModel):
    new_port: int


def get_available_port(db: Session, start_port=3000):
    """
    Mencari port yang belum dipakai di database.
    Mulai cek dari 3000, kalau ada lanjut 3001, dst.
    """
    # Ambil semua port yang terdaftar di DB
    used_ports_query = db.query(models.Site.app_port).filter(models.Site.app_port != None).all()
    # Ratakan list (karena hasil query berupa tuple) -> [3000, 3002, 3005]
    used_ports = [p[0] for p in used_ports_query]

    current_port = start_port
    while True:
        if current_port not in used_ports:
            return current_port  # Ketemu yang kosong!
        current_port += 1


# 1. GET ALL SITES (Hanya milik user yang login)
@router.get("/", response_model=list[schemas.SiteResponse])
def read_sites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # LOGIC MULTIROLE
    if current_user.role == "admin":
        # Kalau Admin, kembalikan SEMUA data
        return db.query(models.Site).all()
    else:
        # Kalau User biasa, kembalikan data MILIK SENDIRI
        return db.query(models.Site).filter(models.Site.user_id == current_user.id).all()


# 2. CREATE SITE
@router.post("/", response_model=schemas.SiteResponse)
def create_site(site: schemas.SiteCreate, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    # Cek apakah domain sudah ada (di seluruh server)
    existing_site = db.query(models.Site).filter(models.Site.domain == site.domain).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Domain already exists")

    # LOGIC PORT ALLOCATOR (Sederhana dulu)
    # Jika tipe Node/Python, kita kasih port random/urut (nanti kita bikin logic canggihnya)
    assigned_port = None
    if site.type in ["node", "python"]:
        # [FIX] Jangan hardcode 3000 lagi! Cari yang kosong.
        assigned_port = get_available_port(db)

    new_site = models.Site(
        domain=site.domain,
        type=site.type,
        user_id=current_user.id,
        app_port=assigned_port
    )

    db.add(new_site)
    db.commit()
    db.refresh(new_site)

    # 1. BUAT FOLDER WEBSITE
    # Di Linux biasanya: /var/www/domain.com
    # Di Windows Dev: backend/www/domain.com
    base_dir = os.path.join(os.getcwd(), "www_data", new_site.domain)
    os.makedirs(base_dir, exist_ok=True)

    # Buat file dummy 'index.js' atau 'app.py' biar gak kosong
    script_filename = "app.py" if new_site.type == "python" else "index.js"
    script_path = os.path.join(base_dir, script_filename)

    if not os.path.exists(script_path):
        with open(script_path, "w") as f:
            if new_site.type == "python":
                f.write("# Dummy Python App\nprint('Hello AlimPanel')")
            else:
                f.write("// Dummy Node App\nconsole.log('Hello AlimPanel');")

    # 2. JALANKAN VIA PM2 (Khusus Node/Python)
    if new_site.type in ["node", "python"] and new_site.app_port:
        success, msg = start_app(
            domain=new_site.domain,
            port=new_site.app_port,
            script_path=script_path
        )
        if success:
            print(f"✅ App {new_site.domain} started on port {new_site.app_port}")
        else:
            print(f"⚠️ Failed to start app: {msg}")

    return new_site


@router.delete("/{site_id}")
def delete_site(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Cari Site
    site = db.query(models.Site).filter(models.Site.id == site_id, models.Site.user_id == current_user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # 2. Hapus Process PM2 (Kalau ada)
    if site.type in ["node", "python"]:
        delete_app(site.domain)

    # 3. Hapus Config Nginx (Simulasi hapus file)
    # (Di Windows hapus file di generated_configs)
    conf_path = os.path.join(os.getcwd(), "generated_configs", f"{site.domain}.conf")
    if os.path.exists(conf_path):
        os.remove(conf_path)

    # 4. Hapus dari Database
    db.delete(site)
    db.commit()

    return {"message": f"Site {site.domain} deleted successfully"}


@router.get("/{site_id}/env")
def get_site_env(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(models.Site).filter(models.Site.id == site_id).first()
    if not site: raise HTTPException(404, "Site not found")

    # Path: backend/www_data/domain.com/.env
    env_path = os.path.join(os.getcwd(), "www_data", site.domain, ".env")

    if not os.path.exists(env_path):
        return {"env": []}  # Kosong

    # Baca .env jadi Dictionary
    config = dotenv_values(env_path)
    # Convert ke Array biar enak di Frontend: [{key: "DB_HOST", value: "localhost"}]
    return {"env": [{"key": k, "value": v} for k, v in config.items()]}


@router.post("/{site_id}/env")
def save_site_env(
        site_id: int,
        payload: dict,  # { "env": [{"key": "A", "value": "B"}] }
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    site = db.query(models.Site).filter(models.Site.id == site_id).first()
    if not site: raise HTTPException(404, "Site not found")

    env_path = os.path.join(os.getcwd(), "www_data", site.domain, ".env")

    # Tulis ulang file .env
    with open(env_path, "w") as f:
        for item in payload['env']:
            if item['key']:  # Skip key kosong
                f.write(f"{item['key']}={item['value']}\n")

    # Restart App biar efeknya jalan (Penting!)
    if site.type in ['node', 'python']:
        from app.system.pm2_manager import reload_app
        reload_app(site.domain)

    return {"message": "Environment variables saved & App restarted!"}


# --- FITUR 2: SSL MANAGER (CERTBOT) ---

@router.post("/{site_id}/ssl")
def enable_ssl(site_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    site = db.query(models.Site).filter(models.Site.id == site_id).first()
    if not site: raise HTTPException(404, "Site not found")

    # Cek OS
    import platform
    if platform.system() == "Windows":
        # Simulasi Windows
        import time
        time.sleep(2)  # Pura-pura mikir
        return {"message": "[SIMULATION] SSL Certificate issued for " + site.domain}

    # Logic Linux (Real Certbot)
    try:
        # Command: certbot --nginx -d domain.com --non-interactive --agree-tos -m admin@example.com
        cmd = [
            "certbot", "--nginx",
            "-d", site.domain,
            "--non-interactive",
            "--agree-tos",
            "-m", "admin@alimpanel.com"  # Nanti bisa ambil email user
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
    # 1. Cari Site (Pastikan punya user sendiri / admin)
    query = db.query(models.Site).filter(models.Site.id == site_id)
    if current_user.role != "admin":
        query = query.filter(models.Site.user_id == current_user.id)

    site = query.first()
    if not site: raise HTTPException(404, "Site not found")

    # 2. Cek apakah port baru bentrok dengan site LAIN?
    existing = db.query(models.Site).filter(models.Site.app_port == payload.new_port).first()
    if existing and existing.id != site.id:
        raise HTTPException(400, "Port already used by another site")

    old_port = site.app_port
    site.app_port = payload.new_port
    db.commit()

    # 3. Update Konfigurasi System (Nginx & PM2)
    # Karena port berubah, Nginx harus tau port baru, dan PM2 harus restart di port baru.

    # A. Regenerate Nginx
    from app.system.nginx_manager import create_nginx_config
    create_nginx_config(site.domain, site.app_port, site.type)

    # B. Restart PM2 (Logic restart akan baca port baru dari DB atau Env)
    # Kita perlu update Environment Variable PORT di folder site juga kalau mau proper
    # Tapi untuk simpelnya, user disuruh restart manual atau kita trigger reload
    if site.type in ['node', 'python']:
        from app.system.pm2_manager import delete_app, start_app
        # Kill yang lama (port lama)
        delete_app(site.domain)
        # Start yang baru (port baru)
        # Kita perlu path scriptnya
        base_dir = os.path.join(os.getcwd(), "www_data", site.domain)
        script = "app.py" if site.type == "python" else "index.js"  # Default logic
        # Kalau user udah punya package.json, logic start_app harusnya bisa nyesuain (nanti kita upgrade)
        start_app(site.domain, site.app_port, os.path.join(base_dir, script))

    return {"message": f"Port changed from {old_port} to {site.app_port}"}