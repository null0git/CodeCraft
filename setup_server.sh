#!/bin/bash
"""
CrackPi Server Setup Script
Installs and configures the CrackPi server with all dependencies
"""

set -e  # Exit on any error

echo "🚀 Setting up CrackPi Server..."

# Auto-detect user and configuration
CURRENT_USER=$(whoami)
CRACKPI_USER="${CURRENT_USER}"
CRACKPI_DIR="/home/${CURRENT_USER}/crackpi"
LOG_DIR="/var/log/crackpi"
SERVICE_NAME="crackpi-server"

# If running as root, use a dedicated user
if [[ $EUID -eq 0 ]]; then
    CRACKPI_USER="crackpi"
    CRACKPI_DIR="/opt/crackpi"
    
    # Create dedicated user
    if ! id "$CRACKPI_USER" &>/dev/null; then
        useradd -r -s /bin/bash -m -d "$CRACKPI_DIR" "$CRACKPI_USER"
        print_status "Created dedicated user: $CRACKPI_USER"
    fi
fi

# Function to print colored output
print_status() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root. Please run as the pi user."
    exit 1
fi

print_status "Starting CrackPi Server installation..."

# Update system packages
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
print_status "Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    sqlite3 \
    git \
    curl \
    nmap \
    htop \
    nginx \
    ufw

# Install password cracking tools
print_status "Installing password cracking tools..."
sudo apt install -y john hashcat || print_warning "Some cracking tools may not be available in repositories"

# Create CrackPi directory
print_status "Setting up CrackPi directory..."
mkdir -p $CRACKPI_DIR
cd $CRACKPI_DIR

# Create Python virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install \
    flask \
    flask-sqlalchemy \
    flask-login \
    gunicorn \
    psycopg2-binary \
    python-socketio \
    eventlet \
    requests \
    psutil \
    python-nmap \
    netifaces \
    paramiko \
    werkzeug

# Create log directory
print_status "Creating log directories..."
sudo mkdir -p $LOG_DIR
sudo chown $CRACKPI_USER:$CRACKPI_USER $LOG_DIR

# Copy service file
print_status "Installing systemd service..."
sudo cp crackpi-server.service /etc/systemd/system/
sudo systemctl daemon-reload

# Configure firewall
print_status "Configuring firewall..."
sudo ufw allow 5000/tcp
sudo ufw allow 22/tcp
sudo ufw --force enable

# Configure nginx (optional reverse proxy)
print_status "Configuring nginx reverse proxy..."
sudo tee /etc/nginx/sites-available/crackpi > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/crackpi /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# Create database
print_status "Initializing database..."
export DATABASE_URL="sqlite:///$CRACKPI_DIR/crackpi.db"
python3 -c "from app import create_app; app = create_app()"

# Make scripts executable
chmod +x *.sh *.py

# Enable and start service
print_status "Enabling CrackPi server service..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Wait for service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    print_status "✅ CrackPi server installed and started successfully!"
    print_status "🌐 Web interface: http://$(hostname -I | cut -d' ' -f1)"
    print_status "🔑 Default login: admin / admin123"
else
    print_error "❌ Service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME"
fi

# Create stop/start scripts
cat > start_server.sh << 'EOF'
#!/bin/bash
sudo systemctl start crackpi-server
echo "CrackPi server started"
sudo systemctl status crackpi-server --no-pager
EOF

cat > stop_server.sh << 'EOF'
#!/bin/bash
sudo systemctl stop crackpi-server
echo "CrackPi server stopped"
EOF

chmod +x start_server.sh stop_server.sh

print_status "📋 Management commands:"
print_status "  Start:   ./start_server.sh"
print_status "  Stop:    ./stop_server.sh"
print_status "  Status:  sudo systemctl status crackpi-server"
print_status "  Logs:    sudo journalctl -u crackpi-server -f"

print_status "🎉 CrackPi Server setup complete!"