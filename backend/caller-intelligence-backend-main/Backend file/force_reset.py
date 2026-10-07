from sqlalchemy import create_engine # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base # type: ignore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# IMPORTANT: Change this to your actual PostgreSQL credentials


# For password with @ symbol, use %40 instead of @
# Example: "Database@123" becomes "Database%40123"
DATABASE_URL = "postgresql+psycopg2://neondb_owner:npg_y9gXCVS3Klzd@ep-nameless-queen-aqugbfe4-pooler.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

# If the above doesn't work, try with a simpler password first
# DATABASE_URL = "postgresql+psycopg2://postgres:your_password@localhost/call_management"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_db():
    """Initialize database with default settings"""
    try:
        Base.metadata.create_all(bind=engine)
        
        db = SessionLocal()
        try:
            from models import SettingsDB
            settings = db.query(SettingsDB).first()
            
            if not settings:
                default_settings = SettingsDB(
                    auto_block_calls=True,
                    notifications_enabled=True,
                    detection_sensitivity=70,
                    privacy_mode=False,
                    auto_block_threshold=80
                )
                db.add(default_settings)
                db.commit()
                logger.info("Default settings created")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

if __name__ == "__main__":
    init_db()