import os

# Falls back to a local SQLite file so the app runs with zero setup during
# development -- production always sets DATABASE_URL to the Render Postgres
# instance instead.
_default_db = "sqlite:///" + os.path.join(os.path.dirname(__file__), "dev.db")
SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_db)

# Render's managed Postgres hands out "postgres://" URLs, but SQLAlchemy's
# psycopg2 dialect requires "postgresql://".
if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
        "postgres://", "postgresql://", 1
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key")
