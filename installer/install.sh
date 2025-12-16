#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install.sh)"
  exit
fi

INSTALL_DIR=$(pwd)
PANEL_PORT=8888

echo "🚀 STARTING ALIMPANEL INSTALLATION..."

# --- [BARU] 0. SETUP SWAP MEMORY (Penting untuk VPS RAM < 2GB) ---
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

# 1. UPDATE SYSTEM & FIREWALL
echo "📦 Updating System..."
apt update && apt upgrade -y
apt install -y ufw

# --- [BARU] SETUP FIREWALL (UFW) ---
echo "🛡️ Configuring Firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS
ufw allow ${PANEL_PORT}/tcp # Panel Port
# ufw enable # Jangan auto enable dulu takut ke-lock, user harus enable manual nanti
echo "✅ Firewall rules added (Run 'ufw enable' manually later)"

# Install Dependencies
apt install -y python3-pip python3-venv nginx git mariadb-server curl unzip certbot python3-certbot-nginx

# [BARU] Tambahkan Repository PHP Ondrej
echo "🐘 Adding PHP Repository..."
apt install -y software-properties-common
add-apt-repository ppa:ondrej/php -y
apt update

# Install Versi PHP Populer
for version in 7.4 8.0 8.1 8.2; do
    echo "📦 Installing PHP $version..."
    apt install -y php$version-fpm php$version-mysql php$version-common php$version-curl php$version-xml php$version-zip php$version-gd php$version-mbstring php$version-bcmath php$version-intl php$version-imagick
    systemctl enable php$version-fpm
    systemctl start php$version-fpm
done

# --- [FIX] AMANKAN MYSQL DATABASE ---
echo "🔒 Securing MySQL..."
# Generate Password Random untuk Root MySQL
MYSQL_ROOT_PASS=$(openssl rand -base64 24)

# Set password root MySQL (Tanpa interaksi user)
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASS}'; FLUSH PRIVILEGES;"
echo "✅ MySQL Root Password set."

# Buat file kredensial agar root sistem tetap bisa akses mysql tanpa password (opsional tapi memudahkan maintenance)
cat > /root/.my.cnf <<EOF
[client]
user=root
password=${MYSQL_ROOT_PASS}
EOF

# 2. INSTALL NODE.JS
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs build-essential
npm install -g pm2

# 3. SETUP BACKEND
echo "🐍 Setting up Backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# --- [FIX] Generate .env Backend dengan Password MySQL ---
if [ ! -f .env ]; then
    echo "⚙️ Generating Backend .env..."
    SECRET=$(openssl rand -hex 32)
    
    cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sarahpanel.db

# [PENTING] Simpan Password MySQL Root di sini agar Backend bisa baca
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASS}"
EOF
fi

deactivate
cd ..

# Install phpMyAdmin
sudo apt install -y phpmyadmin

# Pilih 'apache2' atau kosongkan saja (tab -> enter) saat ditanya web server, karena kita pakai Nginx.
# Pilih 'Yes' untuk dbconfig-common.
# Masukkan password root MySQL yang ada di file .env backend Anda.

# Buat Symlink agar bisa diakses
sudo ln -s /usr/share/phpmyadmin /var/www/html/phpmyadmin

# Fix Permission untuk Nginx (karena defaultnya root)
sudo chown -R www-data:www-data /usr/share/phpmyadmin

# 4. SETUP FRONTEND
echo "⚛️ Setting up Frontend..."
cd frontend
PUBLIC_IP=$(curl -s ifconfig.me)
echo "NEXT_PUBLIC_API_URL=http://${PUBLIC_IP}:${PANEL_PORT}/api" > .env.local
npm install
npm run build
cd ..

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

# Setup Sudoers (Sama seperti sebelumnya, tidak diubah)
echo "🔓 Configuring Sudoers for alimpanel..."
cat > /etc/sudoers.d/alimpanel <<EOF
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl reload nginx
alimpanel ALL=(root) NOPASSWD: /usr/bin/certbot
alimpanel ALL=(root) NOPASSWD: /usr/bin/tee /etc/nginx/sites-available/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/ln -s /etc/nginx/sites-available/* /etc/nginx/sites-enabled/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/rm /etc/nginx/sites-enabled/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/rm /etc/nginx/sites-available/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl restart php*-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl start php*-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/systemctl enable php*-fpm
alimpanel ALL=(root) NOPASSWD: /usr/bin/apt-get install -y php*
alimpanel ALL=(root) NOPASSWD: /usr/bin/apt-get remove -y php*
alimpanel ALL=(root) NOPASSWD: /usr/bin/apt-get update
alimpanel ALL=(root) NOPASSWD: /usr/bin/apt-get autoremove -y
alimpanel ALL=(root) NOPASSWD: /usr/bin/tee /etc/php/*/fpm/pool.d/*
alimpanel ALL=(root) NOPASSWD: /usr/bin/rm /etc/php/*/fpm/pool.d/*
EOF

# 6. SETUP NGINX UTAMA
echo "🌐 Configuring Nginx for Panel UI (Port ${PANEL_PORT})..."
cat > /etc/nginx/sites-available/alimpanel <<EOF
server {
    listen ${PANEL_PORT} default_server;
    server_name _;

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

rm /etc/nginx/sites-enabled/default 2>/dev/null
ln -s /etc/nginx/sites-available/alimpanel /etc/nginx/sites-enabled/alimpanel 2>/dev/null

systemctl restart nginx

# 7. START FRONTEND
echo "🚀 Starting Frontend..."
cd frontend
pm2 delete alimpanel-ui 2>/dev/null || true
pm2 start npm --name "alimpanel-ui" -- start
cd ..

pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 100M
pm2 set pm2-logrotate:retain 7
pm2 set pm2-logrotate:compress true

echo "⚙️ Configuring PM2 Startup..."
pm2 startup systemd -u alimpanel --hp /home/alimpanel | bash
pm2 save

mkdir -p /var/www/sarahpanel
chown -R alimpanel:alimpanel /var/www/sarahpanel
chmod -R 755 /var/www/sarahpanel

echo "✅ INSTALLATION COMPLETE!"
echo "🔑 MySQL Root Password saved in backend/.env"
echo "➡️  Access Panel: http://${PUBLIC_IP}:${PANEL_PORT}"