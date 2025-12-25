#!/bin/bash

# --- CHECK ROOT ---
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install_alma.sh)"
  exit
fi

# --- AUTO-MOVE KE /var/www/sarah-panel ---
CURRENT_DIR=$(pwd)
TARGET_DIR="/var/www/sarah-panel"
PANEL_PORT=8888

echo "🚀 STARTING ALIMPANEL INSTALLATION (ALMA 8 FIX)..."

# Pindahkan file jika belum di lokasi target
if [ "$CURRENT_DIR" != "$TARGET_DIR/installer" ] && [ "$CURRENT_DIR" != "$TARGET_DIR" ]; then
    echo "⚠️  Moving files to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    if [ -d "../backend" ]; then
        cp -rf ../* "$TARGET_DIR/"
    else
        cp -rf * "$TARGET_DIR/"
    fi
    cd "$TARGET_DIR"
    echo "✅ Files moved."
else
    echo "✅ Already in safe directory."
fi

INSTALL_DIR="$TARGET_DIR"
# [FIX] Generate Password MySQL (Hanya Alphanumeric agar aman di URL/CLI)
MYSQL_ROOT_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9')

# --- 0. SWAP MEMORY ---
if [ $(free -m | grep Swap | awk '{print $2}') -eq 0 ]; then
    echo "💾 Creating 2GB Swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- 1. FIREWALL & SELINUX ---
echo "🛡️ Configuring Firewall..."
dnf install firewalld -y
systemctl enable --now firewalld
firewall-cmd --permanent --add-service={http,https,ssh}
firewall-cmd --permanent --add-port=${PANEL_PORT}/tcp
firewall-cmd --reload

# SELinux Permissive
setenforce 0
sed -i 's/^SELINUX=.*/SELINUX=permissive/g' /etc/selinux/config

# --- 2. SYSTEM UPDATE & REPO (FIX EL8) ---
echo "📦 Updating Repositories..."
dnf update -y
dnf install -y epel-release

# [FIX] Gunakan REMI release 8 (Bukan 9)
dnf install -y https://rpms.remirepo.net/enterprise/remi-release-8.rpm
dnf makecache

# Dependencies Dasar
dnf install -y python3 python3-pip python3-devel nginx git mariadb-server curl unzip gcc make tar policycoreutils-python-utils

# --- 3. PHP INSTALLATION (FIX) ---
echo "🐘 Installing PHP 8.2..."
# Reset module php dulu agar tidak conflict
dnf module reset php -y
dnf module enable php:remi-8.2 -y

# Install paket PHP
dnf install -y php php-fpm php-mysqlnd php-common php-curl php-xml php-zip php-gd php-mbstring php-bcmath php-intl php-pecl-imagick

# Pastikan service nyala
systemctl enable --now mariadb
systemctl enable --now nginx
systemctl enable --now php-fpm

# --- 4. NODE.JS & PM2 ---
echo "📦 Installing Node.js..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g pm2

# Fix permission node binary
chmod 755 $(which node) 2>/dev/null
chmod 755 /usr/bin/node 2>/dev/null

# --- 5. CREATE USER ---
echo "👤 Creating System User 'alimpanel'..."
if ! id -u alimpanel > /dev/null 2>&1; then
    useradd -r -m -d /home/alimpanel -s /bin/false alimpanel
fi
chown -R alimpanel:alimpanel "$INSTALL_DIR"
chmod -R 775 "$INSTALL_DIR"

# --- 6. DATABASE SETUP (FIX SYNTAX) ---
echo "🔒 Securing Database..."
# [FIX] Syntax MariaDB 10.3 menggunakan 'IDENTIFIED BY' untuk plaintext
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASS}';"
mysql -e "FLUSH PRIVILEGES;"

cat > /root/.my.cnf <<EOF
[client]
user=root
password=${MYSQL_ROOT_PASS}
EOF

# Install phpMyAdmin Manual
echo "Installing phpMyAdmin..."
cd /usr/share
rm -rf phpmyadmin
curl -L -o phpmyadmin.zip https://files.phpmyadmin.net/phpMyAdmin/5.2.1/phpMyAdmin-5.2.1-all-languages.zip
unzip -q phpmyadmin.zip
mv phpMyAdmin-5.2.1-all-languages phpmyadmin
rm -f phpmyadmin.zip
mkdir -p /usr/share/phpmyadmin/tmp
chmod 777 /usr/share/phpmyadmin/tmp
chown -R nginx:nginx /usr/share/phpmyadmin

cat > /usr/share/phpmyadmin/config.inc.php <<EOF
<?php
\$cfg['blowfish_secret'] = '$(openssl rand -hex 16)'; 
\$i = 0;
\$i++;
\$cfg['Servers'][\$i]['auth_type'] = 'cookie';
\$cfg['Servers'][\$i]['host'] = 'localhost';
\$cfg['Servers'][\$i]['compress'] = false;
\$cfg['Servers'][\$i]['AllowNoPassword'] = false;
\$cfg['TempDir'] = '/usr/share/phpmyadmin/tmp';
?>
EOF

cd "$INSTALL_DIR"

# --- 7. SETUP BACKEND (FIX PYTHON 3.6) ---
echo "🐍 Setting up Backend..."
cd "$INSTALL_DIR/backend"
rm -rf .venv

# Setup venv
sudo -u alimpanel python3 -m venv .venv

# [FIX] Upgrade pip & Install Bcrypt Lama (Kompatibel Python 3.6 di EL8)
# Kita install bcrypt 3.2.2 secara eksplisit sebelum requirements.txt
sudo -u alimpanel bash -c "source .venv/bin/activate && pip install --upgrade pip && pip install bcrypt==3.2.2 && pip install -r requirements.txt"

# Create .env
if [ ! -f .env ]; then
    SECRET=$(openssl rand -hex 32)
    sudo -u alimpanel bash -c "cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sarahpanel.db
MYSQL_ROOT_PASSWORD=\"${MYSQL_ROOT_PASS}\"
EOF"
fi
cd ..

# --- 8. SETUP FRONTEND ---
echo "⚛️ Setting up Frontend..."
cd "$INSTALL_DIR/frontend"
echo "NEXT_PUBLIC_API_URL=/api" > .env.local
sudo -u alimpanel npm install
sudo -u alimpanel npm run build
cd ..

# --- 9. SETUP SYSTEMD ---
echo "⚙️ Creating Backend Service..."
cat > /etc/systemd/system/alimpanel.service <<EOF
[Unit]
Description=AlimPanel Backend API
After=network.target

[Service]
User=alimpanel
Group=alimpanel
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
EnvironmentFile=${INSTALL_DIR}/backend/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable alimpanel
systemctl restart alimpanel

# --- 10. CONFIG NGINX (FIX SOCKET) ---
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/conf.d/alimpanel.conf <<EOF
server {
    listen ${PANEL_PORT} default_server;
    server_name _;
    root /usr/share/phpmyadmin;

    location ^~ /phpmyadmin {
        alias /usr/share/phpmyadmin;
        index index.php index.html;
        location ~ \.php$ {
            fastcgi_pass unix:/run/php-fpm/www.sock;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME \$request_filename;
            include fastcgi_params;
        }
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    location /api/ {
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak 2>/dev/null

# Fix PHP-FPM User (Apache -> Nginx)
if [ -f /etc/php-fpm.d/www.conf ]; then
    sed -i 's/user = apache/user = nginx/g' /etc/php-fpm.d/www.conf
    sed -i 's/group = apache/group = nginx/g' /etc/php-fpm.d/www.conf
    chown -R nginx:nginx /var/lib/php/session /var/lib/php/wsdlcache /var/lib/php/opcache 2>/dev/null
fi
# Buat socket directory jika belum ada (kadang di EL8 hilang)
mkdir -p /run/php-fpm

systemctl restart php-fpm
systemctl restart nginx

# --- 11. START FRONTEND ---
echo "🚀 Starting Frontend..."
cd "$INSTALL_DIR/frontend"
sudo -u alimpanel pm2 delete alimpanel-ui 2>/dev/null || true
sudo -u alimpanel pm2 start npm --name "alimpanel-ui" -- start

echo "⚙️ Generating Startup Script..."
sudo -u alimpanel pm2 save
# [FIX] Ambil command startup bersih tanpa logo
PM2_CMD=$(pm2 startup systemd -u alimpanel --hp /home/alimpanel | grep "sudo env")
if [ ! -z "$PM2_CMD" ]; then
    eval "$PM2_CMD"
else
    # Fallback aman
    pm2 startup systemd -u alimpanel --hp /home/alimpanel | tail -n 1 | bash
fi

# Folder Hosting
mkdir -p /var/www/sarahpanel
chown -R nginx:nginx /var/www/sarahpanel
chmod -R 775 /var/www/sarahpanel
usermod -aG nginx alimpanel

# --- 12. FAIL2BAN & SUDOERS ---
echo "🛡️ Security Config..."
cat > /etc/sudoers.d/alimpanel <<EOF
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
alimpanel ALL=(root) NOPASSWD: /usr/bin/certbot
alimpanel ALL=(root) NOPASSWD: /usr/bin/tee /etc/nginx/conf.d/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/rm /etc/nginx/conf.d/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl restart php-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/dnf
EOF
dnf install -y fail2ban
systemctl enable --now fail2ban
cat > /etc/fail2ban/jail.local <<EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/secure
maxretry = 3
bantime = 3600
EOF
systemctl restart fail2ban

PUBLIC_IP=$(curl -s ifconfig.me)
echo ""
echo "✅ INSTALLATION SUCCESSFUL!"
echo "➡️  Login Panel: http://${PUBLIC_IP}:${PANEL_PORT}"
echo "🔑 MySQL Root Pass: Saved in $INSTALL_DIR/backend/.env"