import os
import platform
import subprocess

# [BARU] Template Khusus PHP-FPM
# Perhatikan bagian: fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;
NGINX_PHP_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};
    root /var/www/sarahpanel/{domain};
    index index.php index.html index.htm;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
"""

# Template PHP + SSL
NGINX_PHP_HTTPS_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};
    root /var/www/sarahpanel/{domain};
    index index.php index.html index.htm;

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;
    }}
}}
"""

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


def create_nginx_config(domain: str, port: int, type: str, php_version: str = "8.2"):
    if platform.system() == "Windows":
        return

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    # Cek SSL
    ssl_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    # Logic cek file exist dengan sudo (seperti fix sebelumnya)
    has_ssl = subprocess.run(["sudo", "test", "-f", ssl_path], capture_output=True).returncode == 0

    try:
        config_content = ""

        # LOGIC PEMILIHAN TEMPLATE
        if type == "php":
            # Pakai template PHP
            if has_ssl:
                config_content = NGINX_PHP_HTTPS_TEMPLATE.format(domain=domain, php_version=php_version)
            else:
                config_content = NGINX_PHP_TEMPLATE.format(domain=domain, php_version=php_version)
        else:
            # Pakai template Node/Python (Proxy Pass)
            if has_ssl:
                # Gunakan template HTTPS Node/Python yg lama
                # (Pastikan template HTTPS lama diimport/ada di file ini)
                from app.system.nginx_manager import NGINX_HTTPS_TEMPLATE
                config_content = NGINX_HTTPS_TEMPLATE.format(domain=domain, port=port)
            else:
                from app.system.nginx_manager import NGINX_HTTP_TEMPLATE
                config_content = NGINX_HTTP_TEMPLATE.format(domain=domain, port=port)

        # Tulis File (Pakai sudo tee)
        subprocess.run(
            ["sudo", "tee", config_path],
            input=config_content, text=True, check=True
        )

        # Symlink
        if not subprocess.run(["sudo", "test", "-L", symlink_path], capture_output=True).returncode == 0:
            subprocess.run(["sudo", "ln", "-s", config_path, symlink_path], check=True)

        reload_nginx()
        print(f"✅ Nginx Config updated for {domain} (Type: {type})")

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