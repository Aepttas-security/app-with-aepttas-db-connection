# app/routers/screentime.py
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.db_models import User, ScreentimeSettingsTable
from app.models.Screentime import ScreenTimeDashboardResponse, LockOverrideRequest, SetDailyLimitRequest
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screentime", tags=["Screen Time Management"])

@router.get("/{child_id}/dashboard", response_model=ScreenTimeDashboardResponse)
async def get_screentime_dashboard(
    child_id: str, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Fetches real-time metric limits for dashboard."""
    parsed_id = await get_child_id(db, child_id)
    await verify_parent_ownership(db, parsed_id, current_parent.id)
        
    try:
        query = select(ScreentimeSettingsTable).where(ScreentimeSettingsTable.child_id == parsed_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        if not record:
            record = ScreentimeSettingsTable(
                child_id=parsed_id,
                daily_limit_minutes=240,
                current_usage_minutes=0,
                is_locked_remotely=False
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            
        return {
            "child_id": str(child_id),
            "daily_limit_minutes": record.daily_limit_minutes,
            "current_usage_minutes": record.current_usage_minutes,
            "is_locked_remotely": record.is_locked_remotely
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Screentime Dashboard DB Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed while fetching screen time metrics."
        )

@router.post("/{child_id}/remote-lock")
async def toggle_remote_device_lock(
    child_id: str, 
    payload: LockOverrideRequest, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Fired when parent toggles remote device lock."""
    parsed_id = await get_child_id(db, child_id)
    await verify_parent_ownership(db, parsed_id, current_parent.id)
        
    try:
        query = select(ScreentimeSettingsTable).where(ScreentimeSettingsTable.child_id == parsed_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            record.is_locked_remotely = payload.is_locked
        else:
            record = ScreentimeSettingsTable(
                child_id=parsed_id,
                daily_limit_minutes=240,
                current_usage_minutes=0,
                is_locked_remotely=payload.is_locked
            )
            db.add(record)
            
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Hardware override sent. Device status changed to {'LOCKED' if payload.is_locked else 'UNLOCKED'}.",
            "is_locked_remotely": payload.is_locked
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Screentime Lock DB Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during remote lock toggle."
        )

@router.put("/{child_id}/daily-limit")
async def update_daily_limit(
    child_id: str, 
    payload: SetDailyLimitRequest, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Updates screen time daily limit for a child."""
    parsed_id = await get_child_id(db, child_id)
    await verify_parent_ownership(db, parsed_id, current_parent.id)
        
    try:
        query = select(ScreentimeSettingsTable).where(ScreentimeSettingsTable.child_id == parsed_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        
        if record:
            record.daily_limit_minutes = payload.daily_limit_minutes
        else:
            record = ScreentimeSettingsTable(
                child_id=parsed_id,
                daily_limit_minutes=payload.daily_limit_minutes,
                current_usage_minutes=0,
                is_locked_remotely=False
            )
            db.add(record)
            
        await db.commit()
        
        return {
            "status": "success",
            "message": f"Daily limit updated to {payload.daily_limit_minutes} minutes.",
            "daily_limit_minutes": payload.daily_limit_minutes
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Screentime Limit Update DB Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed during daily limit update."
        )

