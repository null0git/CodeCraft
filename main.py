import os
from app import create_app

# Force SQLite by clearing PostgreSQL environment variables
pg_vars = ['DATABASE_URL', 'PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE']
for var in pg_vars:
    if var in os.environ:
        del os.environ[var]

# Set SQLite configuration
os.environ["DATABASE_URL"] = "sqlite:///crackpi.db"
os.environ["SESSION_SECRET"] = "dev-secret-key-change-in-production"

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
