# CrackPi Configuration Guide

This guide explains how to set up and configure the CrackPi distributed password cracking system using Raspberry Pi devices.

## System Overview

CrackPi consists of:
- **Main Server**: One Raspberry Pi running the web interface and coordinating jobs
- **Client Nodes**: Multiple Raspberry Pis that perform the actual password cracking

## Prerequisites

### Hardware Requirements

**Main Server (Raspberry Pi):**
- Raspberry Pi 4 (4GB RAM recommended)
- 32GB+ microSD card (Class 10 or better)
- Ethernet connection (for stability)
- Optional: External storage for large wordlists

**Client Nodes (Raspberry Pi):**
- Raspberry Pi 3B+ or 4 (any RAM variant)
- 16GB+ microSD card (Class 10 or better)
- Ethernet connection (recommended) or WiFi

### Software Requirements

**Operating System:**
- Raspberry Pi OS (64-bit recommended)
- Python 3.8+
- Git

**Network:**
- All devices on the same network
- Internet access for initial setup

## Installation Steps

### 1. Prepare Raspberry Pi OS

1. **Flash Raspberry Pi OS** to microSD cards using Raspberry Pi Imager
2. **Enable SSH** by placing an empty file named `ssh` in the boot partition
3. **Configure WiFi** (if needed) by creating `wpa_supplicant.conf` in boot partition:
   ```
   country=US
   ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
   update_config=1
   
   network={
       ssid="Your_WiFi_Name"
       psk="Your_WiFi_Password"
   }
   ```

### 2. Initial Setup (All Devices)

1. **Boot and connect** to each Raspberry Pi
2. **Update the system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
3. **Clone CrackPi repository**:
   ```bash
   git clone https://github.com/your-repo/crackpi.git
   cd crackpi
   ```

### 3. Server Setup

On the main server Raspberry Pi:

1. **Run the server setup script**:
   ```bash
   chmod +x setup_server.sh
   ./setup_server.sh
   ```

2. **Follow the prompts** for:
   - Nginx configuration (recommended for production)
   - Firewall settings
   - Service configuration

3. **Access the web interface**:
   - Open browser to `http://[server-ip]:5000`
   - Default login: `admin` / `admin123`
   - **IMPORTANT**: Change the default password immediately

### 4. Client Setup

On each client Raspberry Pi:

1. **Copy CrackPi files** from server or clone repository
2. **Run the client setup script**:
   ```bash
   chmod +x setup_client.sh
   ./setup_client.sh [server-ip-address]
   ```
   
   Example:
   ```bash
   ./setup_client.sh 192.168.1.100
   ```

3. **Verify connection** by checking the server's web interface

## Configuration Files

### Server Configuration

**Location**: `/etc/crackpi/server.conf`

```ini
[server]
host = 0.0.0.0
port = 5000
debug = false
secret_key = your-generated-secret-key

[database]
url = sqlite:///var/lib/crackpi/crackpi.db

[paths]
upload_dir = /home/pi/crackpi/uploads
wordlists_dir = /usr/share/wordlists
rules_dir = /usr/share/hashcat/rules

[tools]
hashcat_path = /usr/bin/hashcat
john_path = /usr/bin/john

[network]
scan_interval = 300
client_timeout = 1800
