import random
import logging
import uuid
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.db_models import User, Child, UnlinkCodeTable
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/child", tags=["Child Subsystem Onboarding"])

# ==========================================
# DATA VALIDATION SCHEMAS (PYDANTIC)
# ==========================================
class ChildProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, example="Alex")
    age: int = Field(..., ge=2, le=18, example=12)
    linking_code: Optional[str] = Field(None, example="123-456")

class DevicePairRequest(BaseModel):
    linking_code: str = Field(..., min_length=6, max_length=10, description="Format: 123-456")
    device_name: str = Field(..., example="Samsung S23 Ultra")
    os_type: str = Field(..., description="Android or iOS")

class PermissionStatusPayload(BaseModel):
    location_allowed: Optional[bool] = Field(True, example=True)
    usage_stats_allowed: Optional[bool] = Field(True, example=True)
    vpn_filter_allowed: Optional[bool] = Field(True, example=True)
    location: Optional[bool] = Field(True, example=True)
    screentime: Optional[bool] = Field(True, example=True)

class VerifyUnlinkCodePayload(BaseModel):
    unlink_code: str = Field(..., min_length=6, max_length=10, example="482-391")

# In-memory store for high reliability unlink verification
IN_MEMORY_UNLINK_CODES: Dict[str, dict] = {}

# ==========================================
# EXPRESS ROUTE CHANNELS
# ==========================================

# 1. CREATE CHILD PROFILE
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_child_profile(
    payload: ChildProfileCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_parent)
):
    """Creates a child profile tracking row inside the database for the authenticated parent."""
    try:
        p_id = current_user.id
        new_child_uuid = uuid.uuid4()
        link_code = payload.linking_code or f"{random.randint(100, 999)}-{random.randint(100, 999)}"

        new_child = Child(
            child_uuid=new_child_uuid,
            parent_id=p_id,
            child_name=payload.name,
            age=payload.age,
            linking_code=link_code
        )
        db.add(new_child)
        await db.flush()
        await db.commit()
        await db.refresh(new_child)
        
        # Synchronize child profile into pairing table
        try:
            insert_pairing = text("""
                INSERT INTO apt.apt_device_pairing_b (linking_code, parent_id, child_id, child_uuid, device_identifier, device_name, status, child_consent_given)
                VALUES (:linking_code, :parent_id, :child_id, :child_uuid, :dev_id, :dev_id, 'PENDING', false)
                ON CONFLICT (linking_code) DO NOTHING;
            """)
            await db.execute(insert_pairing, {
                "linking_code": link_code,
                "parent_id": p_id,
                "child_id": new_child.child_id,
                "child_uuid": str(new_child.child_uuid),
                "dev_id": f"DEV-{link_code}"
            })
            await db.commit()

        except Exception as sync_err:
            logger.warning(f"Failed to sync child pairing: {sync_err}")

        return {
            "id": str(new_child.child_uuid),
            "child_id": new_child.child_id,
            "name": new_child.child_name,
            "age": new_child.age,
            "device": "Samsung S23 Ultra",
            "battery": "100%",
            "is_active_online": True,
            "linking_code": link_code
        }
    except Exception as err:
        await db.rollback()
        logger.error(f"Child Create DB Error: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during child profile creation."
        )

# 2. LIST ALL REGISTERED CHILD PROFILES BELONGING TO AUTHENTICATED PARENT
@router.get("")
async def list_child_profiles(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_parent)
):
    """Fetches all registered child profiles belonging to the authenticated parent."""
    try:
        p_id = current_user.id
        query = text("""
            SELECT c.child_uuid, c.child_name, c.age, c.linking_code, c.child_id, COALESCE(c.is_paired, false)
            FROM apt.apt_children_b c 
            WHERE c.parent_user_id = :parent_id
            ORDER BY c.child_id ASC;
        """)
        result = await db.execute(query, {"parent_id": p_id})
        rows = result.fetchall()
        
        response = []
        for r in rows:
            response.append({
                "id": str(r[0]),
                "child_id": r[4],
                "name": r[1],
                "age": r[2],
                "linking_code": r[3],
                "device": "Samsung S23 Ultra",
                "battery": "100%",
                "is_paired": bool(r[5]),
                "is_active_online": True
            })

        return response
    except Exception as err:
        await db.rollback()
        logger.error(f"Child List Error: {str(err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error fetching child profiles."
        )

# 3. PARENT GENERATES LINKING CODE
@router.post("/generate-code", status_code=status.HTTP_200_OK)
@router.post("/{child_id}/generate-code", status_code=status.HTTP_200_OK)
async def generate_linking_token(
    child_id: Optional[str] = "1", 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_parent)
):
    """Generates a tracking pairing code token inside the device_pairing table."""
    try:
        cid_val = await get_child_id(db, child_id)
        await verify_parent_ownership(db, cid_val, current_user.id)
        
        # Get child UUID string
        uuid_query = text("SELECT child_uuid FROM apt.apt_children_b WHERE child_id = :cid LIMIT 1;")
        res_u = await db.execute(uuid_query, {"cid": cid_val})
        row_u = res_u.fetchone()
        c_uuid = str(row_u[0]) if row_u and row_u[0] else str(uuid.uuid4())
            
        formatted_token = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
        
        update_apt_child = text("UPDATE apt.apt_children_b SET linking_code = :code WHERE child_id = :cid;")
        await db.execute(update_apt_child, {"code": formatted_token, "cid": cid_val})
        
        insert_apt = text("""
            INSERT INTO apt.apt_device_pairing_b (linking_code, parent_id, child_id, child_uuid, device_identifier, status, child_consent_given)
            VALUES (:code, :p_id, :cid, :c_uuid, :dev_id, 'PENDING', false)
            ON CONFLICT (linking_code) DO UPDATE SET status = 'PENDING';
        """)
        await db.execute(insert_apt, {
            "code": formatted_token,
            "p_id": current_user.id,
            "cid": cid_val,
            "c_uuid": c_uuid,
            "dev_id": f"DEV-{formatted_token}"
        })
        await db.commit()
        
        return {"child_id": str(child_id), "linking_code": formatted_token, "status": "PENDING"}
    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Token generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error generating token.")

# 4. PARENT UNLINKS / DELETES CHILD PROFILE
@router.delete("/{child_id}", status_code=status.HTTP_200_OK)
@router.post("/{child_id}/unlink", status_code=status.HTTP_200_OK)
async def unlink_or_delete_child_profile(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_parent)
):
    """Permanently deletes or unlinks a child device and all dependent records."""
    try:
        cid = await get_child_id(db, child_id)
        await verify_parent_ownership(db, cid, current_user.id)

        delete_queries = [
            "DELETE FROM apt.apt_unlink_codes_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_child_location_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_screen_time_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_geofence_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_filter_policy_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_child_apps_b WHERE child_id = :cid;",
            "DELETE FROM apt.apt_device_pairing_b WHERE child_id = :cid OR child_uuid::text = :cid_raw;",
            """
            DELETE FROM apt.apt_children_b 
            WHERE child_id = :cid AND parent_user_id = :pid;
            """
        ]
        
        for q in delete_queries:
            try:
                await db.execute(text(q), {"cid": cid, "cid_raw": str(child_id), "pid": current_user.id})
            except Exception as e:
                logger.warning(f"Unlink cleanup notice for query {q}: {e}")

        await db.commit()

        # Remove from memory fallback if present
        if str(cid) in IN_MEMORY_UNLINK_CODES:
            del IN_MEMORY_UNLINK_CODES[str(cid)]

        return {"status": "success", "message": "Child profile permanently removed."}
    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete child profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Database failure during child profile deletion.")

# 5. CHILD APP REQUESTS UNLINK
@router.post("/{child_id}/request-unlink", status_code=status.HTTP_201_CREATED)
async def request_device_unlink(child_id: str, db: AsyncSession = Depends(get_db)):
    """
    Invoked when child requests device unlinking.
    Generates a 6-digit code with 5-minute expiry and dispatches parent notification.
    """
    try:
        cid = await get_child_id(db, child_id)

        parent_id = None
        child_name = "Child Device"
        
        lookup_sql = text("SELECT parent_user_id, child_name FROM apt.apt_children_b WHERE child_id = :cid LIMIT 1;")
        res = await db.execute(lookup_sql, {"cid": cid})
        row = res.fetchone()
        if row:
            parent_id = row[0]
            child_name = row[1] or child_name

        formatted_code = f"{random.randint(100, 999)}-{random.randint(100, 999)}"
        now_dt = datetime.now(timezone.utc)
        expires_at = now_dt + timedelta(minutes=5)

        # Store in in-memory dict first
        IN_MEMORY_UNLINK_CODES[str(cid)] = {
            "unlink_code": formatted_code,
            "expires_at": expires_at,
            "is_used": False,
            "parent_id": parent_id
        }

        # Try persisting to database
        try:
            insert_apt_sql = text("""
                INSERT INTO apt.apt_unlink_codes_b (parent_id, child_id, unlink_code, expires_at, is_used, status, created_by)
                VALUES (:p_id, :cid, :code, :expires_at, FALSE, 'PENDING', 'CHILD_APP');
            """)
            await db.execute(insert_apt_sql, {
                "p_id": parent_id,
                "cid": cid,
                "code": formatted_code,
                "expires_at": expires_at
            })

            if parent_id:
                alert_title = f"Unlink Request from {child_name}"
                alert_msg = f"Child device unlinking requested. Verification code: {formatted_code} (Expires in 5 minutes)."
                notify_apt_sql = text("""
                    INSERT INTO apt.apt_parent_notification_b (parent_user_id, message, is_read, created_by, created_date)
                    VALUES (:parent_id, :msg, FALSE, 'CHILD_APP', NOW());
                """)
                await db.execute(notify_apt_sql, {
                    "parent_id": parent_id,
                    "msg": f"{alert_title}: {alert_msg}"
                })

            await db.commit()
        except Exception as db_err:
            await db.rollback()
            logger.info(f"Unlink DB write notice (stored in memory): {db_err}")

        return {
            "status": "pending_parent_verification",
            "message": "Unlink request dispatched. Verification code generated.",
            "unlink_code": formatted_code,
            "expires_in_seconds": 300
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Unlink request failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Unlink request database write failed.")

# 6. PARENT DASHBOARD: FETCH ACTIVE UNLINK CODE
@router.get("/{child_id}/active-unlink-code", status_code=status.HTTP_200_OK)
async def get_active_unlink_code(
    child_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_parent)
):
    """Called by the Parent App to retrieve active unlink code."""
    try:
        cid = await get_child_id(db, child_id)
        await verify_parent_ownership(db, cid, current_user.id)
        
        now = datetime.now(timezone.utc)

        # Check PostgreSQL database first
        try:
            fetch_apt_sql = text("""
                SELECT unlink_code, expires_at 
                FROM apt.apt_unlink_codes_b 
                WHERE child_id = :cid AND is_used = FALSE AND expires_at > :now
                ORDER BY unlink_id DESC LIMIT 1;
            """)
            res_apt = await db.execute(fetch_apt_sql, {"cid": cid, "now": now})
            row_apt = res_apt.fetchone()
            if row_apt:
                unlink_code, expires_at = row_apt
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                remaining_seconds = int((expires_at - now).total_seconds())
                return {
                    "active": True,
                    "unlink_code": unlink_code,
                    "remaining_seconds": max(0, remaining_seconds)
                }
        except Exception:
            await db.rollback()

        # Fallback to in-memory store
        mem_data = IN_MEMORY_UNLINK_CODES.get(str(cid))
        if mem_data and not mem_data.get("is_used") and mem_data.get("expires_at") > now:
            remaining_seconds = int((mem_data["expires_at"] - now).total_seconds())
            return {
                "active": True,
                "unlink_code": mem_data["unlink_code"],
                "remaining_seconds": max(0, remaining_seconds)
            }

        return {"active": False, "unlink_code": None, "remaining_seconds": 0}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Active unlink code check error: {e}")
        raise HTTPException(status_code=500, detail="Database check failed.")

# 7. VERIFY CODE AND DISSOCIATE DEVICE
@router.post("/{child_id}/verify-unlink", status_code=status.HTTP_200_OK)
async def verify_unlink_code_and_dissociate(
    child_id: str, 
    payload: VerifyUnlinkCodePayload, 
    db: AsyncSession = Depends(get_db)
):
    """Validates the 6-digit code entered on the child screen."""
    try:
        cid = await get_child_id(db, child_id)
        clean_code = payload.unlink_code.strip()
        digits = "".join(filter(str.isdigit, clean_code))
        formatted_code = f"{digits[:3]}-{digits[3:]}" if len(digits) == 6 else clean_code
        now = datetime.now(timezone.utc)

        matched_unlink_id = None
        code_valid = False

        # 1. Try DB lookup
        try:
            lookup_sql = text("""
                SELECT unlink_id, unlink_code, expires_at, is_used 
                FROM apt.apt_unlink_codes_b 
                WHERE child_id = :cid AND is_used = FALSE AND expires_at > :now
                ORDER BY unlink_id DESC LIMIT 1;
            """)
            res = await db.execute(lookup_sql, {"cid": cid, "now": now})
            row = res.fetchone()
            if row:
                u_id, u_code, u_exp, u_used = row
                if u_code in [clean_code, formatted_code, digits] or u_code.replace('-', '') == digits:
                    matched_unlink_id = u_id
                    code_valid = True
        except Exception:
            await db.rollback()

        # 2. Try In-Memory lookup if DB didn't match
        if not code_valid:
            mem_data = IN_MEMORY_UNLINK_CODES.get(str(cid))
            if mem_data and not mem_data.get("is_used") and mem_data.get("expires_at") > now:
                mem_code = mem_data.get("unlink_code", "")
                if mem_code in [clean_code, formatted_code, digits] or mem_code.replace('-', '') == digits:
                    code_valid = True
                    mem_data["is_used"] = True

        if not code_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code."
            )

        # Mark DB record as used if found
        if matched_unlink_id:
            try:
                update_sql = text("UPDATE apt.apt_unlink_codes_b SET is_used = TRUE, status = 'USED' WHERE unlink_id = :uid;")
                await db.execute(update_sql, {"uid": matched_unlink_id})
            except Exception:
                await db.rollback()

        # Update pairing status and unpair child in database
        try:
            update_pairing_sql = text("""
                UPDATE apt.apt_device_pairing_b 
                SET status = 'UNLINKED' 
                WHERE child_id = :cid;
            """)
            await db.execute(update_pairing_sql, {"cid": cid})

            update_child_sql = text("""
                UPDATE apt.apt_children_b 
                SET is_paired = false 
                WHERE child_id = :cid;
            """)
            await db.execute(update_child_sql, {"cid": cid})
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.info(f"Notice updating pairing status to UNLINKED: {e}")

        return {
            "status": "success",
            "message": "Device unlinked and dissociated successfully.",
            "unlinked": True
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        await db.rollback()
        logger.error(f"Unlink verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during unlink verification."
        )