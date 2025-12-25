import os
import shutil
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from pydantic import BaseModel
from app.modules.auth.deps import get_current_user
from app.modules.users.models import User
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.modules.sites.models import Site
from app.modules.sites.router import get_user_site

router = APIRouter(prefix="/files", tags=["File Manager"])

SITES_BASE_DIR = "/var/www/sarahpanel"


# Helper: Validasi Path (Anti-Hacking & Permission)
def get_safe_path(site_id: int, relative_path: str, user: User, db: Session):
    # 1. Cari Site
    site = get_user_site(site_id, user.id, db)

    # 2. Tentukan Root Folder Site
    base_dir = os.path.abspath(os.path.join(SITES_BASE_DIR, site.domain))

    # Buat folder jika belum ada
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    # 3. Gabungkan path
    clean_rel = relative_path.lstrip("/").replace("..", "")
    target_path = os.path.abspath(os.path.join(base_dir, clean_rel))

    # 4. Security Check (Jail)
    if not target_path.startswith(base_dir):
        raise HTTPException(400, "Invalid path access (Jailbreak attempt)")

    return target_path, base_dir


# 1. LIST FILES
@router.get("/list/{site_id}")
def list_files(site_id: int, path: str = "", db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    target_path, _ = get_safe_path(site_id, path, current_user, db)

    if not os.path.exists(target_path):
        return []

    items = []
    with os.scandir(target_path) as entries:
        for entry in entries:
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "type": "folder" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else 0,
                    "mtime": stat.st_mtime
                })
            except FileNotFoundError:
                continue  # Skip jika file terhapus saat scan

    # Sort: Folder dulu, baru file
    items.sort(key=lambda x: (x['type'] != 'folder', x['name']))
    return items


# 2. READ FILE CONTENT
@router.get("/content/{site_id}")
def read_file(site_id: int, path: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_path, _ = get_safe_path(site_id, path, current_user, db)

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
    target_path, _ = get_safe_path(site_id, payload.path, current_user, db)

    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
    except Exception as e:
        raise HTTPException(500, f"Failed to save: {str(e)}")

    return {"message": "Saved"}


# 4. CREATE NEW FILE / FOLDER
class CreateItemRequest(BaseModel):
    path: str
    name: str
    type: str


@router.post("/create/{site_id}")
def create_item(
        site_id: int,
        payload: CreateItemRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    parent_path, _ = get_safe_path(site_id, payload.path, current_user, db)
    new_item_path = os.path.join(parent_path, payload.name)

    if os.path.exists(new_item_path):
        raise HTTPException(400, "File or Folder already exists")

    try:
        if payload.type == "folder":
            os.makedirs(new_item_path, mode=0o755)  # Folder Permission 755
        else:
            with open(new_item_path, 'w') as f:
                pass
            os.chmod(new_item_path, 0o644)  # File Permission 644

        # [FIX] HAPUS shutil.chown KE www-data.
        # File otomatis milik 'alimpanel' (user service), Nginx bisa baca (karena 644/755).

    except Exception as e:
        raise HTTPException(500, f"Error creating item: {str(e)}")

    return {"message": f"{payload.type} created successfully"}


# 5. RENAME ITEM
class RenameItemRequest(BaseModel):
    path: str
    old_name: str
    new_name: str


@router.put("/rename/{site_id}")
def rename_item(
        site_id: int,
        payload: RenameItemRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    parent_path, _ = get_safe_path(site_id, payload.path, current_user, db)
    old_path = os.path.join(parent_path, payload.old_name)
    new_path = os.path.join(parent_path, payload.new_name)

    if not os.path.exists(old_path):
        raise HTTPException(404, "Item not found")

    if os.path.exists(new_path):
        raise HTTPException(400, "New name already taken")

    try:
        os.rename(old_path, new_path)
    except Exception as e:
        raise HTTPException(500, f"Error renaming: {str(e)}")

    return {"message": "Renamed successfully"}


# 6. UPLOAD FILE
@router.post("/upload/{site_id}")
async def upload_file(
        site_id: int,
        path: str = Query(""),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    target_dir, _ = get_safe_path(site_id, path, current_user, db)
    file_path = os.path.join(target_dir, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Set permission agar bisa dibaca web server
        os.chmod(file_path, 0o644)

    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")

    return {"message": f"Uploaded {file.filename}"}


# 7. DELETE FILE/FOLDER
@router.delete("/delete/{site_id}")
def delete_item(site_id: int, path: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    target_path, _ = get_safe_path(site_id, path, current_user, db)

    try:
        if os.path.isfile(target_path):
            os.remove(target_path)
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")

    return {"message": "Deleted"}


# 8. EXTRACT ZIP
class ExtractRequest(BaseModel):
    archive_path: str
    destination_path: str


@router.post("/extract/{site_id}")
def extract_file(
        site_id: int,
        payload: ExtractRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    zip_full_path, _ = get_safe_path(site_id, payload.archive_path, current_user, db)
    dest_full_path, _ = get_safe_path(site_id, payload.destination_path, current_user, db)

    if not os.path.exists(zip_full_path) or not zipfile.is_zipfile(zip_full_path):
        raise HTTPException(status_code=400, detail="File is not a valid zip archive")

    # Fungsi Background
    def safe_extract_task(zip_path, dest_dir):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.infolist():
                    # Block Zip Slip (Security)
                    member_path = os.path.join(dest_dir, member.filename)
                    if not os.path.commonpath([dest_dir, member_path]).startswith(dest_dir):
                        continue  # Skip file jahat

                    zf.extract(member, dest_dir)

            # [FIX] Hapus subprocess chown recursive.
            # File hasil extract otomatis milik 'alimpanel'.

        except Exception as e:
            print(f"❌ Extract Error: {e}")

    background_tasks.add_task(safe_extract_task, zip_full_path, dest_full_path)

    return {"message": "Extraction started in background"}