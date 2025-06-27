#!/bin/bash
"""
CrackPi Auto-Start Script
Automatically starts the CrackPi server and opens web browser on boot
"""

# Configuration
CRACKPI_DIR="/home/pi/crackpi"
LOG_DIR="/var/log/crackpi"
SERVER_PORT=5000
BROWSER_DELAY=10  # seconds to wait before opening browser

# Ensure log directory exists
sudo mkdir -p $LOG_DIR
sudo chown pi:pi $LOG_DIR

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_DIR/autostart.log
}

log_message "Starting CrackPi Auto-Start Script"

# Change to CrackPi directory
cd $CRACKPI_DIR || {
    log_message "ERROR: CrackPi directory not found at $CRACKPI_DIR"
    exit 1
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    log_message "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check dependencies
log_message "Checking Python dependencies..."
if ! python -c "import flask, flask_sqlalchemy, flask_login" 2>/dev/null; then
    log_message "Installing missing Python dependencies..."
    pip install flask flask-sqlalchemy flask-login psycopg2-binary gunicorn
fi

# Check for database
log_message "Checking database connection..."
if ! python -c "from app import db; db.create_all()" 2>/dev/null; then
    log_message "WARNING: Database connection failed. Using SQLite fallback."
    export DATABASE_URL="sqlite:///crackpi.db"
fi

# Start the CrackPi server
log_message "Starting CrackPi server on port $SERVER_PORT..."
python main.py &
SERVER_PID=$!

# Wait for server to start
log_message "Waiting for server to initialize..."
sleep $BROWSER_DELAY

# Check if server is running
if ! curl -s http://localhost:$SERVER_PORT > /dev/null; then
    log_message "ERROR: Server failed to start"
    exit 1
fi

log_message "CrackPi server started successfully (PID: $SERVER_PID)"

# Open web browser (if display available)
if [ -n "$DISPLAY" ]; then
    log_message "Opening web browser..."
    # Try different browsers
    if command -v chromium-browser &> /dev/null; then
        chromium-browser --kiosk --disable-features=Translate http://localhost:$SERVER_PORT &
    elif command -v firefox &> /dev/null; then
        firefox --kiosk http://localhost:$SERVER_PORT &
    elif command -v midori &> /dev/null; then
        midori -e Fullscreen -a http://localhost:$SERVER_PORT &
    else
        log_message "No suitable browser found"
    fi
else
    log_message "No display available. Server running in headless mode."
    log_message "Access web interface at: http://$(hostname -I | cut -d' ' -f1):$SERVER_PORT"
fi

# Create stop script
cat > stop_crackpi.sh << 'EOF'
#!/bin/bash
echo "Stopping CrackPi server..."
pkill -f "python main.py"
pkill -f "gunicorn"
echo "CrackPi server stopped."
EOF
chmod +x stop_crackpi.sh

log_message "CrackPi auto-start completed successfully"
log_message "Server accessible at: http://localhost:$SERVER_PORT"
log_message "Default login: admin / admin123"

# Keep script running to maintain server
wait $SERVER_PID