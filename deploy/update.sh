#!/bin/bash
# Britannica Labels - Update Script

set -e

INSTALL_DIR="/opt/labels_britannika"
SERVICE_USER="britannica"

echo "========================================"
echo "Britannica Labels - Update Script"
echo "========================================"
echo ""

# Check if installed
if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Britannica Labels is not installed in $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR"

# 1. Create backup
echo "💾 Creating backup..."
BACKUP_DIR="/opt/backups/britannica/update_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
sudo cp -r backend/data "$BACKUP_DIR/" 2>/dev/null || true
sudo cp backend/dishes_with_extras.sqlite "$BACKUP_DIR/" 2>/dev/null || true
sudo cp backend/.env "$BACKUP_DIR/" 2>/dev/null || true
echo "   Backup saved to: $BACKUP_DIR"

# 2. Pull latest code
echo "📥 Pulling latest code from git..."
sudo -u $SERVICE_USER git fetch origin
sudo -u $SERVICE_USER git pull origin main

# 3. Update backend dependencies
echo "🐍 Updating backend dependencies..."
cd "$INSTALL_DIR/backend"
sudo -u $SERVICE_USER venv/bin/pip install --upgrade pip
sudo -u $SERVICE_USER venv/bin/pip install -r requirements.txt

# 4. Run database migrations (if any)
echo "💾 Running database migrations..."
# TODO: Add migration script if needed
# sudo -u $SERVICE_USER venv/bin/python scripts/migrate.py

# 5. Update frontend
echo "⚛️  Building frontend..."
cd "$INSTALL_DIR/frontend"
sudo -u $SERVICE_USER npm install
sudo -u $SERVICE_USER npm run build

# 6. Restart services
echo "🔄 Restarting services..."
sudo systemctl restart britannica-backend

# Check if service started successfully
sleep 2
if sudo systemctl is-active --quiet britannica-backend; then
    echo "✅ Backend service restarted successfully"
else
    echo "❌ Backend service failed to start"
    echo "   Rolling back..."
    sudo -u $SERVICE_USER git reset --hard HEAD@{1}
    sudo systemctl restart britannica-backend
    echo "   Rolled back to previous version"
    exit 1
fi

# Reload nginx
sudo systemctl reload nginx

echo ""
echo "========================================"
echo "✅ Update completed successfully!"
echo "========================================"
echo ""
echo "📊 Service Status:"
sudo systemctl status britannica-backend --no-pager
echo ""
echo "📝 View logs:"
echo "   sudo journalctl -u britannica-backend -f"
echo ""
