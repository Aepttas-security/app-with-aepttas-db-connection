# database.py - Fixed: Using psycopg2 (synchronous) instead of asyncpg
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib.parse

# ✅ Define Base
Base = declarative_base()


# ============================================
# 🔐 DATABASE CREDENTIALS
# ============================================

TAILSCALE_IP = os.getenv("DB_HOST", "100.112.49.39")
DB_HOST = TAILSCALE_IP
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aepttas_xdr")
DB_SCHEMA = os.getenv("DB_SCHEMA", "apt")
DB_USER = os.getenv("DB_USER", "apt_callmgmt_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Call@intern_aepttas")

# ============================================
# 🔗 URL-ENCODE PASSWORD
# ============================================
encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
ssl_option = "require" if "render.com" in DB_HOST or "neon.tech" in DB_HOST else "prefer"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={ssl_option}"
)

print(f"Connecting to: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ============================================
# 🏗️ ENGINE & SESSION
# ============================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    pool_size=10,
    max_overflow=20,
    connect_args={
        'connect_timeout': 5,
        'sslmode': ssl_option,
        'channel_binding': 'disable',
        'options': f'-c search_path={DB_SCHEMA},public'
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================
# 🔧 DATABASE FUNCTIONS
# ============================================

def get_db():
    """Get database session - used by FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database - creates all tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def drop_db():
    """Drop all tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("⚠️ All tables dropped")

# ============================================
# 🧪 TEST CONNECTION
# ============================================

if __name__ == "__main__":
    from sqlalchemy import text

    print("="*60)
    print("🔍 Testing Database Connection")
    print("="*60)
    print(f"📡 Host: {TAILSCALE_IP} (dinesh's machine)")
    print(f"📊 Database: {DB_NAME}")
    print(f"👤 User: {DB_USER}")
    print(f"📁 Schema: {DB_SCHEMA}")
    print("-"*60)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connected successfully!")
            print(f"✅ Test result: {result.scalar()}")

            schema_check = conn.execute(
                text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"),
                {"schema": DB_SCHEMA}
            ).first()

            if schema_check:
                print(f"✅ Schema '{DB_SCHEMA}' exists")
            else:
                print(f"⚠️ Schema '{DB_SCHEMA}' does not exist.")

            tables = conn.execute(
                text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                """),
                {"schema": DB_SCHEMA}
            ).fetchall()

            if tables:
                print(f"✅ Found {len(tables)} tables in schema '{DB_SCHEMA}':")
                for table in tables:
                    print(f"   - {table[0]}")
            else:
                print(f"ℹ️ No tables found in schema '{DB_SCHEMA}'.")

            print("-"*60)
            print("✅ Connection test completed successfully!")

    except Exception as e:
        print(f"❌ Database connection failed!")
        print(f"❌ Error: {e}")