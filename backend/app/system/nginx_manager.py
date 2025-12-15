import os
import platform
import subprocess

# Template HTTP (Standar)
NGINX_HTTP_TEMPLATE = """
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
    }}
}}
"""

# [FIX] Template HTTPS (Jika SSL terdeteksi)
NGINX_HTTPS_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""


def reload_nginx():
    """Reload Nginx agar konfigurasi baru aktif"""
    try:
        if platform.system() == "Windows":
            print("🖥️ [WINDOWS] Simulasi: nginx -s reload")
        else:
            subprocess.run(["sudo", "nginx", "-t"], check=True)
            subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)
            print("✅ Nginx Reloaded")
    except Exception as e:
        print(f"❌ Nginx Reload Failed: {e}")


def create_nginx_config(domain: str, port: int, type: str):
    if platform.system() == "Windows":
        return

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    # [FIX] Cek apakah User sudah punya SSL dari Certbot?
    ssl_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    has_ssl = os.path.exists(ssl_path)

    try:
        # Pilih Template yang sesuai
        if has_ssl:
            print(f"🔒 SSL Detected for {domain}, generating HTTPS config...")
            config_content = NGINX_HTTPS_TEMPLATE.format(domain=domain, port=port)
        else:
            config_content = NGINX_HTTP_TEMPLATE.format(domain=domain, port=port)

        # Tulis File
        # Tulis file pakai sudo tee
        subprocess.run(
            ["sudo", "tee", config_path],
            input=config_content, text=True, check=True
        )

        # Buat symlink pakai sudo ln
        if not os.path.exists(symlink_path):
            subprocess.run(
                ["sudo", "ln", "-s", config_path, symlink_path],
                check=True
            )

        reload_nginx()
        print(f"✅ Nginx Config updated for {domain}")

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
        subprocess.run(["sudo", "rm", "-f", symlink_path], check=False)
        subprocess.run(["sudo", "rm", "-f", config_path], check=False)

        print(f"🗑️ Nginx Config deleted for {domain}")
        reload_nginx()

    except Exception as e:
        print(f"❌ Failed deleting Nginx config: {e}")