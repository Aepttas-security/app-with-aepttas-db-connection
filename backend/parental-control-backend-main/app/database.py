import os
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from app.config import settings

# Load environment variables from .env file
load_dotenv()

# 1. Load DATABASE_URL from environment variable
raw_db_url = os.getenv(
    "DATABASE_URL",
    settings.DATABASE_URL
)

# Safely handle unescaped '@' symbol in password
if "Par@intern_aepttas" in raw_db_url:
    raw_db_url = raw_db_url.replace("Par@intern_aepttas", "Par%40intern_aepttas")

DATABASE_URL = raw_db_url

# 2. Establish PostgreSQL connection arguments (adjusted for network latency)
connect_args = {
    "timeout": 3.0,          # 3s connection establishment timeout
    "command_timeout": 5.0,  # 5s individual query execution timeout
}

if "neon.tech" in DATABASE_URL or "render.com" in DATABASE_URL:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

# Default search path to 'apt, public' so tables in the apt schema resolve automatically
db_schema = os.getenv("DB_SCHEMA", "apt, public")
connect_args["server_settings"] = {"search_path": db_schema}

# 3. Create the Asynchronous PostgreSQL Engine with high-capacity pooling
engine = create_async_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,       # Health-checks connections before reusing them
    pool_size=10,             # Base connection pool size
    max_overflow=20,          # Max burst connections during rapid polling
    pool_timeout=15.0,        # Max seconds to wait for an available connection
    pool_recycle=300          # Reconnect every 5 minutes to prevent stale VPN sockets
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()