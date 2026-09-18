import os
from datetime import timedelta

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

# When set, every route except the dashboard requires this password (see
# app.py's require_login before_request hook). Left unset, the app stays
# fully open -- matches its existing no-auth posture until this is
# deliberately turned on.
EDIT_PASSWORD = os.environ.get("EDIT_PASSWORD")

# Flask sessions expire on browser close by default -- fine on a laptop,
# but this is mostly used one-handed on a phone where "closing the
# browser" isn't really a thing, so keep the login sticky for a month.
PERMANENT_SESSION_LIFETIME = timedelta(days=30)
