import os
import platform
import subprocess

# --- TEMPLATE UTAMA DENGAN SECURITY & OPTIMASI ---

# [FIX] PHP Template: Tambah Upload Limit & Security Isolation (open_basedir)
NGINX_PHP_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};
    root /var/www/sarahpanel/{domain};
    index index.php index.html index.htm;

    # [FIX] Izinkan upload file besar (Theme WP, SQL Import, dll)
    client_max_body_size 128M;

    # [OPTIMASI] Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;

        # [SECURITY CRITICAL] Isolasi Website
        # Mencegah script PHP membaca file di luar folder website ini
        # Kita izinkan akses ke folder web itu sendiri, folder tmp, dan session PHP
        fastcgi_param PHP_ADMIN_VALUE "open_basedir=$document_root:/tmp:/var/lib/php/sessions";
    }}

    # [SECURITY] Blokir akses ke file sensitif
    location ~ /\\.(?!well-known).* {{
        deny all;
    }}
}}
"""

# [FIX] PHP + SSL Template
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

    # [FIX] Upload Limit
    client_max_body_size 128M;

    # [OPTIMASI]
    gzip on;

    location / {{
        try_files $uri $uri/ =404;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php_version}-fpm.sock;

        # [SECURITY CRITICAL] Isolasi Website
        fastcgi_param PHP_ADMIN_VALUE "open_basedir=$document_root:/tmp:/var/lib/php/sessions";
    }}

    location ~ /\\.(?!well-known).* {{
        deny all;
    }}
}}
"""

# Template Proxy (NodeJS/Python) - Juga butuh upload limit
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

    client_max_body_size 128M;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

NGINX_HTTP_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};

    client_max_body_size 128M;

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


def create_nginx_config(domain: str, port: int, type: str, php_version: str = "8.2", custom_socket: str = None):
    if platform.system() == "Windows":
        return

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    # Cek SSL
    ssl_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    has_ssl = subprocess.run(["sudo", "test", "-f", ssl_path], capture_output=True).returncode == 0

    try:
        config_content = ""

        if type == "php":
            if has_ssl:
                config_content = NGINX_PHP_HTTPS_TEMPLATE.format(domain=domain, php_version=php_version)
            else:
                config_content = NGINX_PHP_TEMPLATE.format(domain=domain, php_version=php_version)

            # Support custom socket (jika nanti mau isolasi user linux)
            if custom_socket:
                default_socket = f"unix:/run/php/php{php_version}-fpm.sock"
                target_socket = f"unix:{custom_socket}"
                config_content = config_content.replace(default_socket, target_socket)

        else:
            if has_ssl:
                config_content = NGINX_HTTPS_TEMPLATE.format(domain=domain, port=port)
            else:
                config_content = NGINX_HTTP_TEMPLATE.format(domain=domain, port=port)

        subprocess.run(["sudo", "tee", config_path], input=config_content, text=True, check=True)

        if not subprocess.run(["sudo", "test", "-L", symlink_path], capture_output=True).returncode == 0:
            subprocess.run(["sudo", "ln", "-s", config_path, symlink_path], check=True)

        reload_nginx()
        print(f"✅ Nginx Config updated for {domain} (Type: {type})")

    except Exception as e:
        print(f"❌ Failed creating Nginx config: {e}")


def delete_nginx_config(domain: str):
    if platform.system() == "Windows":
        return

    config_path = f"/etc/nginx/sites-available/{domain}"
    symlink_path = f"/etc/nginx/sites-enabled/{domain}"

    try:
        subprocess.run(["sudo", "rm", "-f", symlink_path], check=False)
        subprocess.run(["sudo", "rm", "-f", config_path], check=False)
        reload_nginx()
        print(f"🗑️ Nginx Config deleted for {domain}")
    except Exception as e:
        print(f"❌ Failed deleting Nginx config: {e}")