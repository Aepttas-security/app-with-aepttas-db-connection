# caller_backend/database.py
import os
import urllib.parse
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger("unified_backend.database")

Base = declarative_base()

# ============================================
# 🔐 DATABASE CONFIGURATION
# ============================================
TAILSCALE_IP = os.getenv("DB_HOST", "dpg-dail4sh5efls73dvr100-a.oregon-postgres.render.com")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aepttas_xdr")
DB_SCHEMA = os.getenv("DB_SCHEMA", "apt")
DB_USER = os.getenv("DB_USER", "apt_callmgmt_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Call@intern_aepttas")

encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
DEFAULT_DB_URL = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{TAILSCALE_IP}:{DB_PORT}/{DB_NAME}?sslmode=require"

raw_db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
if "aepttas_xdr_user" in raw_db_url or not raw_db_url:
    DATABASE_URL = DEFAULT_DB_URL
else:
    DATABASE_URL = raw_db_url

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

# Connect args with timeout and SSL settings for cloud database (Render / AWS)
connect_args = {
    "connect_timeout": 10,
    "sslmode": "require",
    "channel_binding": "disable",
    "options": f"-c search_path={DB_SCHEMA},public"
}

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
        pool_size=10,
        max_overflow=20,
        connect_args=connect_args
    )
except Exception as e:
    logger.warning(f"Initial engine setup warning: {e}")
    engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

import time

_db_status = None
_last_check = 0.0

def is_db_online() -> bool:
    """Cached connectivity check with 15s TTL to prevent cascading network timeouts"""
    global _db_status, _last_check
    now = time.time()
    if _db_status is not None and (now - _last_check) < 15:
        return _db_status
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_status = True
    except Exception:
        _db_status = False
    _last_check = now
    return _db_status

def check_db_connection() -> bool:
    return is_db_online()
