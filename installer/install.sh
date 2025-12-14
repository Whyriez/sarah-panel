#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install.sh)"
  exit
fi

echo "🚀 STARTING ALIMPANEL INSTALLATION..."

# 1. UPDATE SYSTEM
echo "📦 Updating System..."
apt update && apt upgrade -y
apt install -y python3-pip python3-venv nginx git mariadb-server curl unzip

# 2. INSTALL NODE.JS (Versi 20 LTS)
echo "📦 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
npm install -g pm2

# 3. SETUP BACKEND
echo "🐍 Setting up Backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Keluar dari venv
deactivate
cd ..

# 4. SETUP FRONTEND
echo "⚛️ Setting up Frontend..."
cd frontend
# Buat file .env production untuk frontend
echo "NEXT_PUBLIC_API_URL=http://$(curl -s ifconfig.me):8000" > .env.local
npm install
npm run build
cd ..

# 5. SETUP SYSTEMD (Auto Start Backend)
echo "⚙️ Creating System Service..."
cat > /etc/systemd/system/alimpanel.service <<EOF
[Unit]
Description=AlimPanel Backend
After=network.target

[Service]
User=root
WorkingDirectory=$(pwd)/backend
ExecStart=$(pwd)/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable alimpanel
systemctl start alimpanel

# 6. SETUP NGINX UTAMA (Untuk akses Panel)
# Panel akan jalan di Port 80 (Tanpa domain dulu, akses via IP)
echo "🌐 Configuring Nginx for Panel UI..."
cat > /etc/nginx/sites-available/default <<EOF
server {
    listen 80 default_server;
    server_name _;

    # Frontend (Next.js) - Kita serve pakai PM2 nanti atau Static Export
    # Untuk MVP, kita proxy ke frontend dev server atau build result
    # Asumsi: Frontend jalan di port 3000
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
    }

    # Backend API
    location /api/ {
        # Redirect /api/v1/... ke localhost:8000/...
        # Note: Di kode Frontend, base URL harusnya http://IP:8000 kalau mau direct
        # Tapi lebih aman via proxy biar gak kena CORS
        proxy_pass http://127.0.0.1:8000/; 
    }
}
EOF

# Restart Nginx
systemctl restart nginx

# 7. START FRONTEND WITH PM2
echo "🚀 Starting Frontend..."
cd frontend
pm2 start npm --name "alimpanel-ui" -- start
pm2 save
pm2 startup

echo "✅ INSTALLATION COMPLETE!"
echo "Try accessing: http://$(curl -s ifconfig.me)"