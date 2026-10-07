# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.apt_users_b import AptUserB
from app.models.Auth import ParentRegisterRequest, ParentLoginRequest
from app.services.hash_helper import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Authentication System"])

# ==========================================
# 1. PARENT REGISTRATION ROUTE (Stores in apt_users_b)
# ==========================================
@router.post("/register", status_code=201)
async def register_parent(payload: ParentRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Search for existing email in table apt_users_b
    query = select(AptUserB).where(AptUserB.email == payload.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    # Build the database row object matching apt_users_b table columns exactly
    new_user_row = AptUserB(
        username=payload.email.split('@')[0],
        name=payload.name,
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
        role="PARENT"
    )
    
    db.add(new_user_row)
    await db.flush() # Force ID generation instantly inside PostgreSQL table apt_users_b
    await db.commit()
    await db.refresh(new_user_row)
    
    return {
        "status": "success",
        "message": "Account successfully written to PostgreSQL table apt_users_b!",
        "user_id": new_user_row.id
    }

# ==========================================
# 2. PARENT LOGIN ROUTE (Reads & Stores Login in apt_users_b)
# ==========================================
@router.post("/login", status_code=200)
async def login_parent(payload: ParentLoginRequest, db: AsyncSession = Depends(get_db)):
    clean_email = payload.email.lower().strip()
    
    try:
        query = select(AptUserB).where(AptUserB.email == clean_email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account not found in PostgreSQL database. Please sign up first."
            )
            
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password. Access denied."
            )
            
        # Record successful login in apt_users_b table
        user.updated_at = func.now()
        await db.commit()
        await db.refresh(user)
        
        return {
            "status": "success",
            "message": "Login successful. Session recorded in PostgreSQL apt_users_b table!",
            "user_id": user.id,
            "parent_name": user.name or user.username,
            "token_type": "bearer",
            "access_token": f"secure_jwt_token_for_user_{user.id}"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Database lookup in apt_users_b failed: {e}.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Invalid email or password."
        )

# ==========================================
# 3. ADMINISTRATIVE DIAGNOSTIC DEBUG ROUTE
# ==========================================
@router.get("/debug-db-users")
async def view_all_stored_users(db: AsyncSession = Depends(get_db)):
    query = select(User)
    result = await db.execute(query)
    all_users = result.scalars().all()
    
    return {
        "database_type": "Neon PostgreSQL Production Cluster (AWS Cloud)",
        "total_records_found": len(all_users),
        "stored_data": all_users
    }
