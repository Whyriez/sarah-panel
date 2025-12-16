import os
import zipfile
import subprocess
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.sites.models import Site
from app.modules.databases.models import Database
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(tags=["Backups"])

BACKUP_ROOT = os.path.join(os.getcwd(), "backups")
os.makedirs(BACKUP_ROOT, exist_ok=True)

DB_ROOT_PASS = os.getenv("MYSQL_ROOT_PASSWORD")

# Helper: Zip Folder
def zip_folder(folder_path, zip_handle):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Hindari zip file zip sendiri atau folder .git yang besar
            if file.endswith('.zip') or '.git' in root:
                continue

            file_path = os.path.join(root, file)
            # Simpan dengan path relatif biar pas diextract rapi
            arcname = os.path.relpath(file_path, os.path.join(folder_path, '..'))
            zip_handle.write(file_path, arcname)


@router.post("/backups/create/{site_id}")
async def create_backup(
        site_id: int,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site: raise HTTPException(404, "Site not found")

    # Generate Nama File Unik: domain_timestamp.zip
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{site.domain}_{timestamp}.zip"
    filepath = os.path.join(BACKUP_ROOT, filename)

    # Jalankan di Background biar UI gak lemot
    background_tasks.add_task(perform_backup, site, db, filepath)

    return {"message": "Backup started in background", "filename": filename}


def perform_backup(site, db_session, zip_filepath):
    print(f"📦 Starting backup for {site.domain}...")

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. BACKUP FILES WEBSITE
            # Path: backend/www_data/domain.com
            site_dir = os.path.join(os.getcwd(), "www_data", site.domain)
            if os.path.exists(site_dir):
                zip_folder(site_dir, zipf)
                print("✅ Files zipped")

            # 2. BACKUP DATABASE (Jika ada)
            # Kita cari database yang namanya mirip domain atau milik user ini
            # Untuk simpelnya, kita ambil semua DB milik user ini (karena relasi site-db belum strict di model kita)
            user_dbs = db_session.query(Database).filter(Database.user_id == site.user_id).all()

            for database in user_dbs:
                # Dump SQL
                dump_file = f"{database.name}.sql"

                # Command mysqldump (Sesuaikan path kalau di Windows dan gak masuk PATH)
                # Contoh: "C:/xampp/mysql/bin/mysqldump.exe"
                # Di Linux biasanya langsung "mysqldump"
                cmd = [
                    "mysqldump",
                    "-u", "root",
                    f"-p{DB_ROOT_PASS}",
                    database.name
                ]

                try:
                    # Di Windows kadang mysqldump perlu path lengkap, kita try-except
                    with open(dump_file, "w") as f:
                        subprocess.run(cmd, stdout=f, check=True)

                    # Masukkan SQL ke dalam Zip
                    zipf.write(dump_file, arcname=f"database/{dump_file}")

                    # Hapus file mentahan SQL setelah masuk zip
                    os.remove(dump_file)
                    print(f"✅ Database {database.name} dumped")

                except Exception as e:
                    print(f"⚠️ Skip DB Backup {database.name}: {e}")
                    # Bikin file txt error log di dalam zip
                    zipf.writestr(f"database/{database.name}_ERROR.txt", str(e))

        print(f"🎉 Backup Complete: {zip_filepath}")

    except Exception as e:
        print(f"❌ Backup Failed: {e}")


@router.get("/backups/list")
def list_backups(current_user: User = Depends(get_current_user)):
    # List semua file di folder backups
    # Idealnya difilter by user, tapi untuk MVP kita list semua dlu atau filter by nama domain user
    files = []
    if os.path.exists(BACKUP_ROOT):
        for f in os.listdir(BACKUP_ROOT):
            if f.endswith(".zip"):
                stat = os.stat(os.path.join(BACKUP_ROOT, f))
                files.append({
                    "filename": f,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
    # Sort by terbaru
    files.sort(key=lambda x: x['created_at'], reverse=True)
    return files


@router.get("/backups/download/{filename}")
def download_backup(filename: str, current_user: User = Depends(get_current_user)):
    file_path = os.path.join(BACKUP_ROOT, filename)
    if not os.path.exists(file_path):
        raise HTTPException(404, "File not found")

    return FileResponse(file_path, filename=filename)


@router.delete("/backups/delete/{filename}")
def delete_backup(filename: str, current_user: User = Depends(get_current_user)):
    file_path = os.path.join(BACKUP_ROOT, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Backup deleted"}
    raise HTTPException(404, "File not found")