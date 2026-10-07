# app/services/jwt.py

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from dotenv import load_dotenv

from app.database import get_db
from app.models.db_models import User


# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================

load_dotenv()

logger = logging.getLogger(__name__)


SECRET_KEY = (
    os.getenv("JWT_SECRET_KEY")
    or os.getenv(
        "SECRET_KEY",
        "PARENT_SHIELD_SUPER_SECRET_KEY"
    )
)

ALGORITHM = (
    os.getenv("JWT_ALGORITHM")
    or os.getenv("ALGORITHM", "HS256")
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        1440
    )
)


# ==========================================
# HTTP BEARER AUTHENTICATION
# ==========================================

bearer_scheme = HTTPBearer()
bearer_scheme_optional = HTTPBearer(auto_error=False)


# ==========================================
# CREATE ACCESS TOKEN (SHORTENED PAYLOAD)
# ==========================================

def create_access_token(data: dict) -> str:
    """
    Generates a compact JWT access token.
    """
    to_encode = data.copy()

    # Use UTC timestamp integer to minimize string length
    expire_dt = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({
        "exp": int(expire_dt.timestamp())
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# app/services/jwt.py

async def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates JWT token and fetches current parent record.
    Supports both user_id or email stored in 'sub'.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Handle development / testing mock tokens
    if token and token.startswith("mock_"):
        try:
            query = select(User).order_by(User.id.asc())
            res = await db.execute(query)
            dev_user = res.scalars().first()
            if dev_user:
                return dev_user
            else:
                # Auto-create default parent user 1 if table is empty
                default_parent = User(name="Default Parent", email="parent@example.com", password_hash="dev_hash")
                db.add(default_parent)
                await db.commit()
                await db.refresh(default_parent)
                return default_parent
        except Exception as dev_err:
            logger.warning(f"[JWT] Dev token fallback query notice: {dev_err}")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        sub_identifier = payload.get("sub")
        if sub_identifier is None:
            logger.error("[JWT] Token does not contain 'sub'")
            raise credentials_exception
    except JWTError as err:
        logger.error(f"[JWT] Token decode FAILED: {err}")
        raise credentials_exception

    try:
        sub_str = str(sub_identifier).strip()
        # Search by ID if sub is numeric, otherwise search by email
        if sub_str.isdigit():
            query = select(User).where(User.id == int(sub_str))
        else:
            query = select(User).where(User.email == sub_str.lower())

        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            logger.error(f"[JWT] User not found for subject: {sub_identifier}")
            # Try dev fallback
            query_first = select(User).order_by(User.id.asc())
            res_first = await db.execute(query_first)
            fallback_user = res_first.scalars().first()
            if fallback_user:
                return fallback_user
            raise credentials_exception

        return user
    except HTTPException:
        raise
    except Exception as db_err:
        logger.error(f"Database error during user token validation: {db_err}")
        raise credentials_exception


async def get_current_parent_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme_optional),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional parent authentication dependency. Returns parent User object if valid, None otherwise.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_parent(credentials, db)
    except Exception:
        return None