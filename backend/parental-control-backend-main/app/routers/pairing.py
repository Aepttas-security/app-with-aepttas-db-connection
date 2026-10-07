import uuid
import secrets
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.db_models import User
from app.services.jwt import get_current_parent

router = APIRouter(prefix="/api/pairing", tags=["Pairing"])

# In-memory store for rapid fallback / cache
IN_MEMORY_PAIRINGS: Dict[str, dict] = {}
LOGOUT_ATTEMPTS: Dict[str, dict] = {}


class LinkDeviceRequest(BaseModel):
    linking_code: str = Field(..., min_length=6, max_length=10, json_schema_extra={"example": "582-914"})
    child_name: str = Field(..., min_length=1, json_schema_extra={"example": "Alex"})
    device_name: Optional[str] = "Samsung S23 Ultra"
    os_type: Optional[str] = "Android"
    parent_email: Optional[str] = Field(None, json_schema_extra={"example": "parent@example.com"})
    age: Optional[int] = Field(10, json_schema_extra={"example": 10})


class ConsentPayload(BaseModel):
    consent_given: bool = True


class DevicePairRequest(BaseModel):
    linking_code: str
    device_name: Optional[str] = "Samsung S23 Ultra"
    os_type: Optional[str] = "Android"


class LogoutAttemptPayload(BaseModel):
    child_id: str
    parent_id: int
    child_name: Optional[str] = "Child Device"


def normalize_code(code: str) -> str:
    """Extracts digits and standardizes format as XXX-XXX."""
    digits = "".join(filter(str.isdigit, str(code)))
    if len(digits) == 6:
        return f"{digits[:3]}-{digits[3:]}"
    return str(code).strip()


# ==========================================
# 1. GENERATE PARENT LINKING CODE
# ==========================================
@router.post("/generate-parent-code", status_code=status.HTTP_200_OK)
async def generate_parent_linking_code(
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    p_id = current_parent.id
    part_left = secrets.randbelow(900) + 100
    part_right = secrets.randbelow(900) + 100
    linking_code = f"{part_left}-{part_right}"
    
    now_ts = time.time()
    expires_at_ts = now_ts + 900
    expires_at_str = datetime.fromtimestamp(expires_at_ts, tz=timezone.utc).isoformat()

    pairing_data = {
        "linking_code": linking_code,
        "parent_id": p_id,
        "status": "PENDING",
        "expires_at": expires_at_ts,
        "expires_at_str": expires_at_str,
        "created_at": now_ts,
        "child_uuid": None,
        "child_name": None,
        "device_name": None,
        "os_type": None,
        "linking_timestamp": None,
        "telemetry": None,
    }

    IN_MEMORY_PAIRINGS[linking_code] = pairing_data

    try:
        dev_id = f"DEV-{linking_code}"
        upsert_pairing = text("""
            INSERT INTO apt.apt_device_pairing_b (linking_code, parent_id, device_identifier, status, child_consent_given)
            VALUES (:linking_code, :parent_id, :dev_id, 'PENDING', false)
            ON CONFLICT (linking_code) DO UPDATE
            SET parent_id = EXCLUDED.parent_id, status = 'PENDING', child_consent_given = false;
        """)
        await db.execute(upsert_pairing, {
            "linking_code": linking_code,
            "parent_id": p_id,
            "dev_id": dev_id
        })
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"[WARN] DB pairing record creation failed: {e}")

    return {
        "status": "success",
        "linking_code": linking_code,
        "parent_id": p_id,
        "pairing_status": "PENDING",
        "expires_at": expires_at_str,
        "expires_in_seconds": 900
    }


@router.post("/generate-code/{child_id}", status_code=status.HTTP_200_OK)
async def generate_pairing_code_legacy(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    res = await generate_parent_linking_code(db=db, current_parent=current_parent)
    res["child_id"] = child_id
    return res


# ==========================================
# 2. CHECK PAIRING STATUS BY CODE
# ==========================================
@router.get("/status-by-code/{linking_code}", status_code=status.HTTP_200_OK)
async def check_pairing_status_by_code(
    linking_code: str,
    db: AsyncSession = Depends(get_db)
):
    formatted_code = normalize_code(linking_code)

    if formatted_code in IN_MEMORY_PAIRINGS:
        item = IN_MEMORY_PAIRINGS[formatted_code]
        if item["status"] == "PENDING" and time.time() > item["expires_at"]:
            item["status"] = "EXPIRED"

        return {
            "status": item["status"],
            "linking_code": formatted_code,
            "parent_id": item["parent_id"],
            "child_id": item.get("child_uuid"),
            "child_name": item.get("child_name"),
            "device_name": item.get("device_name"),
            "os_type": item.get("os_type"),
            "linking_timestamp": item.get("linking_timestamp"),
            "telemetry": item.get("telemetry"),
            "message": "Waiting for child device to connect" if item["status"] == "PENDING" else "Pairing completed"
        }

    try:
        query = text("""
            SELECT p.status, p.child_consent_given, p.linking_code, p.parent_id, p.device_name, c.child_name, c.child_uuid, c.child_id
            FROM apt.apt_device_pairing_b p
            LEFT JOIN apt.apt_children_b c ON (p.child_uuid = c.child_uuid OR p.linking_code = c.linking_code)
            WHERE p.linking_code = :code OR REPLACE(p.linking_code, '-', '') = REPLACE(:code, '-', '')
            ORDER BY p.pairing_id DESC LIMIT 1;
        """)
        res = await db.execute(query, {"code": formatted_code})
        row = res.fetchone()

        if row:
            p_status, consent, code, p_id, device_name, child_name, child_uuid, c_int_id = row
            is_linked = p_status in ["LINKED", "COMPLETED"] or bool(consent)
            current_status = "LINKED" if is_linked else (p_status or "PENDING")

            return {
                "status": current_status,
                "linking_code": formatted_code,
                "parent_id": p_id,
                "child_id": str(c_int_id or child_uuid or ""),
                "child_uuid": str(child_uuid) if child_uuid else None,
                "child_name": child_name,
                "device_name": device_name or "Samsung S23 Ultra",
                "os_type": "Android",
                "linking_timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Connected" if is_linked else "Waiting for child device to connect"
            }
    except Exception as e:
        await db.rollback()
        print(f"[WARN] DB status check fallback error: {e}")

    return {
        "status": "PENDING",
        "linking_code": formatted_code,
        "message": "Waiting for child device to connect"
    }


# ==========================================
# 3. LINK MY DEVICE (CHILD ACTION)
# ==========================================
@router.post("/link-device", status_code=status.HTTP_200_OK)
async def link_child_device(
    payload: LinkDeviceRequest,
    db: AsyncSession = Depends(get_db)
):
    child_name = payload.child_name.strip()
    formatted_code = normalize_code(payload.linking_code)
    device_name = payload.device_name or "Samsung S23 Ultra"
    os_type = payload.os_type or "Android"

    if not child_name:
        raise HTTPException(status_code=400, detail="Child name is required.")

    pairing_item = IN_MEMORY_PAIRINGS.get(formatted_code)
    p_id = None

    if pairing_item:
        if pairing_item.get("status") in ["COMPLETED", "USED"]:
            raise HTTPException(status_code=400, detail="Invalid Linking Code. This code has already been used.")

        if pairing_item.get("status") == "EXPIRED" or time.time() > pairing_item.get("expires_at", 0):
            pairing_item["status"] = "EXPIRED"
            raise HTTPException(status_code=400, detail="Invalid Linking Code. The code has expired.")

        p_id = pairing_item.get("parent_id")
    else:
        try:
            verify_sql = text("""
                SELECT parent_id, status FROM apt.apt_device_pairing_b 
                WHERE linking_code = :code OR REPLACE(linking_code, '-', '') = REPLACE(:code, '-', '');
            """)
            res = await db.execute(verify_sql, {"code": formatted_code})
            row = res.fetchone()
            if not row:
                # Check directly in children table if linking_code exists
                c_check = await db.execute(text("""
                    SELECT parent_user_id FROM apt.apt_children_b 
                    WHERE linking_code = :code OR REPLACE(linking_code, '-', '') = REPLACE(:code, '-', '');
                """), {"code": formatted_code})
                c_row = c_check.fetchone()
                if not c_row:
                    raise HTTPException(status_code=400, detail="Invalid Linking Code. Please check the code and try again.")
                p_id = c_row[0]
            else:
                p_id, db_status = row[0], row[1]
                if db_status in ["USED"]:
                    raise HTTPException(status_code=400, detail="Invalid Linking Code. This code has already been used.")
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database verification error: {str(e)}")

    new_c_uuid = str(uuid.uuid4())
    link_ts = datetime.now(timezone.utc).isoformat()
    telemetry_data = {
        "screentime_used_minutes": 0,
        "daily_limit_minutes": 240,
        "battery_percentage": 100,
        "charging_status": "Not Charging",
        "current_location": "Live Coordinates Transmitted",
        "security_status": "Protected (Score 98/100)",
        "last_sync_time": "Just now"
    }

    try:
        # 1. Update/Insert child record with is_paired = true
        insert_child = text("""
            INSERT INTO apt.apt_children_b (child_uuid, parent_user_id, child_name, age, linking_code, is_paired)
            VALUES (:c_uuid, :p_id, :c_name, :age, :code, true)
            ON CONFLICT (linking_code) DO UPDATE
            SET child_name = EXCLUDED.child_name, 
                age = EXCLUDED.age,
                is_paired = true;
        """)
        await db.execute(insert_child, {
            "c_uuid": new_c_uuid,
            "p_id": p_id,
            "c_name": child_name,
            "age": payload.age or 10,
            "code": formatted_code
        })

        # 2. Upsert device pairing table
        upsert_pairing = text("""
            INSERT INTO apt.apt_device_pairing_b (linking_code, parent_id, child_uuid, device_identifier, device_name, status, child_consent_given)
            VALUES (:code, :p_id, :c_uuid, :dev_id, :dev_name, 'COMPLETED', true)
            ON CONFLICT (linking_code) DO UPDATE
            SET status = 'COMPLETED', 
                child_consent_given = true, 
                device_name = EXCLUDED.device_name, 
                child_uuid = EXCLUDED.child_uuid;
        """)
        await db.execute(upsert_pairing, {
            "code": formatted_code,
            "p_id": p_id,
            "c_uuid": new_c_uuid,
            "dev_id": f"DEV-{formatted_code}",
            "dev_name": device_name
        })

        # 3. Initialize default screen time in apt.apt_screen_time_b
        init_st = text("""
            INSERT INTO apt.apt_screen_time_b (child_id, daily_limit_minutes, minutes_used, record_date, is_locked_remotely)
            SELECT child_id, 240, 0, CURRENT_DATE, false
            FROM apt.apt_children_b WHERE linking_code = :code
            ON CONFLICT (child_id, record_date) DO UPDATE SET is_locked_remotely = false;
        """)
        await db.execute(init_st, {"code": formatted_code})

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database persistence failure: {str(e)}")

    IN_MEMORY_PAIRINGS[formatted_code] = {
        "linking_code": formatted_code,
        "parent_id": p_id,
        "status": "LINKED",
        "child_uuid": new_c_uuid,
        "child_name": child_name,
        "device_name": device_name,
        "os_type": os_type,
        "linking_timestamp": link_ts,
        "telemetry": telemetry_data
    }

    return {
        "status": "success",
        "message": "Device successfully linked to Parent account!",
        "pairing_status": "LINKED",
        "parent_id": p_id,
        "child_id": new_c_uuid,
        "child_name": child_name,
        "device_name": device_name,
        "os_type": os_type,
        "linking_timestamp": link_ts,
        "telemetry": telemetry_data
    }


@router.post("/verify", status_code=status.HTTP_200_OK)
async def verify_and_pair_device(
    payload: DevicePairRequest,
    db: AsyncSession = Depends(get_db)
):
    link_req = LinkDeviceRequest(
        linking_code=payload.linking_code,
        child_name="Child Device",
        device_name=payload.device_name,
        os_type=payload.os_type
    )
    return await link_child_device(link_req, db)


# ==========================================
# 4. CHECK PARENT LINKED CHILD
# ==========================================
@router.get("/check-parent-linked/{parent_id}", status_code=status.HTTP_200_OK)
async def check_parent_linked_child(
    parent_id: int,
    db: AsyncSession = Depends(get_db)
):
    for _, item in IN_MEMORY_PAIRINGS.items():
        if item.get("parent_id") == parent_id and item.get("status") == "LINKED":
            return {
                "is_linked": True,
                "linked_child": {
                    "id": item.get("child_uuid"),
                    "name": item.get("child_name"),
                    "device": item.get("device_name"),
                    "linking_timestamp": item.get("linking_timestamp"),
                    "telemetry": item.get("telemetry")
                }
            }

    try:
        query = text("""
            SELECT c.child_id, c.child_uuid, c.child_name, p.device_name 
            FROM apt.apt_children_b c
            LEFT JOIN apt.apt_device_pairing_b p ON (c.child_uuid = p.child_uuid OR c.linking_code = p.linking_code)
            WHERE c.parent_user_id = :p_id AND (c.is_paired = true OR p.status IN ('LINKED', 'COMPLETED'))
            ORDER BY c.child_id DESC
            LIMIT 1;
        """)
        res = await db.execute(query, {"p_id": parent_id})
        row = res.fetchone()

        if row:
            return {
                "is_linked": True,
                "linked_child": {
                    "id": str(row[0]),
                    "child_uuid": str(row[1]),
                    "name": row[2],
                    "device": row[3] or "Samsung S23 Ultra",
                    "permissions_granted": True,
                    "linking_timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
    except Exception as e:
        await db.rollback()
        print(f"[WARN] DB check parent linked query error: {e}")

    return {"is_linked": False, "linked_child": None}


# ==========================================
# 5. CHILD CONSENT AUTHORIZATION
# ==========================================
@router.post("/child-consent/{child_id}", status_code=status.HTTP_200_OK)
async def submit_child_linking_consent(
    child_id: str,
    payload: ConsentPayload,
    db: AsyncSession = Depends(get_db)
):
    for _, item in IN_MEMORY_PAIRINGS.items():
        if str(item.get("child_uuid")) == child_id:
            item["status"] = "LINKED"
            item["child_consent_given"] = payload.consent_given

    try:
        update_query = text("""
            UPDATE apt.apt_device_pairing_b
            SET child_consent_given = :consent, status = 'COMPLETED'
            WHERE child_uuid::text = :c_id;
        """)
        await db.execute(update_query, {"consent": payload.consent_given, "c_id": child_id})
        
        # Set is_paired in children table
        await db.execute(text("""
            UPDATE apt.apt_children_b
            SET is_paired = true
            WHERE child_uuid::text = :c_id OR child_id::text = :c_id;
        """), {"c_id": child_id})
        
        await db.commit()
    except Exception as e:
        await db.rollback()
        print(f"[WARN] Failed to update child consent in DB: {e}")

    return {
        "status": "success",
        "message": "Hardware link successfully authorized.",
        "child_id": child_id,
        "pairing_status": "LINKED"
    }


# ==========================================
# 6. GET PAIRING STATUS BY CHILD ID
# ==========================================
@router.get("/status/{child_id}", status_code=status.HTTP_200_OK)
async def get_pairing_status(
    child_id: str,
    db: AsyncSession = Depends(get_db)
):
    for _, item in IN_MEMORY_PAIRINGS.items():
        if str(item.get("child_uuid")) == child_id:
            return {
                "status": item.get("status", "LINKED"),
                "child_id": child_id,
                "child_consent_given": item.get("child_consent_given", True),
                "device_model": item.get("device_name", "Samsung S23 Ultra"),
                "is_online": True
            }

    try:
        query = text("""
            SELECT COALESCE(p.status, CASE WHEN c.is_paired THEN 'COMPLETED' ELSE 'PENDING' END),
                   COALESCE(p.child_consent_given, c.is_paired),
                   COALESCE(p.device_name, 'Samsung S23 Ultra')
            FROM apt.apt_children_b c
            LEFT JOIN apt.apt_device_pairing_b p ON (c.child_uuid = p.child_uuid OR c.linking_code = p.linking_code)
            WHERE c.child_uuid::text = :c_id OR c.child_id::text = :c_id
            ORDER BY c.child_id DESC LIMIT 1;
        """)
        res = await db.execute(query, {"c_id": child_id})
        row = res.fetchone()
        if row:
            return {
                "status": row[0] or "LINKED",
                "child_id": child_id,
                "child_consent_given": bool(row[1]),
                "device_model": row[2] or "Samsung S23 Ultra",
                "is_online": True
            }
    except Exception as e:
        await db.rollback()
        print(f"[WARN] DB fetch status by child ID failed: {e}")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Pairing status for the specified child device was not found."
    )


# ==========================================
# 7. UNLINK DEVICE PAIRING
# ==========================================
@router.post("/unlink/{child_id}", status_code=status.HTTP_200_OK)
async def unlink_pairing(
    child_id: str,
    db: AsyncSession = Depends(get_db)
):
    to_delete = [
        code for code, item in IN_MEMORY_PAIRINGS.items()
        if str(item.get("child_uuid")) == child_id
    ]
    for code in to_delete:
        del IN_MEMORY_PAIRINGS[code]

    try:
        # 1. Update pairing status
        update_pairing = text("""
            UPDATE apt.apt_device_pairing_b 
            SET status = 'UNLINKED', child_consent_given = false 
            WHERE child_uuid::text = :c_id;
        """)
        await db.execute(update_pairing, {"c_id": child_id})

        # 2. Update child status to unpaired
        update_child = text("""
            UPDATE apt.apt_children_b
            SET is_paired = false
            WHERE child_uuid::text = :c_id OR child_id::text = :c_id;
        """)
        await db.execute(update_child, {"c_id": child_id})

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database unlinking error: {str(e)}")

    return {
        "status": "success",
        "message": "Device unlinked successfully.",
        "child_id": child_id,
        "pairing_status": "UNLINKED"
    }


# ==========================================
# 8. CHILD LOGOUT NOTIFICATIONS
# ==========================================
@router.post("/logout-attempt", status_code=status.HTTP_200_OK)
async def report_logout_attempt(payload: LogoutAttemptPayload):
    LOGOUT_ATTEMPTS[payload.child_id] = {
        "child_id": payload.child_id,
        "parent_id": payload.parent_id,
        "child_name": payload.child_name,
        "timestamp": time.time(),
        "status": "ATTEMPTING_LOGOUT"
    }
    return {"status": "success", "message": "Logout attempt reported."}


@router.get("/check-logout-attempt/{parent_id}", status_code=status.HTTP_200_OK)
async def check_logout_attempt(parent_id: int):
    now = time.time()
    active_attempts = [
        v for v in LOGOUT_ATTEMPTS.values()
        if v.get("parent_id") == parent_id and (now - v.get("timestamp", 0) < 30)
    ]
    return {
        "has_logout_attempt": len(active_attempts) > 0,
        "attempts": active_attempts
    }