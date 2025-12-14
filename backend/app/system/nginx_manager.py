import os
import platform
import subprocess

# Template Config untuk Reverse Proxy (Node.js / Python)
NGINX_PROXY_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}

    # Log files
    access_log /var/log/nginx/{domain}_access.log;
    error_log /var/log/nginx/{domain}_error.log;
}}
"""


def reload_nginx():
    """Reload Nginx agar konfigurasi baru aktif"""
    try:
        if platform.system() == "Windows":
            print("🖥️ [WINDOWS] Simulasi: nginx -s reload")
        else:
            # Cek syntax dulu biar gak crash satu server
            subprocess.run(["nginx", "-t"], check=True)
            # Reload
            subprocess.run(["systemctl", "reload", "nginx"], check=True)
            print("✅ Nginx Reloaded")
    except Exception as e:
        print(f"❌ Nginx Reload Failed: {e}")


def create_nginx_config(domain: str, port: int, type: str):
    """
    Membuat file konfigurasi Nginx.
    """
    if platform.system() == "Windows":
        print(f"🖥️ [WINDOWS] Simulasi Config Nginx untuk {domain} port {port}")
        return

    # --- LINUX LOGIC ---
    config_content = NGINX_PROXY_TEMPLATE.format(domain=domain, port=port)

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    try:
        # 1. Tulis File Config
        with open(config_path, "w") as f:
            f.write(config_content)

        # 2. Buat Symlink (Shortcut) kalau belum ada
        if not os.path.exists(symlink_path):
            os.symlink(config_path, symlink_path)

        print(f"✅ Nginx Config created for {domain}")

        # 3. Reload Nginx
        reload_nginx()

    except PermissionError:
        print("❌ Permission Denied! Pastikan menjalankan Backend dengan 'sudo' di Linux.")
    except Exception as e:
        print(f"❌ Failed creating Nginx config: {e}")


def delete_nginx_config(domain: str):
    """
    Menghapus konfigurasi Nginx saat website didelete.
    """
    if platform.system() == "Windows":
        print(f"🖥️ [WINDOWS] Simulasi Delete Nginx {domain}")
        return

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    try:
        # Hapus Symlink
        if os.path.exists(symlink_path):
            os.remove(symlink_path)

        # Hapus File Asli
        if os.path.exists(config_path):
            os.remove(config_path)

        print(f"🗑️ Nginx Config deleted for {domain}")
        reload_nginx()

    except Exception as e:
        print(f"❌ Failed deleting Nginx config: {e}")