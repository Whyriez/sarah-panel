#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install.sh)"
  exit
fi

# Set Absolute Path untuk instalasi (Biar konsisten)
INSTALL_DIR=$(pwd)
PANEL_PORT=8888

echo "🚀 STARTING ALIMPANEL INSTALLATION..."

# 1. UPDATE SYSTEM
echo "📦 Updating System..."
apt update && apt upgrade -y
apt install -y python3-pip python3-venv nginx git mariadb-server curl unzip certbot python3-certbot-nginx

# [BARU] Tambahkan Repository PHP Ondrej (Standar Industri)
echo "🐘 Adding PHP Repository..."
apt install -y software-properties-common
add-apt-repository ppa:ondrej/php -y
apt update

# Install Versi PHP Populer (7.4, 8.0, 8.1, 8.2) + Modules Standard
# Kita install FPM (FastCGI Process Manager) karena Nginx butuh ini
for version in 7.4 8.0 8.1 8.2; do
    echo "📦 Installing PHP $version..."
    apt install -y php$version-fpm php$version-mysql php$version-common php$version-curl php$version-xml php$version-zip php$version-gd php$version-mbstring php$version-bcmath
    
    # Pastikan service jalan
    systemctl enable php$version-fpm
    systemctl start php$version-fpm
done

# 2. INSTALL NODE.JS (Versi 20 LTS)
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

# [FIX] Generate .env untuk Backend agar Secure
if [ ! -f .env ]; then
    echo "⚙️ Generating Backend .env..."
    # Generate random key 32 karakter
    SECRET=$(openssl rand -hex 32)
    
    # Sesuaikan variable ini dengan yang dipakai di config.py backend Anda
    cat > .env <<EOF
SECRET_KEY=${SECRET}
ACCESS_TOKEN_EXPIRE_MINUTES=1440
# Database URL (Default SQLite, ganti ke MySQL jika perlu)
DATABASE_URL=sqlite:///./sarahpanel.db
EOF
fi

deactivate
cd ..

# 4. SETUP FRONTEND
echo "⚛️ Setting up Frontend..."
cd frontend
# Point API ke Public IP dengan port Backend (8000)
# Atau jika mau lebih secure, nanti diproxy via Nginx Admin Port
PUBLIC_IP=$(curl -s ifconfig.me)
echo "NEXT_PUBLIC_API_URL=http://${PUBLIC_IP}:${PANEL_PORT}/api" > .env.local
npm install
npm run build
cd ..

# 5. SETUP SYSTEMD (Auto Start Backend)
echo "⚙️ Creating System Service..."

# [BARU] 1. Buat user sistem khusus 'alimpanel' (jika belum ada)
# -r: system account, -s /bin/false: tidak bisa login shell (aman)
if ! id -u alimpanel > /dev/null 2>&1; then
    # -m: Create Home Directory
    # -d: Tentukan path home directory
    useradd -r -m -d /home/alimpanel -s /bin/false alimpanel
fi

# [BARU] 2. Ubah kepemilikan folder backend ke user 'alimpanel'
# Agar user tersebut punya hak baca/tulis di folder aplikasi & db
chown -R alimpanel:alimpanel ${INSTALL_DIR}/backend

# [BARU] 3. Update Service agar berjalan sebagai 'alimpanel'
cat > /etc/systemd/system/alimpanel.service <<EOF
[Unit]
Description=AlimPanel Backend API
After=network.target

[Service]
# Ganti dari root ke alimpanel
User=alimpanel
Group=alimpanel

WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

# Environment variables (PENTING: agar backend bisa baca .env)
EnvironmentFile=${INSTALL_DIR}/backend/.env

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable alimpanel
systemctl restart alimpanel

echo "🔓 Configuring Sudoers for alimpanel..."
# Memberi izin user alimpanel menjalankan perintah root tertentu tanpa password
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
EOF

# 6. SETUP NGINX UTAMA (Admin Panel Only)
# [FIX] Kita pindahkan Panel ke Port 8888 supaya Port 80/443 murni untuk User Sites
echo "🌐 Configuring Nginx for Panel UI (Port ${PANEL_PORT})..."
cat > /etc/nginx/sites-available/alimpanel <<EOF
server {
    listen ${PANEL_PORT} default_server;
    server_name _;

    # Frontend Proxy (Next.js berjalan di 3000)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API Proxy
    location /api/ {
        # Hilangkan /api prefix saat pass ke backend jika backend root-nya bukan /api
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Hapus default nginx config biar ga bentrok di port 80 (opsional, tapi disarankan)
rm /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/alimpanel /etc/nginx/sites-enabled/alimpanel

systemctl restart nginx

# 7. START FRONTEND WITH PM2 & FREEZE PROCESS
echo "🚀 Starting Frontend..."
cd frontend
# Hapus process lama jika ada
pm2 delete alimpanel-ui 2>/dev/null || true
pm2 start npm --name "alimpanel-ui" -- start
cd ..

# [FIX] Setup PM2 Startup Script agar otomatis jalan pas reboot
echo "⚙️ Configuring PM2 Startup..."
# Ini akan mendeteksi sistem init (systemd) dan menjalankannya
pm2 startup systemd -u alimpanel --hp /home/alimpanel | bash
pm2 save

echo "📂 Preparing Web Directory..."
# Buat folder untuk menampung website user
mkdir -p /var/www/sarahpanel
# Pastikan user alimpanel yang punya folder ini
chown -R alimpanel:alimpanel /var/www/sarahpanel
chmod -R 755 /var/www/sarahpanel

echo "✅ INSTALLATION COMPLETE!"
echo "➡️  Access Panel: http://${PUBLIC_IP}:${PANEL_PORT}"