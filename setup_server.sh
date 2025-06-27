#!/bin/bash

# CrackPi Server Setup Script
# This script sets up the CrackPi main server on a Raspberry Pi

set -e

echo "========================================="
echo "CrackPi Server Setup"
echo "========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Please run as a regular user with sudo privileges."
   exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRACKPI_DIR="$SCRIPT_DIR"

print_status "Starting CrackPi server setup..."
print_status "Installation directory: $CRACKPI_DIR"

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
print_status "Installing required system packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    sqlite3 \
    nginx \
    supervisor \
    nmap \
    hashcat \
    john \
    curl \
    htop \
    screen \
    tmux

# Install additional wordlists
print_status "Installing wordlists..."
sudo apt install -y wordlists
if [ ! -f /usr/share/wordlists/rockyou.txt ]; then
    print_warning "RockYou wordlist not found. Downloading..."
    sudo mkdir -p /usr/share/wordlists
    cd /tmp
    wget https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
    sudo mv rockyou.txt /usr/share/wordlists/
    cd "$CRACKPI_DIR"
fi

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install \
    flask \
    flask-sqlalchemy \
    flask-login \
    flask-socketio \
    psutil \
    python-nmap \
    netifaces \
    paramiko \
    python-socketio \
    eventlet \
    gunicorn \
    werkzeug

# Create necessary directories
print_status "Creating directories..."
sudo mkdir -p /var/log/crackpi
sudo mkdir -p /etc/crackpi
sudo mkdir -p /var/lib/crackpi
sudo mkdir -p "$CRACKPI_DIR/uploads"

# Set permissions
sudo chown -R $USER:$USER /var/log/crackpi
sudo chown -R $USER:$USER /var/lib/crackpi
sudo chown -R $USER:$USER "$CRACKPI_DIR"

# Create configuration file
print_status "Creating configuration file..."
cat > /etc/crackpi/server.conf << EOF
# CrackPi Server Configuration

[server]
host = 0.0.0.0
port = 5000
debug = false
secret_key = $(openssl rand -hex 32)

[database]
url = sqlite:///var/lib/crackpi/crackpi.db

[paths]
upload_dir = $CRACKPI_DIR/uploads
wordlists_dir = /usr/share/wordlists
rules_dir = /usr/share/hashcat/rules

[tools]
hashcat_path = /usr/bin/hashcat
john_path = /usr/bin/john

[network]
scan_interval = 300
client_timeout = 1800
EOF

sudo chown root:root /etc/crackpi/server.conf
sudo chmod 644 /etc/crackpi/server.conf

# Copy systemd service file
print_status "Installing systemd service..."
sudo cp "$CRACKPI_DIR/crackpi-server.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Initialize database
print_status "Initializing database..."
cd "$CRACKPI_DIR"
source venv/bin/activate
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database initialized successfully')
"

# Configure nginx (optional)
read -p "Do you want to configure Nginx reverse proxy? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Configuring Nginx..."
    
    sudo tee /etc/nginx/sites-available/crackpi << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    sudo ln -sf /etc/nginx/sites-available/crackpi /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl restart nginx
    sudo systemctl enable nginx
fi

# Configure firewall
print_status "Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow 5000/tcp
if command -v nginx >/dev/null 2>&1; then
    sudo ufw allow 'Nginx Full'
fi
echo "y" | sudo ufw enable

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl enable crackpi-server
sudo systemctl start crackpi-server

# Create desktop shortcut for GUI access
if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    print_status "Creating desktop shortcut..."
    cat > ~/Desktop/CrackPi.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=CrackPi Server
Comment=CrackPi Distributed Password Cracking
Exec=xdg-open http://localhost:5000
Icon=applications-internet
Terminal=false
Categories=Network;Security;
EOF
    chmod +x ~/Desktop/CrackPi.desktop
fi

# Get network information
IP_ADDRESS=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

# Installation complete
print_status "========================================="
print_status "CrackPi Server installation complete!"
print_status "========================================="
print_status ""
print_status "Server Information:"
print_status "  Hostname: $HOSTNAME"
print_status "  IP Address: $IP_ADDRESS"
print_status "  Web Interface: http://$IP_ADDRESS:5000"
print_status ""
print_status "Default Login:"
print_status "  Username: admin"
print_status "  Password: admin123"
print_status ""
print_status "Service Management:"
print_status "  Start:   sudo systemctl start crackpi-server"
print_status "  Stop:    sudo systemctl stop crackpi-server"
print_status "  Restart: sudo systemctl restart crackpi-server"
print_status "  Status:  sudo systemctl status crackpi-server"
print_status "  Logs:    sudo journalctl -u crackpi-server -f"
print_status ""
print_status "Configuration:"
print_status "  Server config: /etc/crackpi/server.conf"
print_status "  Database: /var/lib/crackpi/crackpi.db"
print_status "  Logs: /var/log/crackpi/"
print_status ""

# Check service status
sleep 2
if sudo systemctl is-active --quiet crackpi-server; then
    print_status "✓ CrackPi server is running successfully!"
    print_status "✓ You can now access the web interface at: http://$IP_ADDRESS:5000"
else
    print_error "✗ CrackPi server failed to start. Check logs with: sudo journalctl -u crackpi-server"
fi

print_status ""
print_status "Next steps:"
print_status "1. Access the web interface and change the default admin password"
print_status "2. Set up client Raspberry Pis using the setup_client.sh script"
print_status "3. Configure network settings and client discovery"
print_status ""
print_status "For client setup, copy the CrackPi files to each client Pi and run:"
print_status "  ./setup_client.sh $IP_ADDRESS"
print_status ""
print_warning "Remember to change the default admin password!"
