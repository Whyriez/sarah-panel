#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install_alma.sh)"
  exit
fi

# --- [FIX FATAL] AUTO-MOVE KE DIRECTORY AMAN ---
# Kita pindahkan paksa ke /var/www agar user 'alimpanel' bisa akses
CURRENT_DIR=$(pwd)
TARGET_DIR="/var/www/sarah-panel"
PANEL_PORT=8888

echo "🚀 STARTING ALIMPANEL INSTALLATION (ALMALINUX EDITION)..."
echo "📂 Source: $CURRENT_DIR"
echo "📂 Target: $TARGET_DIR"

# Jika belum di target directory, pindahkan file
if [ "$CURRENT_DIR" != "$TARGET_DIR/installer" ] && [ "$CURRENT_DIR" != "$TARGET_DIR" ]; then
    echo "⚠️  Moving files to safe directory ($TARGET_DIR)..."
    mkdir -p "$TARGET_DIR"
    
    # Copy semua file project ke target
    if [ -d "../backend" ]; then
        cp -rf ../* "$TARGET_DIR/"
    else
        cp -rf * "$TARGET_DIR/"
    fi
    
    # Pindah ke directory target
    cd "$TARGET_DIR"
    echo "✅ Files moved."
else
    echo "✅ Already in safe directory."
fi

INSTALL_DIR="$TARGET_DIR"

# Generate Password MySQL
MYSQL_ROOT_PASS=$(openssl rand -base64 24)
echo "🔑 Generated MySQL Password: $MYSQL_ROOT_PASS"

# --- 0. SETUP SWAP MEMORY ---
echo "💾 Checking Swap Memory..."
if [ $(free -m | grep Swap | awk '{print $2}') -eq 0 ]; then
    echo "⚠️ No Swap detected. Creating 2GB Swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
    echo "✅ Swap Created."
else
    echo "✅ Swap already exists."
fi

# 1. SETUP FIREWALL & SELINUX
echo "🛡️ Configuring Firewall & SELinux..."
dnf install firewalld -y
systemctl enable --now firewalld

# Buka port
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-port=${PANEL_PORT}/tcp
firewall-cmd --reload
echo "✅ Firewall rules added."

# Set SELinux ke Permissive (Penting agar Nginx bisa baca socket backend)
setenforce 0
sed -i 's/^SELINUX=.*/SELINUX=permissive/g' /etc/selinux/config

# 2. UPDATE SYSTEM & DEPENDENCIES
echo "📦 Updating System & Repositories..."
dnf update -y
dnf install -y epel-release
# Install Repo REMI (PHP)
dnf install -y https://rpms.remirepo.net/enterprise/remi-release-9.rpm

# Install Dependencies Dasar
dnf install -y python3 python3-pip python3-devel nginx git mariadb-server curl unzip gcc make tar policycoreutils-python-utils

# Enable PHP 8.2
dnf module reset php -y
dnf module enable php:remi-8.2 -y

# Install PHP
echo "📦 Installing PHP 8.2..."
dnf install -y php php-fpm php-mysqlnd php-common php-curl php-xml php-zip php-gd php-mbstring php-bcmath php-intl php-pecl-imagick

# Start Service
systemctl enable --now mariadb
systemctl enable --now nginx
systemctl enable --now php-fpm

# 3. INSTALL NODE.JS & FIX PERMISSION
echo "📦 Installing Node.js..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g pm2

# [FIX] Pastikan binary node bisa dieksekusi oleh semua user (mengatasi EACCES)
chmod 755 $(which node) 2>/dev/null
chmod 755 /usr/bin/node 2>/dev/null

# 4. CREATE SYSTEM USER (Dilakukan SEBELUM setup backend)
echo "👤 Creating System User..."
if ! id -u alimpanel > /dev/null 2>&1; then
    useradd -r -m -d /home/alimpanel -s /bin/false alimpanel
fi

# [PENTING] Set permission folder project ke user alimpanel
chown -R alimpanel:alimpanel "$INSTALL_DIR"
chmod -R 775 "$INSTALL_DIR"

# 5. SETUP MYSQL & PHPMYADMIN
echo "🔒 Securing MySQL..."
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_ROOT_PASS}'); FLUSH PRIVILEGES;"
echo "✅ MySQL Root Password set."

cat > /root/.my.cnf <<EOF
[client]
user=root
password=${MYSQL_ROOT_PASS}
EOF

echo "🐘 Installing phpMyAdmin..."
cd /usr/share
curl -L -o phpmyadmin.zip https://files.phpmyadmin.net/phpMyAdmin/5.2.1/phpMyAdmin-5.2.1-all-languages.zip
unzip -q phpmyadmin.zip
mv phpMyAdmin-5.2.1-all-languages phpmyadmin
rm -f phpmyadmin.zip
# Fix permissions (User nginx)
chown -R nginx:nginx /usr/share/phpmyadmin
chmod -R 755 /usr/share/phpmyadmin
mkdir -p /usr/share/phpmyadmin/tmp
chmod 777 /usr/share/phpmyadmin/tmp
cd "$INSTALL_DIR"

# Config phpMyAdmin
cat > /usr/share/phpmyadmin/config.inc.php <<EOF
<?php
\$cfg['blowfish_secret'] = '$(openssl rand -hex 16)'; 
\$i = 0;
\$i++;
\$cfg['Servers'][\$i]['auth_type'] = 'cookie';
\$cfg['Servers'][\$i]['host'] = 'localhost';
\$cfg['Servers'][\$i]['compress'] = false;
\$cfg['Servers'][\$i]['AllowNoPassword'] = false;
\$cfg['UploadDir'] = '';
\$cfg['SaveDir'] = '';
\$cfg['TempDir'] = '/usr/share/phpmyadmin/tmp';
?>
EOF

# 6. SETUP BACKEND (Running as User)
echo "🐍 Setting up Backend..."
cd "$INSTALL_DIR/backend"

# Hapus venv lama (bersih-bersih)
rm -rf .venv

# Install sebagai user alimpanel
sudo -u alimpanel python3 -m venv .venv
sudo -u alimpanel bash -c "source .venv/bin/activate && pip install -r requirements.txt"

# Generate .env
if [ ! -f .env ]; then
    echo "⚙️ Generating Backend .env..."
    SECRET=$(openssl rand -hex 32)
    
    sudo -u alimpanel bash -c "cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sarahpanel.db
MYSQL_ROOT_PASSWORD=\"${MYSQL_ROOT_PASS}\"
EOF"
fi

cd ..

# 7. SETUP FRONTEND (Running as User)
echo "⚛️ Setting up Frontend..."
cd "$INSTALL_DIR/frontend"
echo "NEXT_PUBLIC_API_URL=/api" > .env.local

# Install & Build sebagai user alimpanel
sudo -u alimpanel npm install
sudo -u alimpanel npm run build
cd ..

# 8. SETUP SYSTEMD
echo "⚙️ Creating System Service..."
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

# Setup Sudoers
echo "🔓 Configuring Sudoers for alimpanel..."
cat > /etc/sudoers.d/alimpanel <<EOF
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
alimpanel ALL=(root) NOPASSWD: /usr/bin/certbot
alimpanel ALL=(root) NOPASSWD: /usr/bin/tee /etc/nginx/conf.d/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/rm /etc/nginx/conf.d/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl restart php-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl start php-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl enable php-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/dnf install -y php*
alimpanel ALL=(root) NOPASSWD: /usr/bin/dnf remove -y php*
alimpanel ALL=(root) NOPASSWD: /usr/bin/dnf update
EOF

echo "🛡️ Installing Fail2Ban..."
dnf install -y fail2ban
systemctl enable fail2ban
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

# 9. SETUP NGINX UTAMA
echo "🌐 Configuring Nginx for Panel UI..."
cat > /etc/nginx/conf.d/alimpanel.conf <<EOF
server {
    listen ${PANEL_PORT} default_server;
    server_name _;
    root /usr/share/phpmyadmin;

    # 1. Config Khusus phpMyAdmin
    location ^~ /phpmyadmin {
        alias /usr/share/phpmyadmin;
        index index.php index.html index.htm;
        location ~ \.php$ {
            fastcgi_pass unix:/run/php-fpm/www.sock;
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME \$request_filename;
            include fastcgi_params;
        }
    }

    # 2. Frontend Proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # 3. Backend API Proxy
    location /api/ {
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Disable default
mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak 2>/dev/null

# Fix PHP-FPM User (Apache -> Nginx)
sed -i 's/user = apache/user = nginx/g' /etc/php-fpm.d/www.conf
sed -i 's/group = apache/group = nginx/g' /etc/php-fpm.d/www.conf
chown -R nginx:nginx /var/lib/php/session /var/lib/php/wsdlcache /var/lib/php/opcache 2>/dev/null

systemctl restart php-fpm
systemctl restart nginx

# 10. START FRONTEND (PM2)
echo "🚀 Starting Frontend..."
cd "$INSTALL_DIR/frontend"

# Jalankan PM2 sebagai user alimpanel
sudo -u alimpanel pm2 delete alimpanel-ui 2>/dev/null || true
sudo -u alimpanel pm2 start npm --name "alimpanel-ui" -- start

cd ..
sudo -u alimpanel pm2 install pm2-logrotate
sudo -u alimpanel pm2 save
# Generate startup script
pm2 startup systemd -u alimpanel --hp /home/alimpanel | bash

# Buat folder hosting
mkdir -p /var/www/sarahpanel
chown -R nginx:nginx /var/www/sarahpanel
chmod -R 775 /var/www/sarahpanel
usermod -aG nginx alimpanel

PUBLIC_IP=$(curl -s ifconfig.me)
echo "✅ INSTALLATION COMPLETE!"
echo "📂 Location: $INSTALL_DIR"
echo "🔑 MySQL Root Password saved in backend/.env"
echo "➡️  Access Panel: http://${PUBLIC_IP}:${PANEL_PORT}"