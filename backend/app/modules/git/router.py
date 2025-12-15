import subprocess
import time

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.files.router import SITES_BASE_DIR
from app.modules.sites.models import Site
from app.system.git_manager import git_clone, git_pull
from app.system.pm2_manager import reload_app
import os
import stat
import shutil

router = APIRouter(tags=["Git Deployment"])


def handle_remove_readonly(func, path, exc):
    """
    Fungsi ini dipanggil kalau shutil.rmtree gagal hapus file.
    Kita paksa ubah permission jadi Writable, lalu coba hapus lagi.
    """
    excvalue = exc[1]
    # Ubah jadi boleh tulis/hapus
    os.chmod(path, stat.S_IWRITE)
    # Coba hapus lagi
    try:
        func(path)
    except Exception:
        pass # Kalau masih gagal, ya pasrah (biasanya butuh restart PC/Kill process)


@router.post("/git/setup/{site_id}")
def setup_git(
        site_id: int,
        payload: dict,
        db: Session = Depends(get_db)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site.repo_url = payload.get('repo_url')
    site.branch = payload.get('branch', 'main')
    site.auto_deploy = True
    db.commit()

    target_dir = os.path.join(os.getcwd(), "www_data", site.domain)

    # [FIX LEBIH GALAK] BERSIHKAN FOLDER
    if os.path.exists(target_dir):
        # 1. Coba cara halus dulu
        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.chmod(file_path, stat.S_IWRITE)  # Pastikan tidak Read-Only
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    # Pakai handler khusus Windows
                    shutil.rmtree(file_path, onerror=handle_remove_readonly)
            except Exception as e:
                print(f"⚠️ Gagal hapus {file_path}: {e}")

        # 2. Cek lagi, kalau masih ada file bandel, kita tunggu sebentar
        # Kadang Windows butuh waktu sedetik buat lepas lock
        if os.listdir(target_dir):
            time.sleep(1)
            # Coba hapus lagi sisa-sisanya
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path, onerror=handle_remove_readonly)
                    else:
                        os.unlink(file_path)
                except:
                    pass

    # Clone
    success, msg = git_clone(site.repo_url, target_dir)

    if not success:
        site.auto_deploy = False
        db.commit()
        # Pesan error lebih jelas
        raise HTTPException(status_code=400,
                            detail=f"Git Clone Failed ({msg}). Coba hapus folder '{site.domain}' secara manual di Windows Explorer.")

    return {"message": "Git Connected & Cloned!", "webhook_url": f"http://localhost:8000/git/webhook/{site.id}"}


# 2. WEBHOOK RECEIVER (Dipanggil oleh GitHub)
@router.post("/git/webhook/{site_id}")
async def git_webhook(
        site_id: int,
        request: Request,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    # Verifikasi Site
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site or not site.auto_deploy:
        return {"message": "Ignored (Auto deploy disabled)"}

    # Jalankan Pull & Restart di Background
    background_tasks.add_task(perform_deploy, site)

    return {"message": "Deploy triggered!"}


def perform_deploy(site):
    target_dir = os.path.join(os.getcwd(), "www_data", site.domain)
    print(f"🚀 Deploying {site.domain} from Git...")

    # 1. Git Pull
    success, msg = git_pull(target_dir, site.branch)
    if success:
        print("✅ Git Pull Success")

        # 2. Install Dependency (Opsional, kalau ada package.json)
        if os.path.exists(os.path.join(target_dir, "package.json")):
            print("📦 Installing NPM packages...")
            # Di Windows pakai shell=True
            import subprocess
            subprocess.run(["npm", "install"], cwd=target_dir, shell=True)

        # 3. Restart PM2
        if site.type in ['node', 'python']:
            reload_app(site.domain)
            print("🔄 PM2 Reloaded")
    else:
        print(f"❌ Deploy Failed: {msg}")


@router.post("/webhook/deploy/{token}")
def webhook_deploy(token: str, db: Session = Depends(get_db)):
    # 1. Cari site berdasarkan token
    site = db.query(Site).filter(Site.webhook_token == token).first()
    if not site:
        raise HTTPException(404, "Invalid Webhook Token")

    # 2. Jalankan Git Pull
    base_dir = os.path.join(SITES_BASE_DIR, site.domain)

    try:
        # Git Pull
        subprocess.run(["git", "pull"], cwd=base_dir, check=True)

        # 3. Post-Deploy Action (Install Dep & Restart)
        if site.type == "node":
            subprocess.run(["npm", "install"], cwd=base_dir, check=False)
            subprocess.run(["pm2", "restart", site.domain], check=False)

        elif site.type == "python":
            venv_python = os.path.join(base_dir, "venv/bin/python")
            if os.path.exists(venv_python):
                subprocess.run([venv_python, "-m", "pip", "install", "-r", "requirements.txt"], cwd=base_dir)
            subprocess.run(["pm2", "restart", site.domain], check=False)

        elif site.type == "php":
            # Laravel optimization
            subprocess.run(["composer", "install", "--no-dev"], cwd=base_dir, check=False)
            subprocess.run(["php", "artisan", "migrate", "--force"], cwd=base_dir, check=False)
            # Reload PHP-FPM (butuh sudo, pastikan izin ada)
            # subprocess.run(["sudo", "systemctl", "reload", f"php{site.php_version}-fpm"])

        return {"status": "Deployed", "site": site.domain}

    except Exception as e:
        return {"status": "Failed", "error": str(e)}