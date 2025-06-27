#!/bin/bash

# CrackPi Client Setup Script
# This script sets up a CrackPi client on a Raspberry Pi

set -e

echo "========================================="
echo "CrackPi Client Setup"
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

# Check if server URL is provided
if [ -z "$1" ]; then
    read -p "Enter the CrackPi server IP address or hostname: " SERVER_HOST
else
    SERVER_HOST="$1"
fi

# Validate server connectivity
print_status "Testing connection to server: $SERVER_HOST"
if ! ping -c 1 "$SERVER_HOST" > /dev/null 2>&1; then
    print_error "Cannot reach server at $SERVER_HOST. Please check the address and network connectivity."
    exit 1
fi

SERVER_URL="http://$SERVER_HOST:5000"
print_status "Server URL: $SERVER_URL"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRACKPI_DIR="$SCRIPT_DIR"

print_status "Starting CrackPi client setup..."
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
    hashcat \
    john \
    curl \
    htop \
    screen \
    tmux \
    git

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
    python-socketio \
    psutil \
    netifaces \
    requests

# Create necessary directories
print_status "Creating directories..."
sudo mkdir -p /var/log/crackpi
sudo mkdir -p /etc/crackpi

# Set permissions
sudo chown -R $USER:$USER /var/log/crackpi

# Generate unique client ID
CLIENT_ID=$(python3 -c "
import hashlib
import socket
import uuid
try:
    import netifaces
    gws = netifaces.gateways()
    interface = gws['default'][netifaces.AF_INET][1]
    mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
except:
    mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])
hostname = socket.gethostname()
unique_string = f'{hostname}-{mac}'
client_id = hashlib.md5(unique_string.encode()).hexdigest()[:16]
print(client_id)
")

print_status "Generated client ID: $CLIENT_ID"

# Create configuration file
print_status "Creating configuration file..."
sudo tee /etc/crackpi/client.conf > /dev/null << EOF
# CrackPi Client Configuration

[client]
client_id = $CLIENT_ID
server_url = $SERVER_URL

[tools]
hashcat_path = /usr/bin/hashcat
john_path = /usr/bin/john

[paths]
wordlists_dir = /usr/share/wordlists
rules_dir = /usr/share/hashcat/rules
temp_dir = /tmp

[metrics]
update_interval = 30
EOF

sudo chown root:root /etc/crackpi/client.conf
sudo chmod 644 /etc/crackpi/client.conf

# Copy systemd service file
print_status "Installing systemd service..."
sudo cp "$CRACKPI_DIR/crackpi-client.service" /etc/systemd/system/
sudo systemctl daemon-reload

# Create environment file for the service
sudo tee /etc/crackpi/client.env > /dev/null << EOF
CRACKPI_SERVER_URL=$SERVER_URL
CRACKPI_CLIENT_ID=$CLIENT_ID
CRACKPI_DIR=$CRACKPI_DIR
EOF

# Test connection to server
print_status "Testing connection to CrackPi server..."
cd "$CRACKPI_DIR"
source venv/bin/activate

python3 -c "
import requests
import sys
try:
    response = requests.get('$SERVER_URL', timeout=10)
    if response.status_code == 200:
        print('✓ Successfully connected to CrackPi server')
    else:
        print(f'✗ Server responded with status code: {response.status_code}')
        sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f'✗ Failed to connect to server: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    print_error "Failed to connect to CrackPi server. Please check the server address and ensure the server is running."
    exit 1
fi

# Configure firewall
print_status "Configuring firewall..."
sudo ufw allow ssh
sudo ufw allow out 5000/tcp
echo "y" | sudo ufw enable

# Enable and start services
print_status "Enabling and starting services..."
sudo systemctl enable crackpi-client
sudo systemctl start crackpi-client

# Get network information
IP_ADDRESS=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

# Installation complete
print_status "========================================="
print_status "CrackPi Client installation complete!"
print_status "========================================="
print_status ""
print_status "Client Information:"
print_status "  Hostname: $HOSTNAME"
print_status "  IP Address: $IP_ADDRESS"
print_status "  Client ID: $CLIENT_ID"
print_status "  Server URL: $SERVER_URL"
print_status ""
print_status "Service Management:"
print_status "  Start:   sudo systemctl start crackpi-client"
print_status "  Stop:    sudo systemctl stop crackpi-client"
print_status "  Restart: sudo systemctl restart crackpi-client"
print_status "  Status:  sudo systemctl status crackpi-client"
print_status "  Logs:    sudo journalctl -u crackpi-client -f"
print_status ""
print_status "Configuration:"
print_status "  Client config: /etc/crackpi/client.conf"
print_status "  Environment: /etc/crackpi/client.env"
print_status "  Logs: /var/log/crackpi/"
print_status ""

# Check service status
sleep 2
if sudo systemctl is-active --quiet crackpi-client; then
    print_status "✓ CrackPi client is running successfully!"
    print_status "✓ Client should now appear in the server's web interface"
else
    print_error "✗ CrackPi client failed to start. Check logs with: sudo journalctl -u crackpi-client"
fi

print_status ""
print_status "The client is now configured and should automatically:"
print_status "1. Connect to the CrackPi server"
print_status "2. Register itself and send system information"
print_status "3. Wait for cracking jobs to be assigned"
print_status "4. Report progress and results back to the server"
print_status ""
print_status "Check the server's web interface to verify the client appears in the client list."
print_status ""
print_warning "If the client doesn't appear, check the logs and ensure the server is accessible."
