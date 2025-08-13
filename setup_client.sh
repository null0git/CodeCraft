#!/bin/bash
"""
CrackPi Client Setup Script
Installs and configures CrackPi client to connect to server
"""

set -e  # Exit on any error

# Auto-detect user and configuration
CURRENT_USER=$(whoami)
CRACKPI_USER="${CURRENT_USER}"
CRACKPI_DIR="/home/${CURRENT_USER}/crackpi"
LOG_DIR="/var/log/crackpi"
SERVICE_NAME="crackpi-client"
SERVER_IP="${1:-localhost}"

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

echo "🔧 Setting up CrackPi Client..."

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

print_status "Starting CrackPi Client installation for server: $SERVER_IP"

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
    git \
    curl \
    nmap \
    htop

# Install password cracking tools
print_status "Installing password cracking tools..."
sudo apt install -y john hashcat || print_warning "Some cracking tools may not be available"

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
    requests \
    psutil \
    python-nmap \
    netifaces \
    paramiko

# Create log directory
print_status "Creating log directories..."
sudo mkdir -p $LOG_DIR
sudo chown $CRACKPI_USER:$CRACKPI_USER $LOG_DIR

# Update service file with server IP
print_status "Configuring client service for server: $SERVER_IP"
sed "s/localhost/$SERVER_IP/g" crackpi-client.service > /tmp/crackpi-client.service
sudo mv /tmp/crackpi-client.service /etc/systemd/system/
sudo systemctl daemon-reload

# Test connection to server
print_status "Testing connection to CrackPi server..."
if curl -s --connect-timeout 5 "http://$SERVER_IP:5000/api/ping" > /dev/null; then
    print_status "✅ Successfully connected to CrackPi server"
else
    print_warning "⚠️  Cannot connect to server. Client will retry automatically."
fi

# Make scripts executable
chmod +x *.sh *.py

# Enable and start service
print_status "Enabling CrackPi client service..."
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# Wait for service to start
sleep 5

# Check service status
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    print_status "✅ CrackPi client installed and started successfully!"
    print_status "🔗 Connected to server: http://$SERVER_IP:5000"
else
    print_error "❌ Service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME"
fi

# Create management scripts
cat > start_client.sh << EOF
#!/bin/bash
sudo systemctl start crackpi-client
echo "CrackPi client started"
sudo systemctl status crackpi-client --no-pager
EOF

cat > stop_client.sh << 'EOF'
#!/bin/bash
sudo systemctl stop crackpi-client
echo "CrackPi client stopped"
EOF

cat > reconnect_client.sh << EOF
#!/bin/bash
echo "Reconnecting to server: $SERVER_IP"
sudo systemctl restart crackpi-client
sleep 3
sudo systemctl status crackpi-client --no-pager
EOF

chmod +x start_client.sh stop_client.sh reconnect_client.sh

print_status "📋 Management commands:"
print_status "  Start:      ./start_client.sh"
print_status "  Stop:       ./stop_client.sh"
print_status "  Reconnect:  ./reconnect_client.sh"
print_status "  Status:     sudo systemctl status crackpi-client"
print_status "  Logs:       sudo journalctl -u crackpi-client -f"

print_status "🎉 CrackPi Client setup complete!"
print_status "📊 Client will appear in the server dashboard once connected."