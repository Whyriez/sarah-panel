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
# [FIX] Menggunakan Absolute Path yang valid dari INSTALL_DIR
echo "⚙️ Creating System Service..."
cat > /etc/systemd/system/alimpanel.service <<EOF
[Unit]
Description=AlimPanel Backend API
After=network.target

[Service]
User=root
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable alimpanel
systemctl restart alimpanel

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
pm2 startup systemd -u root --hp /root | bash
pm2 save

echo "✅ INSTALLATION COMPLETE!"
echo "➡️  Access Panel: http://${PUBLIC_IP}:${PANEL_PORT}"