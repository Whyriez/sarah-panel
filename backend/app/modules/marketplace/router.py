import os
import requests
import zipfile
import io
import shutil
from pydantic import BaseModel
import subprocess
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.sites.models import Site
from app.modules.databases.router import create_db, schemas as db_schemas  # Reuse logic DB kita yg canggih kemarin
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User


router = APIRouter(tags=["Marketplace"])


class PhpInstallRequest(BaseModel):
    version: str  # Contoh: "8.3", "7.4"

COMMON_EXTENSIONS = [
    "intl", "curl", "gd", "mbstring", "xml", "zip", "mysql",
    "bcmath", "sqlite3", "pgsql", "soap", "gmp", "imagick",
    "redis", "memcached", "bz2", "ldap", "imap"
]

class ExtensionPayload(BaseModel):
    version: str   # "8.1", "8.2"
    extension: str # "intl", "redis"
    action: str    # "install" atau "uninstall"


@router.get("/marketplace/php/{version}/extensions")
def get_php_extensions(version: str, current_user: User = Depends(get_current_user)):
    """
    List status ekstensi untuk versi PHP tertentu.
    """
    # Validasi versi simple
    if version not in ["7.4", "8.0", "8.1", "8.2", "8.3", "8.4"]:
        return {"error": "Unsupported version"}

    results = []

    for ext in COMMON_EXTENSIONS:
        # Nama paket di Ubuntu (ppa:ondrej) biasanya format: php8.2-intl
        pkg_name = f"php{version}-{ext}"

        # Cek apakah terinstall via dpkg
        # Kita pakai shell=True hati-hati, tapi ini internal tool
        cmd = f"dpkg -s {pkg_name} | grep 'Status: install ok installed'"
        is_installed = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).returncode == 0

        results.append({
            "name": ext,
            "installed": is_installed,
            "package": pkg_name
        })

    return results


@router.post("/marketplace/php/extensions")
def manage_php_extension(
        payload: ExtensionPayload,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user)
):
    """
    Install atau Remove ekstensi PHP
    """
    # Validasi input agar tidak kena command injection
    if payload.version not in ["7.4", "8.0", "8.1", "8.2", "8.3", "8.4"]:
        raise HTTPException(400, "Invalid PHP Version")

    if payload.extension not in COMMON_EXTENSIONS:
        raise HTTPException(400, "Extension not supported in this list")

    background_tasks.add_task(
        run_extension_manager,
        payload.version,
        payload.extension,
        payload.action
    )

    msg = "Installing" if payload.action == "install" else "Uninstalling"
    return {"message": f"{msg} {payload.extension} for PHP {payload.version}..."}


def run_extension_manager(version, extension, action):
    pkg_name = f"php{version}-{extension}"

    try:
        print(f"⚙️ {action.upper()} {pkg_name}...")

        if action == "install":
            # Update apt dulu biar nggak error 404
            subprocess.run(["sudo", "apt-get", "update"], check=False)
            subprocess.run(["sudo", "apt-get", "install", "-y", pkg_name], check=True)
        elif action == "uninstall":
            subprocess.run(["sudo", "apt-get", "remove", "-y", pkg_name], check=True)
            # Opsional: autoremove untuk bersih-bersih
            subprocess.run(["sudo", "apt-get", "autoremove", "-y"], check=False)

        # PENTING: Restart PHP-FPM agar efeknya terasa
        subprocess.run(["sudo", "systemctl", "restart", f"php{version}-fpm"], check=True)

        print(f"✅ Success {action} {pkg_name}")

    except Exception as e:
        print(f"❌ Failed to {action} {pkg_name}: {e}")

@router.post("/marketplace/php/install")
def install_php_version(
        payload: PhpInstallRequest,
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user)
):
    """
    Install versi PHP baru secara global ke server (OS Level).
    """
    # Validasi format versi (Security: mencegah command injection)
    allowed_chars = set("0123456789.")
    if not set(payload.version).issubset(allowed_chars):
        raise HTTPException(status_code=400, detail="Invalid version format")

    version = payload.version

    # Jalankan instalasi di background
    background_tasks.add_task(run_php_system_installer, version)

    return {"message": f"Installing PHP {version} in background..."}


def run_php_system_installer(version: str):
    """
    Fungsi worker untuk menjalankan apt install
    """
    print(f"📦 Starting installation of PHP {version}...")
    try:
        # Paket-paket standar yang diperlukan (sesuai install.sh Anda)
        packages = [
            f"php{version}-fpm",
            f"php{version}-mysql",
            f"php{version}-common",
            f"php{version}-curl",
            f"php{version}-xml",
            f"php{version}-zip",
            f"php{version}-gd",
            f"php{version}-mbstring",
            f"php{version}-bcmath"
        ]

        # Construct command string
        pkg_str = " ".join(packages)

        # Command: sudo apt-get install -y php8.x-fpm ...
        cmd = ["sudo", "apt-get", "install", "-y"] + packages

        # Jalankan proses
        # Note: Pastikan user 'alimpanel' punya izin sudo untuk command ini (Lihat Step 2)
        process = subprocess.run(cmd, capture_output=True, text=True)

        if process.returncode == 0:
            print(f"✅ PHP {version} installed successfully!")
            # Auto start service
            subprocess.run(["sudo", "systemctl", "enable", f"php{version}-fpm"])
            subprocess.run(["sudo", "systemctl", "start", f"php{version}-fpm"])
        else:
            print(f"❌ PHP Install Failed: {process.stderr}")

    except Exception as e:
        print(f"❌ System Error: {e}")

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