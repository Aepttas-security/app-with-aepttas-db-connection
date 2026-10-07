# app/routers/auth.py
import asyncio
import logging
from datetime import datetime, timezone
import uuid
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.db_models import User, Child, UnlinkCodeTable
from app.models.Auth import ParentRegisterRequest, ParentLoginRequest, LoginResponse
from app.services.auth import hash_password, verify_password
from app.services.jwt import create_access_token, get_current_parent, get_current_parent_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication System"])

# ==========================================
# 1. PARENT REGISTRATION ROUTE
# ==========================================
@router.post("/register", status_code=201)
async def register_parent(payload: ParentRegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        clean_email = payload.email.strip().lower()
        clean_name = payload.name.strip()
        
        # Search for existing email or username in database table
        query = select(User).where((User.email == clean_email) | (User.name == clean_name))
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            if existing_user.email == clean_email:
                raise HTTPException(status_code=400, detail="Email is already registered.")
            else:
                raise HTTPException(status_code=400, detail="Username is already taken. Please choose another username.")
        
        # Hash password securely before database write
        hashed_pwd = await asyncio.to_thread(hash_password, payload.password)

        new_user_row = User(
            name=clean_name,
            email=clean_email,
            password_hash=hashed_pwd
        )
        
        db.add(new_user_row)
        await db.flush()
        await db.commit()
        await db.refresh(new_user_row)
        
        return {
            "status": "success",
            "message": "Account successfully registered!",
            "user_id": new_user_row.id
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Registration DB error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during user registration."
        )

# ==========================================
# 2. PARENT / CHILD LOGIN ROUTE
# ==========================================
@router.post("/login", response_model=LoginResponse)
async def login_parent_or_child(payload: ParentLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Look up the matching user profile by email or username
        identifier = payload.email.strip().lower()
        query = select(User).where((User.email == identifier) | (User.name == identifier))
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        is_pwd_valid = False
        if user:
            is_pwd_valid = await asyncio.to_thread(verify_password, payload.password, user.password_hash)

        if not user or not is_pwd_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credential combination passed to security gateway."
            )

        # Issue compact signed JWT token using stringified user.id
        token_str = create_access_token(data={"sub": str(user.id)})

        return {
            "status": "success",
            "access_token": token_str,
            "token_type": "bearer",
            "user_id": user.id,
            "user_name": user.name,
            "assigned_role": "PARENT"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during authentication."
        )

# ACCOUNT REGISTRATION INPUT VALIDATOR FOR CHILD PROFILES
class ChildRegisterPayload(BaseModel):
    username: str = Field(..., min_length=2, max_length=100, example="Rohan Sharma")
    email: EmailStr = Field(..., example="rohan@safeguard.com")
    password: str = Field(..., min_length=6, example="mySuperSecretPassword123")

# POST: REGISTER NEW CHILD IDENTITY NODE
@router.post("/child/register", status_code=status.HTTP_201_CREATED)
async def register_new_child_profile(
    payload: ChildRegisterPayload,
    current_parent: User = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates form data fields and provisions a profile within apt_children_b.
    """
    try:
        email_check_sql = text("SELECT child_uuid FROM apt_children_b WHERE linking_code = :email;")
        existing_user = await db.execute(email_check_sql, {"email": payload.email.lower().strip()})
        
        if existing_user.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="This email/linking code is already registered to an active device profile."
            )

        new_child = Child(
            parent_id=current_parent.id,
            child_name=payload.username.strip(),
            age=10,
            linking_code=payload.email.lower().strip()[:10]
        )
        db.add(new_child)
        await db.commit()
        await db.refresh(new_child)

        return {
            "status": "success",
            "message": "Child application profile initialized and secured successfully.",
            "account_details": {
                "child_id": str(new_child.child_id),
                "username": payload.username,
                "email": payload.email
            }
        }

    except HTTPException as http_err:
        raise http_err
    except Exception as db_error:
        await db.rollback()
        logger.error(f"Child registration DB error: {str(db_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during credential provisioning."
        )

# PARENT VERIFICATION PIN VALIDATION ROUTE
class VerifyParentPinPayload(BaseModel):
    pin: str = Field(..., min_length=1, max_length=20, example="1234")
    parent_id: Optional[int] = None
    child_id: Optional[Union[str, int]] = None

@router.post("/verify-parent-pin", status_code=status.HTTP_200_OK)
async def verify_parent_pin(
    payload: VerifyParentPinPayload,
    current_parent: Optional[User] = Depends(get_current_parent_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Validates parent verification code against active records in apt_unlink_codes_b,
    in-memory store, or master PIN fallback.
    """
    clean_pin = payload.pin.strip()
    digits = "".join(filter(str.isdigit, clean_pin))
    formatted_code = f"{digits[:3]}-{digits[3:]}" if len(digits) == 6 else clean_pin
    now_dt = datetime.now(timezone.utc)
    now_naive = now_dt.replace(tzinfo=None)

    # 1. Master PIN check (for admin / developer / emergency parent pin validation)
    MASTER_PINS = {"1234", "582914", "582-914", "9999", "0000"}
    if clean_pin in MASTER_PINS or digits in MASTER_PINS or formatted_code in MASTER_PINS:
        return {
            "status": "success",
            "message": "Parent Verification Code validated successfully.",
            "verified": True
        }

    p_id = current_parent.id if current_parent else payload.parent_id

    # 2. Database Lookup in apt_unlink_codes_b
    try:
        if p_id:
            sql_lookup = text("""
                SELECT unlink_id, unlink_code, expires_at, is_used 
                FROM apt_unlink_codes_b 
                WHERE parent_id = :pid AND is_used = FALSE AND expires_at > :now
                ORDER BY unlink_id DESC LIMIT 10;
            """)
            res = await db.execute(sql_lookup, {"pid": p_id, "now": now_naive})
        else:
            sql_lookup = text("""
                SELECT unlink_id, unlink_code, expires_at, is_used 
                FROM apt_unlink_codes_b 
                WHERE is_used = FALSE AND expires_at > :now
                ORDER BY unlink_id DESC LIMIT 10;
            """)
            res = await db.execute(sql_lookup, {"now": now_naive})

        rows = res.fetchall()
        for row in rows:
            u_id, u_code, u_exp, u_used = row
            db_code = str(u_code).strip()
            db_digits = "".join(filter(str.isdigit, db_code))
            if db_code in [clean_pin, formatted_code, digits] or (digits and db_digits == digits):
                update_sql = text("UPDATE apt_unlink_codes_b SET is_used = TRUE, status = 'USED' WHERE unlink_id = :uid;")
                await db.execute(update_sql, {"uid": u_id})
                await db.commit()
                return {
                    "status": "success",
                    "message": "Parent Verification Code validated successfully.",
                    "verified": True
                }
    except Exception as e:
        await db.rollback()
        logger.debug(f"Notice during DB unlink code query: {e}")

    # 3. In-Memory Lookup Fallback
    try:
        from app.routers.child import IN_MEMORY_UNLINK_CODES
        for cid, mem_data in IN_MEMORY_UNLINK_CODES.items():
            exp = mem_data.get("expires_at")
            is_valid_exp = (exp > now_naive) if (exp and exp.tzinfo is None) else (exp > now_dt if exp else False)
            if not mem_data.get("is_used") and is_valid_exp:
                mem_code = mem_data.get("unlink_code", "").strip()
                mem_digits = "".join(filter(str.isdigit, mem_code))
                if mem_code in [clean_pin, formatted_code, digits] or (digits and mem_digits == digits):
                    mem_data["is_used"] = True
                    return {
                        "status": "success",
                        "message": "Parent Verification Code validated successfully.",
                        "verified": True
                    }
    except Exception as mem_err:
        logger.error(f"Error in in-memory unlink code check: {mem_err}")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification code."
    )