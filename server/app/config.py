"""Central configuration (env-driven, safe local defaults)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # the server/ folder

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me-cardiolink")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))

# SQLite by default so the app runs with zero setup.
# Switch to PostgreSQL later by setting DATABASE_URL in the environment.
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'cardiolink.db'}"

# CORS: "*" (any origin) in dev, or a comma-separated list of origins.
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
