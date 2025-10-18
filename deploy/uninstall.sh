#!/bin/bash
# Britannica Labels - Uninstall Script

set -e

echo "========================================"
echo "Britannica Labels - Uninstall Script"
echo "========================================"
echo ""

# Warning
echo "⚠️  WARNING: This will remove all Britannica Labels components"
echo "   - Backend service"
echo "   - Frontend files"
echo "   - Nginx configuration"
echo "   - Database files"
echo ""
read -p "Are you sure you want to continue? (yes/NO): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Uninstall cancelled"
    exit 1
fi

# Stop and disable service
echo "🛑 Stopping services..."
if systemctl is-active --quiet britannica-backend; then
    sudo systemctl stop britannica-backend
fi
sudo systemctl disable britannica-backend 2>/dev/null || true
sudo rm -f /etc/systemd/system/britannica-backend.service
sudo systemctl daemon-reload

# Remove nginx configuration
echo "🌐 Removing Nginx configuration..."
sudo rm -f /etc/nginx/sites-enabled/britannica-labels
sudo rm -f /etc/nginx/sites-available/britannica-labels
sudo systemctl reload nginx

# Backup data
echo "💾 Creating final backup..."
BACKUP_DIR="/opt/backups/britannica/uninstall_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
sudo cp -r /opt/labels_britannika/backend/data "$BACKUP_DIR/" 2>/dev/null || true
sudo cp /opt/labels_britannika/backend/dishes_with_extras.sqlite "$BACKUP_DIR/" 2>/dev/null || true
echo "   Backup saved to: $BACKUP_DIR"

# Remove installation directory
echo "🗑️  Removing installation directory..."
sudo rm -rf /opt/labels_britannika

# Remove backup script
sudo rm -f /opt/britannica-backup.sh

# Remove cron jobs
echo "⏰ Removing cron jobs..."
sudo crontab -l 2>/dev/null | grep -v "britannica" | sudo crontab - || true

# Optional: Remove service user
read -p "Remove service user 'britannica'? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo userdel britannica 2>/dev/null || true
fi

echo ""
echo "========================================"
echo "✅ Uninstall completed"
echo "========================================"
echo ""
echo "📦 Backup location: $BACKUP_DIR"
echo ""
