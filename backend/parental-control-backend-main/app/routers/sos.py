# app/routers/sos.py
import logging
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.db_models import User, SOSAlertTable
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sos", tags=["SOS Emergency Alerts"])

class SOSAlertRequest(BaseModel):
    child_id: str
    latitude: float = Field(..., alias="current_latitude")
    longitude: float = Field(..., alias="current_longitude")
    current_address: str = Field(..., alias="emergency_message")

    class Config:
        populate_by_name = True

@router.post("/trigger", status_code=status.HTTP_201_CREATED)
async def trigger_panic_button(payload: SOSAlertRequest, db: AsyncSession = Depends(get_db)):
    """Device panic alert trigger. Logs panic alert to apt_sos_alerts_b."""
    cid = await get_child_id(db, payload.child_id)
    try:
        new_alert = SOSAlertTable(
            child_id=cid,
            latitude=payload.latitude,
            longitude=payload.longitude,
            current_address=payload.current_address
        )
        
        db.add(new_alert)
        await db.flush()
        generated_id = new_alert.id
        await db.commit()
        
        return {
            "status": "EMERGENCY_BROADCAST_ACTIVE",
            "message": "CRITICAL: SOS alert logged in database!",
            "alert_details": {
                "alert_id": generated_id,
                "child_id": str(payload.child_id),
                "location": payload.current_address,
                "coordinates": f"{payload.latitude}, {payload.longitude}"
            }
        }
    except Exception as db_sync_error:
        await db.rollback()
        logger.error(f"SOS Write Error: {str(db_sync_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database SOS trigger failed."
        )

@router.get("/active/{child_id}")
async def get_active_alerts(
    child_id: str, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Endpoint polled by Parent Dashboard to check for active panic alarms."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        query = select(SOSAlertTable).where(
            SOSAlertTable.child_id == cid,
            SOSAlertTable.is_resolved == False
        )
        result = await db.execute(query)
        active_alarms = result.scalars().all()
        return {
            "child_id": str(child_id),
            "is_panic_active": len(active_alarms) > 0,
            "active_alerts": active_alarms
        }
    except HTTPException:
        raise
    except Exception as read_error:
        await db.rollback()
        logger.error(f"SOS Active Fetch Error: {str(read_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database active SOS query failed."
        )

@router.get("/feed")
async def get_parent_sos_feed(
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Fetches critical incident history feed for children belonging to authenticated parent."""
    try:
        query = text("""
            SELECT s.sos_alert_id, s.child_id, s.latitude, s.longitude, s.current_address, s.triggered_date, s.is_resolved
            FROM apt_sos_alerts_b s
            JOIN apt_children_b c ON s.child_id = c.child_id
            WHERE c.parent_user_id = :parent_id
            ORDER BY s.sos_alert_id DESC;
        """)
        result = await db.execute(query, {"parent_id": current_parent.id})
        rows = result.fetchall()
        
        feed = []
        for r in rows:
            feed.append({
                "sos_alert_id": r[0],
                "child_id": r[1],
                "latitude": float(r[2]) if r[2] else 0.0,
                "longitude": float(r[3]) if r[3] else 0.0,
                "current_address": r[4],
                "timestamp": str(r[5]),
                "is_resolved": bool(r[6])
            })
        return feed
    except Exception as read_err:
        await db.rollback()
        logger.error(f"SOS Feed Read Error: {str(read_err)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database SOS feed query failed."
        )

class SOSPreferencesPayload(BaseModel):
    email_enabled: Optional[bool] = None
    parent_email: Optional[str] = None
    phone_enabled: Optional[bool] = None
    parent_phone: Optional[str] = None
    emergency_contacts: Optional[list] = Field(default=["911"])
    auto_dial: Optional[bool] = Field(default=False)
    sound_alarm: Optional[bool] = Field(default=True)
    notify_guardians: Optional[bool] = Field(default=True)

@router.put("/preferences/{child_id}")
@router.put("/preferences")
@router.put("/preferences/")
async def update_sos_preferences(
    child_id: Optional[str] = "1",
    payload: Optional[SOSPreferencesPayload] = None,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    cid = await get_child_id(db, child_id or "1")
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        contacts_str = json.dumps(payload.emergency_contacts if payload and payload.emergency_contacts else ["911"])
        
        upsert_sql = text("""
            INSERT INTO apt_sos_preferences_b (child_id, emergency_contacts, auto_dial, sound_alarm, notify_guardians)
            VALUES (:child_id, :contacts, :auto_dial, :sound_alarm, :notify_guardians);
        """)
        await db.execute(upsert_sql, {
            "child_id": cid,
            "contacts": contacts_str,
            "auto_dial": payload.auto_dial if payload else False,
            "sound_alarm": payload.sound_alarm if payload else True,
            "notify_guardians": payload.notify_guardians if payload else True,
        })
        await db.commit()
        return {
            "status": "success",
            "child_id": str(child_id or "1"),
            "message": "SOS preferences updated successfully in database."
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"SOS preferences update DB error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failure updating SOS preferences."
        )

@router.get("/preferences/{child_id}")
@router.get("/preferences")
@router.get("/preferences/")
async def get_sos_preferences(
    child_id: Optional[str] = "1",
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    cid = await get_child_id(db, child_id or "1")
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        query = text("SELECT emergency_contacts, auto_dial, sound_alarm, notify_guardians FROM apt_sos_preferences_b WHERE child_id = :child_id ORDER BY id DESC LIMIT 1;")
        res = await db.execute(query, {"child_id": cid})
        row = res.fetchone()
        if row:
            contacts = json.loads(row[0]) if row[0] else ["911"]
            return {
                "status": "success",
                "child_id": str(child_id or "1"),
                "preferences": {
                    "emergency_contacts": contacts,
                    "auto_dial": bool(row[1]),
                    "sound_alarm": bool(row[2]),
                    "notify_guardians": bool(row[3])
                }
            }
        return {
            "status": "success",
            "child_id": str(child_id or "1"),
            "preferences": {
                "emergency_contacts": ["911"],
                "auto_dial": False,
                "sound_alarm": True,
                "notify_guardians": True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fetching SOS preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error fetching SOS preferences."
        )


