from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os
from app.system.pm2_manager import start_app, delete_app, reload_app
from app.system.nginx_manager import create_nginx_config, delete_nginx_config
from app.modules.sites.schemas import SiteCreate, SiteResponse
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

class QueueWorkerRequest(BaseModel):
    connection: str = "database"
    queue: str = "default"
    tries: int = 3
    timeout: int = 90

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


@router.post("/{site_id}/queue-worker")
def manage_queue_worker(
        site_id: int,
        payload: QueueWorkerRequest,
        action: str = "start",  # query param: ?action=start/stop
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    site = get_user_site(site_id, current_user.id, db)
    if site.type != 'php': return {"error": "PHP Only"}

    worker_name = f"{site.domain}-worker"
    site_path = os.path.join(SITES_BASE_DIR, site.domain)
    php_bin = f"php{site.php_version}"

    if action == "stop":
        subprocess.run(["pm2", "delete", worker_name], check=False)
        return {"message": "Worker stopped"}

    # Start Logic
    cmd = [
        "pm2", "start", php_bin,
        "--name", worker_name,
        "--cwd", site_path,
        "--", "artisan", "queue:work", payload.connection,
        f"--queue={payload.queue}",
        f"--tries={payload.tries}",
        f"--timeout={payload.timeout}"
    ]

    subprocess.run(cmd, check=True)
    subprocess.run(["pm2", "save"], check=True)
    return {"message": "Worker started"}


def generate_nginx_config_internal(site_obj, root_path):
    """
    Fungsi ini menangani pembuatan file Nginx untuk semua tipe:
    PHP (Native/Laravel/WP) dan Node/Python (Proxy).
    """
    nginx_path = f"/etc/nginx/sites-available/{site_obj.domain}"

    # 1. Tentukan Block Location (Routing Rule)
    location_block = ""

    # Kita cek site.type atau site.framework (jika sudah ditambahkan di schemas)
    # Disini kita pakai logika: jika type="laravel" atau "wordpress", handle routingnya.
    # Jika Anda belum ubah schemas, kita anggap type="php" default native,
    # tapi nanti bisa kita update manual di DB.

    # CASE A: LARAVEL / WORDPRESS
    # (Asumsi: Anda akan kirim type="laravel" atau "wordpress" dari frontend,
    # atau type="php" tapi ada field framework. Disini saya support jika type="laravel")
    if site_obj.type in ["laravel", "wordpress"]:
        location_block = """
    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }"""

    # CASE B: SPA (React/Vue Build)
    elif site_obj.type == "spa":
        location_block = """
    location / {
        try_files $uri $uri/ /index.html;
    }"""

    # CASE C: PROXY (Node / Python)
    elif site_obj.type in ["node", "python"]:
        location_block = f"""
    location / {{
        proxy_pass http://127.0.0.1:{site_obj.app_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}"""

    # CASE D: DEFAULT PHP / HTML STATIC
    else:
        location_block = """
    location / {
        try_files $uri $uri/ =404;
    }"""

    # 2. Config PHP Block (Untuk PHP, Laravel, Wordpress)
    php_block = ""
    if site_obj.type in ["php", "laravel", "wordpress"]:
        # Default pakai PHP 8.1, sesuaikan logic jika ingin dinamis dari site_obj.php_version
        php_ver = site_obj.php_version if site_obj.php_version else "8.1"
        php_block = f"""
    location ~ \.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_ver}-fpm.sock; 
    }}"""

    # 3. Susun Config Lengkap
    nginx_config = f"""
server {{
    listen 80;
    server_name {site_obj.domain} www.{site_obj.domain};

    root {root_path};
    index index.php index.html index.htm; # Prioritas index

    access_log /var/log/nginx/{site_obj.domain}_access.log;
    error_log /var/log/nginx/{site_obj.domain}_error.log;

    {location_block}

    {php_block}

    location ~ /\.ht {{
        deny all;
    }}
}}
"""
    # 4. Tulis File Nginx
    with open(nginx_path, "w") as f:
        f.write(nginx_config)

    # 5. Enable & Reload
    if not os.path.exists(f"/etc/nginx/sites-enabled/{site_obj.domain}"):
        os.symlink(nginx_path, f"/etc/nginx/sites-enabled/{site_obj.domain}")

    os.system("systemctl reload nginx")

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
    # 1. CEK DUPLIKASI DOMAIN
    existing_site = db.query(models.Site).filter(models.Site.domain == site.domain).first()
    if existing_site:
        raise HTTPException(status_code=400, detail="Domain already exists")

    # 2. ASSIGN PORT (Hanya untuk Node/Python)
    assigned_port = None
    if site.type in ["node", "python"]:
        assigned_port = get_available_port(db)

    # 3. SIMPAN KE DATABASE
    # Perhatikan: Saya pakai 'new_site' sesuai variabel anda
    new_site = models.Site(
        domain=site.domain,
        type=site.type,
        # Jika type="laravel", kita anggap php_version perlu disimpan juga
        php_version=site.php_version if site.type in ["php", "laravel", "wordpress"] else None,
        user_id=current_user.id,
        app_port=assigned_port,
        startup_command=site.startup_command if hasattr(site, 'startup_command') else None
    )

    db.add(new_site)
    db.commit()
    db.refresh(new_site)

    # 4. BUAT FOLDER & FILE DUMMY
    base_dir = os.path.join(SITES_BASE_DIR, new_site.domain)
    os.makedirs(base_dir, exist_ok=True)

    # File dummy (app.py / index.js / index.php)
    if new_site.type == "python":
        script_path = os.path.join(base_dir, "app.py")
        if not os.path.exists(script_path):
            with open(script_path, "w") as f:
                f.write("# Dummy Python App\nprint('Hello AlimPanel')")

    elif new_site.type == "node":
        script_path = os.path.join(base_dir, "index.js")
        if not os.path.exists(script_path):
            with open(script_path, "w") as f:
                f.write(
                    "// Dummy Node App\nconst http = require('http');\nconst server = http.createServer((req, res) => { res.writeHead(200); res.end('Hello AlimPanel!'); });\nserver.listen(process.env.PORT || 3000);")

    elif new_site.type in ["php", "laravel", "wordpress"]:
        # Khusus PHP Native kita buat index.php dummy.
        # Kalau Laravel/WP biasanya user upload file sendiri nanti, tapi dummy oke juga.
        index_php = os.path.join(base_dir, "index.php")
        if not os.path.exists(index_php):
            with open(index_php, "w") as f:
                f.write(f"<?php echo '<h1>Hello from {new_site.type} on AlimPanel</h1>'; phpinfo(); ?>")

    # 5. START APP (PM2) - Khusus Node/Python
    if new_site.type in ["node", "python"] and new_site.app_port:
        script_filename = "app.py" if new_site.type == "python" else "index.js"
        script_path_full = os.path.join(base_dir, script_filename)

        success, msg = start_app(
            domain=new_site.domain,
            port=new_site.app_port,
            script_path=script_path_full
        )
        if not success:
            print(f"⚠️ Failed to start app: {msg}")

    # 6. GENERATE NGINX CONFIG (INTEGRASI BARU DISINI)
    # Ini akan menghandle semua tipe: Node, Python, PHP, Laravel, WP
    try:
        generate_nginx_config_internal(new_site, base_dir)
    except Exception as e:
        print(f"⚠️ Failed to generate Nginx: {e}")
        # Opsional: raise HTTPException jika ingin user tau errornya

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


@router.put("/{site_id}/startup-command")
def update_startup_command(
        site_id: int,
        payload: dict,  # { "command": "npm run dev" }
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    site = get_user_site(site_id, current_user.id, db)
    site.startup_command = payload['command']
    db.commit()

    # Restart app dengan command baru
    base_dir = os.path.join(SITES_BASE_DIR, site.domain)
    start_app(site.domain, site.app_port, base_dir, site.startup_command)

    return {"message": "Startup command updated & App restarted"}

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


class UpdatePhpRequest(BaseModel):
    version: str # "7.4", "8.0", "8.2"

@router.put("/{site_id}/php")
def update_php_version(
    site_id: int,
    payload: UpdatePhpRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Secure Get
    site = get_user_site(site_id, current_user.id, db)

    if site.type != "php":
        raise HTTPException(400, "This site is not a PHP application")

    # Update DB
    site.php_version = payload.version
    db.commit()

    # Regenerate Nginx dengan versi baru
    create_nginx_config(site.domain, 0, "php", site.php_version)

    # Opsional: Restart PHP-FPM service (via sudo) biar fresh
    # subprocess.run(["sudo", "systemctl", "restart", f"php{site.php_version}-fpm"], check=False)

    return {"message": f"Switched to PHP {site.php_version}"}


@router.post("/{site_id}/enable-dedicated-pool")
def enable_dedicated_pool(
        site_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Fitur 'Laravel/Pro Mode':
    Otomatis membuat Dedicated PHP-FPM Pool untuk website ini.
    Efek: 'disable_functions' dikosongkan (Exec, Symlink, dll bisa jalan).
    """
    # 1. Ambil Data Site & Validasi Kepemilikan
    site = get_user_site(site_id, current_user.id, db)

    if site.type != 'php':
        raise HTTPException(400, "Only for PHP sites")

    # 2. Siapkan Variabel
    php_ver = site.php_version or "8.2"
    # Nama pool aman (ganti titik jadi underscore)
    pool_name = site.domain.replace('.', '_')

    # Path Config Pool (contoh: /etc/php/8.2/fpm/pool.d/domain.com.conf)
    conf_file = f"/etc/php/{php_ver}/fpm/pool.d/{site.domain}.conf"

    # Path Socket Baru (contoh: /run/php/php8.2-fpm-domain.com.sock)
    socket_file = f"/run/php/php{php_ver}-fpm-{site.domain}.sock"

    # 3. Template Konfigurasi Pool (Open Security)
    # Perhatikan: disable_functions = "" (KOSONG) artinya semua fungsi boleh dipakai
    pool_config = f"""
[{pool_name}]
user = alimpanel
group = alimpanel

listen = {socket_file}
listen.owner = www-data
listen.group = www-data
listen.mode = 0660

pm = dynamic
pm.max_children = 10
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

; SECURITY OVERRIDE
; Unblock semua fungsi berbahaya untuk user ini
php_admin_value[disable_functions] = ""
php_admin_flag[allow_url_fopen] = on
; Limit memory custom (opsional)
php_admin_value[memory_limit] = 256M
"""

    try:
        print(f"⚙️ Creating Dedicated Pool for {site.domain}...")

        # 4. Tulis File Conf (Memerlukan izin sudo tee ke folder /etc/php/...)
        subprocess.run(
            ["sudo", "tee", conf_file],
            input=pool_config, text=True, check=True
        )

        # 5. Restart PHP-FPM (Agar pool baru aktif)
        subprocess.run(["sudo", "systemctl", "restart", f"php{php_ver}-fpm"], check=True)

        # 6. Update Nginx agar mengarah ke Socket Baru
        create_nginx_config(
            domain=site.domain,
            port=0,
            type="php",
            php_version=php_ver,
            custom_socket=socket_file  # Gunakan socket baru
        )

        return {
            "message": f"Dedicated Pool activated for {site.domain}!",
            "details": "Exec & Symlink enabled. Socket updated."
        }

    except subprocess.CalledProcessError as e:
        print(f"❌ Subprocess Error: {e}")
        raise HTTPException(500, detail="Failed to configure system files. Check server logs.")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(500, detail=str(e))