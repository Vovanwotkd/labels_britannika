#!/bin/bash
# Britannica Labels - Installation Script
# Ubuntu/Debian automatic installation

set -e  # Exit on error

echo "========================================"
echo "Britannica Labels - Installation Script"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    echo "   Run as regular user with sudo privileges"
    exit 1
fi

# Check sudo
if ! sudo -v; then
    echo "❌ This script requires sudo privileges"
    exit 1
fi

# Variables
INSTALL_DIR="/opt/labels_britannika"
SERVICE_USER="britannica"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "📂 Installation directory: $INSTALL_DIR"
echo "👤 Service user: $SERVICE_USER"
echo ""

# 1. Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. Install dependencies
echo "📦 Installing dependencies..."
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    git \
    curl \
    netcat

# Install Node.js
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# 3. Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "👤 Creating service user: $SERVICE_USER"
    sudo useradd -r -s /bin/false $SERVICE_USER
fi

# 4. Copy files
echo "📂 Copying files to $INSTALL_DIR..."
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory $INSTALL_DIR already exists"
    read -p "   Remove and reinstall? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm -rf "$INSTALL_DIR"
    else
        echo "❌ Installation cancelled"
        exit 1
    fi
fi

sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
sudo chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR"

# 5. Backend setup
echo "🐍 Setting up Backend..."
cd "$INSTALL_DIR/backend"

sudo -u $SERVICE_USER python3.11 -m venv venv
sudo -u $SERVICE_USER venv/bin/pip install --upgrade pip
sudo -u $SERVICE_USER venv/bin/pip install -r requirements.txt

# Check .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    sudo cp .env.example .env
    sudo chown $SERVICE_USER:$SERVICE_USER .env
    echo ""
    echo "📝 Please edit $INSTALL_DIR/backend/.env with your configuration:"
    echo "   - SH5_PASS (Store House password)"
    echo "   - SECRET_KEY (generate with: python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "   - PRINTER_IP (printer IP address)"
    echo ""
    read -p "Press Enter to edit .env now or Ctrl+C to exit..."
    sudo nano "$INSTALL_DIR/backend/.env"
fi

# Initialize database
echo "💾 Initializing database..."
sudo -u $SERVICE_USER venv/bin/python scripts/init_db.py

# 6. Frontend setup
echo "⚛️  Setting up Frontend..."
cd "$INSTALL_DIR/frontend"

sudo -u $SERVICE_USER npm install
sudo -u $SERVICE_USER npm run build

# 7. Install systemd service
echo "⚙️  Installing systemd service..."
sudo cp "$INSTALL_DIR/deploy/britannica-backend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable britannica-backend
sudo systemctl start britannica-backend

# Check service status
if sudo systemctl is-active --quiet britannica-backend; then
    echo "✅ Backend service started successfully"
else
    echo "❌ Backend service failed to start"
    echo "   Check logs with: sudo journalctl -u britannica-backend -n 50"
    exit 1
fi

# 8. Configure nginx
echo "🌐 Configuring Nginx..."
sudo cp "$INSTALL_DIR/deploy/nginx-britannica.conf" /etc/nginx/sites-available/britannica-labels

if [ -f "/etc/nginx/sites-enabled/britannica-labels" ]; then
    sudo rm /etc/nginx/sites-enabled/britannica-labels
fi

sudo ln -s /etc/nginx/sites-available/britannica-labels /etc/nginx/sites-enabled/

# Test nginx config
if sudo nginx -t; then
    sudo systemctl restart nginx
    echo "✅ Nginx configured and restarted"
else
    echo "❌ Nginx configuration test failed"
    exit 1
fi

# 9. Configure firewall
if command -v ufw &> /dev/null; then
    echo "🔥 Configuring firewall..."
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
fi

# 10. Create backup script
echo "💾 Creating backup script..."
sudo tee /opt/britannica-backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/britannica"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup databases
cp /opt/labels_britannika/backend/data/britannica_labels.db $BACKUP_DIR/britannica_labels_$DATE.db 2>/dev/null || true
cp /opt/labels_britannika/backend/dishes_with_extras.sqlite $BACKUP_DIR/dishes_with_extras_$DATE.sqlite 2>/dev/null || true

# Remove backups older than 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.sqlite" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

sudo chmod +x /opt/britannica-backup.sh

# 11. Setup cron jobs
echo "⏰ Setting up cron jobs..."
(sudo crontab -l 2>/dev/null; echo "# Britannica Labels - Daily backup at 4:00 AM") | sudo crontab -
(sudo crontab -l 2>/dev/null; echo "0 4 * * * /opt/britannica-backup.sh >> /var/log/britannica-backup.log 2>&1") | sudo crontab -

echo ""
echo "========================================"
echo "✅ Installation completed successfully!"
echo "========================================"
echo ""
echo "📊 Service Status:"
sudo systemctl status britannica-backend --no-pager
echo ""
echo "🌐 Access the application:"
echo "   http://$(hostname -I | awk '{print $1}')"
echo "   or http://localhost"
echo ""
echo "🔑 Default credentials:"
echo "   Login: admin"
echo "   Password: admin"
echo ""
echo "📝 Next steps:"
echo "   1. Configure dishes sync:"
echo "      cd $INSTALL_DIR/backend"
echo "      cp export_dishes_with_extras.py.example export_dishes_with_extras.py"
echo "      nano export_dishes_with_extras.py"
echo "      sudo -u $SERVICE_USER venv/bin/python export_dishes_with_extras.py"
echo ""
echo "   2. Test printer connection:"
echo "      curl -X POST http://localhost:8000/api/print/test"
echo ""
echo "   3. View logs:"
echo "      sudo journalctl -u britannica-backend -f"
echo ""
echo "📚 Documentation:"
echo "   $INSTALL_DIR/DEPLOYMENT.md"
echo ""
