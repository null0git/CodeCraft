#!/usr/bin/env python3
"""
Development startup script for CrackPi
Forces SQLite usage and starts the server
"""

import os
import sys

# Force SQLite usage and clear PostgreSQL environment variables
for pg_var in ['DATABASE_URL', 'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE']:
    if pg_var in os.environ:
        del os.environ[pg_var]

os.environ["DATABASE_URL"] = "sqlite:///crackpi.db"
os.environ["SESSION_SECRET"] = "dev-secret-key"

# Now import and run the app
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting CrackPi Development Server")
    print(f"📊 Database: {os.environ['DATABASE_URL']}")
    print(f"🌐 Server will be available at: http://localhost:5000")
    print(f"🔑 Default login: admin / admin123")
    
    app.run(host='0.0.0.0', port=5000, debug=True)