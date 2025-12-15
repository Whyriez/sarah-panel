import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.modules.sites.models import Site

router = APIRouter(prefix="/files", tags=["File Manager"])

SITES_BASE_DIR = "/var/www/sarahpanel"

# Helper: Validasi Path (Anti-Hacking)
def get_safe_path(site_id: int, relative_path: str, user: User, db: Session):
    # 1. Cari Site
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site: raise HTTPException(404, "Site not found")

    # ... (cek permission existing) ...

    # 3. Tentukan Root Folder Site (Gunakan Variable Constant tadi)
    base_dir = os.path.abspath(os.path.join(SITES_BASE_DIR, site.domain))

    # Buat folder jika belum ada (safety net)
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    # 4. Gabungkan path
    target_path = os.path.abspath(os.path.join(base_dir, relative_path.lstrip("/")))

    # 5. Security Check
    if not target_path.startswith(base_dir):
        raise HTTPException(400, "Invalid path access")

    return target_path


# 1. LIST FILES
@router.get("/list/{site_id}")
def list_files(site_id: int, path: str = "", db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    target_path = get_safe_path(site_id, path, current_user, db)

    if not os.path.exists(target_path):
        return []

    items = []
    with os.scandir(target_path) as entries:
        for entry in entries:
            items.append({
                "name": entry.name,
                "type": "folder" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else 0,
                # "mtime": entry.stat().st_mtime
            })

    # Sort: Folder dulu, baru file
    items.sort(key=lambda x: (x['type'] != 'folder', x['name']))
    return items


# 2. READ FILE CONTENT (Buat Editor)
@router.get("/content/{site_id}")
def read_file(site_id: int, path: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_path = get_safe_path(site_id, path, current_user, db)

    if not os.path.isfile(target_path):
        raise HTTPException(400, "Not a file")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    except UnicodeDecodeError:
        return {"content": "[Binary File or Image - Cannot Edit]"}


# 3. SAVE FILE CONTENT
class FileSave(BaseModel):
    path: str
    content: str


@router.post("/save/{site_id}")
def save_file(site_id: int, payload: FileSave, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    target_path = get_safe_path(site_id, payload.path, current_user, db)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(payload.content)

    return {"message": "Saved"}


# 4. UPLOAD FILE
@router.post("/upload/{site_id}")
async def upload_file(
    site_id: int,
    path: str = Query(""), # Baca path dari URL
    file: UploadFile = File(...), # Baca file dari Body (Wajib ada python-multipart)
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # ... logic di bawahnya TETAP SAMA, tidak perlu diubah ...
    target_dir = get_safe_path(site_id, path, current_user, db)
    file_path = os.path.join(target_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": f"Uploaded {file.filename}"}


# 5. DELETE FILE/FOLDER
@router.delete("/delete/{site_id}")
def delete_item(site_id: int, path: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_path = get_safe_path(site_id, path, current_user, db)

    if os.path.isfile(target_path):
        os.remove(target_path)
    elif os.path.isdir(target_path):
        shutil.rmtree(target_path)

    return {"message": "Deleted"}