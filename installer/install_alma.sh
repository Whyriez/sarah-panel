#!/bin/bash

# Pastikan script dijalankan sebagai root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root (sudo bash install_alma.sh)"
  exit
fi

echo "🚀 STARTING ALIMPANEL INSTALLATION (ALMALINUX EDITION)..."

# 1. SETUP FIREWALL & SELINUX (PENTING DI ALMALINUX)
echo "🛡️ Configuring Firewall & SELinux..."
# Buka port HTTP/HTTPS
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
# Set SELinux ke Permissive (Biar Nginx gak diblokir saat akses backend/socket)
setenforce 0
sed -i 's/^SELINUX=.*/SELINUX=permissive/g' /etc/selinux/config

# 2. UPDATE SYSTEM & INSTALL DEPENDENCIES
echo "📦 Updating System..."
dnf update -y
# Install Python, Git, Nginx, MariaDB, Tools Development
dnf install -y python3 python3-pip python3-devel nginx git mariadb-server curl unzip gcc make

# Start Database & Nginx
systemctl enable --now mariadb
systemctl enable --now nginx

# 3. INSTALL NODE.JS (Versi 20 LTS via RPM)
echo "📦 Installing Node.js..."
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
dnf install -y nodejs
npm install -g pm2

# 4. SETUP BACKEND
echo "🐍 Setting up Backend..."
cd backend
# Hapus venv lama jika ada (bekas windows)
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ..

# 5. SETUP FRONTEND
echo "⚛️ Setting up Frontend..."
cd frontend
# Buat file .env production untuk frontend (Ambil IP otomatis)
MY_IP=$(curl -s ifconfig.me)
echo "NEXT_PUBLIC_API_URL=http://$MY_IP:8000" > .env.local

# Hapus node_modules lama (bekas windows) biar bersih
rm -rf node_modules
npm install
npm run build
cd ..

# 6. SETUP SYSTEMD (Auto Start Backend)
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

# 7. SETUP NGINX UTAMA
echo "🌐 Configuring Nginx for Panel UI..."
cat > /etc/nginx/conf.d/alimpanel.conf <<EOF
server {
    listen 80;
    server_name _;

    # Frontend (Next.js) via PM2
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
        proxy_pass http://127.0.0.1:8000/;
    }
}
EOF

# Disable default nginx page jika ada
rm -f /etc/nginx/conf.d/default.conf
# Restart Nginx
systemctl restart nginx

# 8. START FRONTEND WITH PM2
echo "🚀 Starting Frontend..."
cd frontend
pm2 start npm --name "alimpanel-ui" -- start
pm2 save
pm2 startup systemd

echo "✅ INSTALLATION COMPLETE!"
echo "Try accessing: http://$MY_IP"