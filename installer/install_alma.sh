#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install_alma.sh)"
  exit
fi

INSTALL_DIR=$(pwd)
PANEL_PORT=8888

MYSQL_ROOT_PASS=$(openssl rand -base64 24)
echo "🔑 Generated MySQL Password: $MYSQL_ROOT_PASS"

echo "🚀 STARTING ALIMPANEL INSTALLATION (ALMALINUX EDITION)..."

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

# 1. SETUP FIREWALL & SELINUX (PENTING DI ALMALINUX)
echo "🛡️ Configuring Firewall & SELinux..."
# Install firewalld jika belum ada
dnf install firewalld -y
systemctl enable --now firewalld

# Buka port
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-port=${PANEL_PORT}/tcp
firewall-cmd --reload
echo "✅ Firewall rules added."

# Set SELinux ke Permissive (Biar Nginx gak diblokir saat akses backend/socket)
setenforce 0
sed -i 's/^SELINUX=.*/SELINUX=permissive/g' /etc/selinux/config

# 2. UPDATE SYSTEM & INSTALL DEPENDENCIES
echo "📦 Updating System & Repositories..."
dnf update -y
dnf install -y epel-release

# Install REMI Repo untuk PHP Terbaru
dnf install -y https://rpms.remirepo.net/enterprise/remi-release-9.rpm
# Jika gagal (mungkin Alma 8), coba URL remi-release-8.rpm, tapi asumsi Alma 9

# Install Dependencies Dasar
dnf install -y python3 python3-pip python3-devel nginx git mariadb-server curl unzip gcc make tar policycoreutils-python-utils

# Enable PHP 8.2 dari Remi
dnf module reset php -y
dnf module enable php:remi-8.2 -y

# Install PHP & Extensions
echo "📦 Installing PHP 8.2..."
dnf install -y php php-fpm php-mysqlnd php-common php-curl php-xml php-zip php-gd php-mbstring php-bcmath php-intl php-pecl-imagick

# Start Database & Nginx & PHP-FPM
systemctl enable --now mariadb
systemctl enable --now nginx
systemctl enable --now php-fpm

# --- AMANKAN MYSQL DATABASE ---
echo "🔒 Securing MySQL..."

# Set password root MySQL
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${MYSQL_ROOT_PASS}'); FLUSH PRIVILEGES;"
echo "✅ MySQL Root Password set."

# Buat file kredensial root
cat > /root/.my.cnf <<EOF
[client]
user=root
password=${MYSQL_ROOT_PASS}
EOF

# --- INSTALL PHPMYADMIN MANUALLY (Lebih aman di RHEL daripada via repo yg kadang bawa Apache) ---
echo "🐘 Installing phpMyAdmin..."
cd /usr/share
# Download versi terbaru (5.2.1 saat ini)
curl -L -o phpmyadmin.zip https://files.phpmyadmin.net/phpMyAdmin/5.2.1/phpMyAdmin-5.2.1-all-languages.zip
unzip -q phpmyadmin.zip
mv phpMyAdmin-5.2.1-all-languages phpmyadmin
rm -f phpmyadmin.zip
# Fix permissions (User nginx)
chown -R nginx:nginx /usr/share/phpmyadmin
chmod -R 755 /usr/share/phpmyadmin
# Buat direktori tmp khusus phpmyadmin
mkdir -p /usr/share/phpmyadmin/tmp
chmod 777 /usr/share/phpmyadmin/tmp
cd $INSTALL_DIR

# Buat config phpMyAdmin minimal
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

# 3. INSTALL NODE.JS
echo "📦 Installing Node.js..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g pm2

# 4. SETUP BACKEND
echo "🐍 Setting up Backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# --- Generate .env Backend ---
if [ ! -f .env ]; then
    echo "⚙️ Generating Backend .env..."
    SECRET=$(openssl rand -hex 32)
    
    cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sarahpanel.db
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASS}"
EOF
fi

deactivate
cd ..

# Fix Permission Folder Backend untuk user alimpanel
# (User alimpanel akan dibuat di langkah selanjutnya)

# 5. SETUP SYSTEMD (User & Permission)
echo "⚙️ Creating System Service..."

if ! id -u alimpanel > /dev/null 2>&1; then
    useradd -r -m -d /home/alimpanel -s /bin/false alimpanel
fi

chown -R alimpanel:alimpanel ${INSTALL_DIR}/backend

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

# Setup Sudoers (Disesuaikan path command AlmaLinux)
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

# Config Fail2Ban (Path log AlmaLinux berbeda: /var/log/secure)
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

# 6. SETUP FRONTEND
echo "⚛️ Setting up Frontend..."
cd frontend
# Gunakan relative path
echo "NEXT_PUBLIC_API_URL=/api" > .env.local
npm install
npm run build
cd ..

# 7. SETUP NGINX UTAMA
echo "🌐 Configuring Nginx for Panel UI (Port ${PANEL_PORT})..."
# Di AlmaLinux, config ada di /etc/nginx/conf.d/
cat > /etc/nginx/conf.d/alimpanel.conf <<EOF
server {
    listen ${PANEL_PORT} default_server;
    server_name _;
    root /usr/share/phpmyadmin; # Default root ke phpmyadmin agar aman, nanti diloveride location

    # 1. Config Khusus phpMyAdmin
    location ^~ /phpmyadmin {
        alias /usr/share/phpmyadmin;
        index index.php index.html index.htm;

        location ~ \.php$ {
            fastcgi_pass unix:/run/php-fpm/www.sock; # Socket default RHEL/Remi
            fastcgi_index index.php;
            fastcgi_param SCRIPT_FILENAME \$request_filename;
            include fastcgi_params;
        }
    }

    # 2. Frontend Proxy (Next.js)
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

# Disable default nginx page jika ada
mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak 2>/dev/null

# Ubah permission php-fpm agar bisa diakses nginx (default RHEL user apache)
# Kita ubah user di www.conf dari apache ke nginx
sed -i 's/user = apache/user = nginx/g' /etc/php-fpm.d/www.conf
sed -i 's/group = apache/group = nginx/g' /etc/php-fpm.d/www.conf
# Ubah owner socket directory
chown -R nginx:nginx /var/lib/php/session
chown -R nginx:nginx /var/lib/php/wsdlcache
chown -R nginx:nginx /var/lib/php/opcache

systemctl restart php-fpm
systemctl restart nginx

# 8. START FRONTEND
echo "🚀 Starting Frontend..."

# Berikan kepemilikan ke user alimpanel
chown -R alimpanel:alimpanel ${INSTALL_DIR}/frontend

cd frontend

# Jalankan PM2 sebagai user alimpanel
sudo -u alimpanel pm2 delete alimpanel-ui 2>/dev/null || true
sudo -u alimpanel pm2 start npm --name "alimpanel-ui" -- start

cd ..

# Install logrotate untuk user alimpanel
sudo -u alimpanel pm2 install pm2-logrotate
sudo -u alimpanel pm2 set pm2-logrotate:max_size 100M
sudo -u alimpanel pm2 set pm2-logrotate:retain 7
sudo -u alimpanel pm2 set pm2-logrotate:compress true

echo "⚙️ Configuring PM2 Startup..."
# Simpan list proses user alimpanel
sudo -u alimpanel pm2 save
# Generate startup script user alimpanel
pm2 startup systemd -u alimpanel --hp /home/alimpanel | bash

# Buat folder kerja web
mkdir -p /var/www/sarahpanel
chown -R nginx:nginx /var/www/sarahpanel # User nginx di Alma
chmod -R 755 /var/www/sarahpanel

# Masukkan user alimpanel ke group nginx
usermod -aG nginx alimpanel

PUBLIC_IP=$(curl -s ifconfig.me)

echo "✅ INSTALLATION COMPLETE!"
echo "🔑 MySQL Root Password saved in backend/.env"
echo "➡️  Access Panel: http://${PUBLIC_IP}:${PANEL_PORT}"