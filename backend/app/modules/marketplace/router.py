import os
import requests
import zipfile
import io
import shutil
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.sites.models import Site
from app.modules.databases.router import create_db, schemas as db_schemas  # Reuse logic DB kita yg canggih kemarin
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User

router = APIRouter(tags=["Marketplace"])


# Helper: Download & Extract
def download_and_extract(url: str, target_dir: str):
    print(f"⬇️ Downloading from {url}...")
    r = requests.get(url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(target_dir)
    print("✅ Extraction complete.")


# Logic Khusus WordPress
def setup_wordpress(site: Site, db_info, target_dir: str):
    # 1. WordPress biasanya diekstrak ke dalam folder 'wordpress', kita harus pindahin isinya ke root
    wp_subdir = os.path.join(target_dir, "wordpress")
    if os.path.exists(wp_subdir):
        for item in os.listdir(wp_subdir):
            shutil.move(os.path.join(wp_subdir, item), target_dir)
        os.rmdir(wp_subdir)  # Hapus folder kosong

    # 2. Rename wp-config-sample.php -> wp-config.php
    sample_config = os.path.join(target_dir, "wp-config-sample.php")
    real_config = os.path.join(target_dir, "wp-config.php")

    if os.path.exists(sample_config):
        with open(sample_config, 'r') as f:
            content = f.read()

        # 3. Inject Database Info (Magic Part!)
        content = content.replace("database_name_here", db_info.name)
        content = content.replace("username_here", db_info.db_user)
        content = content.replace("password_here", db_info.db_password)

        with open(real_config, 'w') as f:
            f.write(content)

    print(f"✅ WordPress Configured for DB: {db_info.name}")


@router.post("/marketplace/install/wordpress")
async def install_wordpress(
        site_id: int,
        background_tasks: BackgroundTasks,  # Biar user gak nunggu loading lama
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Cek Site
    site = db.query(Site).filter(Site.id == site_id, Site.user_id == current_user.id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    # 2. Setup Path (Windows/Linux Compatible)
    # Lokasi: backend/www_data/domain.com/
    target_dir = os.path.join(os.getcwd(), "www_data", site.domain)

    # 3. Buat Database Otomatis (Reuse logic dari modul Database)
    # Nama DB: wp_domain_acak
    import random
    db_suffix = str(random.randint(1000, 9999))
    db_payload = db_schemas.DatabaseCreate(name=f"wp_{db_suffix}")

    # Panggil fungsi create_db kita yang kemarin (pastikan importnya benar)
    # Note: Kita panggil logic-nya manual di sini biar rapi
    try:
        new_db = create_db(db_payload, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed creating DB: {e}")

    # 4. Jalankan Download di Background (Biar UI gak nge-freeze)
    background_tasks.add_task(run_installer, site, new_db, target_dir)

    return {"message": "Installation started! Check logs or files in a moment.", "db_name": new_db.name}


def run_installer(site, db_info, target_dir):
    try:
        # URL Download WordPress Resmi
        WP_URL = "https://wordpress.org/latest.zip"

        # Bersihkan folder dlu (hati-hati di production!)
        # for item in os.listdir(target_dir):
        #    shutil.rmtree(os.path.join(target_dir, item))

        # Download & Extract
        download_and_extract(WP_URL, target_dir)

        # Setup Config
        setup_wordpress(site, db_info, target_dir)

        print("🎉 WordPress Installed Successfully!")
    except Exception as e:
        print(f"❌ Install Error: {e}")


@router.get("/php-versions")
def get_installed_php_versions():
    """
    Cek folder /etc/php/ untuk melihat versi apa saja yang ada
    """
    try:
        if os.path.exists("/etc/php"):
            versions = os.listdir("/etc/php")
            # Filter hanya angka (7.4, 8.2, dll)
            versions = [v for v in versions if v[0].isdigit()]
            versions.sort()
            return {"versions": versions}
        return {"versions": []}
    except:
        return {"versions": ["7.4", "8.0", "8.2"]} # Fallback simulasi