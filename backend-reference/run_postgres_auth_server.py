# ====================================================================
# Standalone PostgreSQL Backend Server Launcher
# Database Target: aepttas_xdr @ 100.112.49.39:5432  (schema: apt)
# Table: apt.apt_users_b
# Port: 8002
# ====================================================================

import os
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, text, select
from sqlalchemy.dialects.postgresql import UUID
import bcrypt
import uvicorn

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        pwd_bytes = password.encode('utf-8')[:72]
        return bcrypt.checkpw(pwd_bytes, hashed.encode('utf-8'))
    except Exception:
        return False

# 1. Database Connection URL
# DB_HOST=100.112.49.39  DB_PORT=5432  DB_NAME=aepttas_xdr  DB_SCHEMA=apt
# DB_USER=apt_auth_app   DB_PASSWORD=Auth@intern_aepttas
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://apt_auth_app:Auth%40intern_aepttas@100.112.49.39:5432/aepttas_xdr")

connect_args = {
    "server_settings": {"search_path": "apt"}
}

engine = create_async_engine(DATABASE_URL, connect_args=connect_args, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# 2. Table Definition — mapped to the REAL apt.apt_users_b schema
class AptUserB(Base):
    __tablename__ = "apt_users_b"
    __table_args__ = {"schema": "apt"}

    user_id          = Column(BigInteger, primary_key=True, autoincrement=True)
    user_uuid        = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    username         = Column(String(255), unique=True, nullable=False)
    email            = Column(String(255), unique=True, nullable=False)
    phone_number     = Column(String(50), nullable=True)
    password_hash    = Column(String(255), nullable=False)
    first_name       = Column(String(255), nullable=True)
    last_name        = Column(String(255), nullable=True)
    status_id        = Column(BigInteger, nullable=True, default=1)
    is_email_verified  = Column(Boolean, nullable=False, default=False)
    is_phone_verified  = Column(Boolean, nullable=False, default=False)
    last_login_date  = Column(DateTime, nullable=True)
    created_by       = Column(String(255), nullable=False, default="system")
    created_date     = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated_by  = Column(String(255), nullable=False, default="system")
    last_updated_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_dml_by      = Column(String(255), nullable=False, default="system")
    last_dml_date    = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_ddl_by      = Column(String(255), nullable=False, default="system")
    last_ddl_date    = Column(DateTime, nullable=False, default=datetime.utcnow)
    program_id       = Column(BigInteger, nullable=True)

# 3. FastAPI App Setup
app = FastAPI(title="Aepttas Security Authentication API - aepttas_xdr PostgreSQL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db():
    print("[PostgreSQL] Connecting to aepttas_xdr @ 100.112.49.39 (Tailscale) (schema: apt)...")
    # We do NOT call create_all here — the real table already exists in the DB
    # Just verify connectivity
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM apt.apt_users_b"))
        count = result.scalar()
        print(f"[PostgreSQL] Connected! apt.apt_users_b has {count} existing record(s).")
    print("[PostgreSQL] Auth Server listening on http://0.0.0.0:8002")

@app.post("/api/auth/register", status_code=201)
async def register(payload: dict):
    async with AsyncSessionLocal() as db:
        email = (payload.get("email") or payload.get("username") or "").lower().strip()
        name  = (payload.get("name") or payload.get("full_name") or payload.get("username") or email.split("@")[0]).strip()
        password = payload.get("password") or payload.get("password_hash") or "Password123"

        # Check if email already exists
        query = select(AptUserB).where(AptUserB.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            # Update password and login date if user exists
            user.password_hash = hash_password(password)
            user.last_login_date = datetime.utcnow()
            user.last_updated_date = datetime.utcnow()
            await db.commit()
            return {
                "status": "success",
                "message": "User account updated in PostgreSQL table apt.apt_users_b!",
                "user_id": user.user_id
            }

        parts = name.split(" ", 1)
        first_name = parts[0] if parts else name
        last_name  = parts[1] if len(parts) > 1 else ""
        hashed = hash_password(password)
        now = datetime.utcnow()

        new_user = AptUserB(
            username         = email.split("@")[0],
            email            = email,
            password_hash    = hashed,
            first_name       = first_name,
            last_name        = last_name,
            is_email_verified = True,
            is_phone_verified = False,
            status_id        = 1,
            created_by       = "app_register",
            created_date     = now,
            last_updated_by  = "app_register",
            last_updated_date = now,
            last_dml_by      = "app_register",
            last_dml_date    = now,
            last_ddl_by      = "app_register",
            last_ddl_date    = now,
            last_login_date  = now
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        print(f"[PostgreSQL SUCCESS] Stored user_id={new_user.user_id} email={email} in apt.apt_users_b!")
        return {
            "status": "success",
            "message": "Account successfully inserted into PostgreSQL table apt.apt_users_b!",
            "user_id": new_user.user_id
        }

@app.post("/api/auth/login", status_code=200)
async def login(payload: dict):
    async with AsyncSessionLocal() as db:
        email = (payload.get("email") or payload.get("username") or "").lower().strip()
        password = payload.get("password", "")
        name = (payload.get("name") or payload.get("user_name") or email.split("@")[0]).strip()

        if not email:
            raise HTTPException(status_code=400, detail="Email is required.")

        query = select(AptUserB).where(AptUserB.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        now = datetime.utcnow()

        if not user:
            # Auto-register user directly into apt.apt_users_b on login if not already registered
            parts = name.split(" ", 1)
            first_name = parts[0] if parts else name
            last_name = parts[1] if len(parts) > 1 else ""
            hashed = hash_password(password if password else "Password123")

            user = AptUserB(
                username=email.split("@")[0],
                email=email,
                password_hash=hashed,
                first_name=first_name,
                last_name=last_name,
                is_email_verified=True,
                is_phone_verified=False,
                status_id=1,
                created_by="app_login",
                created_date=now,
                last_updated_by="app_login",
                last_updated_date=now,
                last_dml_by="app_login",
                last_dml_date=now,
                last_ddl_by="app_login",
                last_ddl_date=now,
                last_login_date=now
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            print(f"[PostgreSQL SUCCESS] Auto-created & stored user_id={user.user_id} ({email}) in apt.apt_users_b on login!")
        else:
            # User exists - update last login timestamp and password hash if needed
            if password:
                user.password_hash = hash_password(password)
            user.last_login_date = now
            user.last_updated_date = now
            user.last_updated_by = "app_login"
            user.last_dml_date = now
            user.last_dml_by = "app_login"
            await db.commit()
            print(f"[PostgreSQL SUCCESS] Updated login timestamp for user_id={user.user_id} ({email}) in apt.apt_users_b!")

        display_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username
        return {
            "status": "success",
            "message": "Login recorded in PostgreSQL apt.apt_users_b!",
            "user_id": user.user_id,
            "parent_name": display_name,
            "token_type": "bearer",
            "access_token": f"auth_token_{user.user_id}_{int(now.timestamp())}"
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
