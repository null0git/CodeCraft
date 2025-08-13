import os
from app import create_app

# Set environment variable for SQLite if no DATABASE_URL
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///crackpi.db"

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
