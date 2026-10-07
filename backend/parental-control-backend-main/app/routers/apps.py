# app/routers/apps.py
import logging
import datetime
from typing import List, Optional
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.future import select

from app.database import get_db
from app.models.db_models import User
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["Application Access Control"])


# ==========================================
# 📋 PYDANTIC SCHEMAS (DATA VALIDATION)
# ==========================================
class AppToggleRequest(BaseModel):
    is_blocked: bool


class AppItem(BaseModel):
    package_name: str = Field(..., example="com.roblox.client")
    app_name: str = Field(..., example="Roblox")
    category: str = Field(default="Gaming", example="Gaming")


class SyncAppsPayload(BaseModel):
    apps: List[AppItem]


class ToggleBlockPayload(BaseModel):
    package_name: Optional[str] = None
    app_id: Optional[str] = None
    is_blocked: bool = Field(..., example=True)

    @property
    def target_package(self) -> str:
        return self.package_name or self.app_id or "unknown.package"


class SetAppLimitPayload(BaseModel):
    package_name: str = Field(..., example="com.instagram.android")
    daily_limit_minutes: int = Field(..., ge=0, example=30)


class UsageItem(BaseModel):
    package_name: str = Field(..., example="com.instagram.android")
    minutes_used: int = Field(..., ge=0, example=45)


class SubmitUsagePayload(BaseModel):
    usage_data: List[UsageItem]


class NewInstallPayload(BaseModel):
    package_name: str = Field(..., example="com.tiktok.android")
    app_name: str = Field(..., example="TikTok")
    category: str = Field(default="Entertainment", example="Entertainment")


class TrackTimePayload(BaseModel):
    package_name: str = Field(..., example="com.instagram.android")
    minutes_to_increment: int = Field(default=1, example=1)


class UninstallAppPayload(BaseModel):
    package_name: str = Field(..., example="com.instagram.android")
    app_name: str = Field(..., example="Instagram")


# ==========================================
# 📱 1. GET INSTALLED APPLICATIONS (FOR PARENT UI)
# ==========================================
@router.get("/{child_id}", status_code=status.HTTP_200_OK)
async def list_installed_applications(
    child_id: str, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Fetches the actual list of installed applications for a child device from apt.apt_child_apps_b."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    try:
        query = text("""
            SELECT 
                child_app_id, 
                package_name, 
                app_name, 
                is_blocked, 
                category, 
                daily_limit_minutes, 
                is_always_allowed,
                minutes_used_today
            FROM apt.apt_child_apps_b
            WHERE child_id = :child_id
            ORDER BY app_name ASC;
        """)
        result = await db.execute(query, {"child_id": cid})
        rows = result.fetchall()

        app_list = []
        for r in rows:
            app_list.append({
                "app_id": r[0],
                "package_name": r[1] or f"com.app.{r[0]}",
                "app_name": r[2] or f"Application {r[0]}",
                "is_blocked": bool(r[3]),
                "category": r[4] or "General",
                "daily_limit_minutes": r[5] if r[5] is not None else -1,
                "is_always_allowed": bool(r[6]),
                "minutes_used_today": r[7] if r[7] is not None else 0
            })
        return app_list

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error fetching installed applications for child {child_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed while fetching installed applications."
        )


# ==========================================
# 📱 2. TOGGLE APP BY ID (PARENT ACTION)
# ==========================================
@router.post("/{child_id}/toggle/{app_id}", status_code=status.HTTP_200_OK)
async def toggle_application_lockout(
    child_id: str, 
    app_id: int, 
    payload: AppToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Handles real-time lock/unlock override signals for a specific app ID."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    try:
        update_sql = text("""
            UPDATE apt.apt_child_apps_b 
            SET is_blocked = :is_blocked,
                last_updated_date = now()
            WHERE child_id = :child_id AND child_app_id = :app_id;
        """)
        result = await db.execute(update_sql, {
            "is_blocked": payload.is_blocked, 
            "child_id": cid, 
            "app_id": app_id
        })
        
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="App record not found.")

        await db.commit()

        return {
            "status": "success",
            "message": f"Application {app_id} restriction state updated.",
            "updated_state": {
                "child_id": child_id,
                "app_id": app_id,
                "is_blocked": payload.is_blocked
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error toggling app lockout: {e}")
        raise HTTPException(status_code=500, detail="Database failure during app restriction toggle.")


# ==========================================
# 📱 3. SYNC APPS FROM CHILD DEVICE
# ==========================================
@router.post("/{child_id}/sync", status_code=status.HTTP_200_OK)
async def sync_installed_apps(
    child_id: str, 
    payload: SyncAppsPayload, 
    db: AsyncSession = Depends(get_db)
):
    """
    Invoked when child device scans its applications.
    Upserts apps into apt.apt_child_apps_b.
    """
    cid = await get_child_id(db, child_id)
    try:
        upsert_sql = text("""
            INSERT INTO apt.apt_child_apps_b (child_id, package_name, app_name, category, is_blocked)
            VALUES (:child_id, :package_name, :app_name, :category, false)
            ON CONFLICT (child_id, package_name) 
            DO UPDATE SET 
                app_name = EXCLUDED.app_name, 
                category = EXCLUDED.category,
                last_updated_date = now();
        """)
        for app in payload.apps:
            await db.execute(upsert_sql, {
                "child_id": cid,
                "package_name": app.package_name,
                "app_name": app.app_name,
                "category": app.category
            })

        await db.commit()
        return {"status": "success", "message": f"Successfully cataloged {len(payload.apps)} device apps."}

    except Exception as e:
        await db.rollback()
        logger.error(f"Apps Sync Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error during application synchronization.")


# ==========================================
# 📱 4. TOGGLE APP BLOCK BY PACKAGE (PARENT ACTION)
# ==========================================
@router.put("/{child_id}/toggle-block", status_code=status.HTTP_200_OK)
async def toggle_app_restriction(
    child_id: str, 
    payload: ToggleBlockPayload, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """
    Parent toggles an app's restriction by package name or app_id.
    """
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    pkg = payload.target_package

    try:
        upsert_sql = text("""
            INSERT INTO apt.apt_child_apps_b (child_id, package_name, app_name, is_blocked, category)
            VALUES (:child_id, :package_name, :package_name, :is_blocked, 'General')
            ON CONFLICT (child_id, package_name) 
            DO UPDATE SET 
                is_blocked = EXCLUDED.is_blocked,
                last_updated_date = now();
        """)
        await db.execute(upsert_sql, {
            "is_blocked": payload.is_blocked,
            "child_id": cid,
            "package_name": pkg
        })

        await db.commit()
        
        return {
            "status": "success", 
            "package_name": pkg, 
            "is_blocked": payload.is_blocked
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"App Toggle Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database failure during app restriction toggle: {str(e)}"
        )


# ==========================================
# 📱 5. SET APP TIME LIMIT (PARENT ACTION)
# ==========================================
@router.put("/{child_id}/set-limit", status_code=status.HTTP_200_OK)
async def set_app_time_limit(
    child_id: str, 
    payload: SetAppLimitPayload, 
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Parent assigns a daily usage limit in minutes to an application."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)
    
    try:
        update_sql = text("""
            UPDATE apt.apt_child_apps_b 
            SET daily_limit_minutes = :limit,
                last_updated_date = now()
            WHERE child_id = :child_id AND package_name = :package_name;
        """)
        result = await db.execute(update_sql, {
            "limit": payload.daily_limit_minutes,
            "child_id": cid,
            "package_name": payload.package_name
        })

        if result.rowcount == 0:
            # If app doesn't exist yet, insert with limit
            insert_sql = text("""
                INSERT INTO apt.apt_child_apps_b (child_id, package_name, app_name, daily_limit_minutes)
                VALUES (:child_id, :package_name, :package_name, :limit)
                ON CONFLICT (child_id, package_name) DO UPDATE SET daily_limit_minutes = EXCLUDED.daily_limit_minutes;
            """)
            await db.execute(insert_sql, {
                "child_id": cid,
                "package_name": payload.package_name,
                "limit": payload.daily_limit_minutes
            })

        await db.commit()
        
        return {
            "status": "success", 
            "package_name": payload.package_name, 
            "daily_limit_minutes": payload.daily_limit_minutes
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"App Time Limit Error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Database failure setting app limit: {str(e)}"
        )


# ==========================================
# 📱 6. GET LIVE RULES (CHILD DEVICE ENGINE)
# ==========================================
@router.get("/{child_id}/rules", status_code=status.HTTP_200_OK)
async def get_app_restriction_rules(child_id: str, db: AsyncSession = Depends(get_db)):
    """The child's device runtime requests this list to enforce local block policies."""
    cid = await get_child_id(db, child_id)
    try:
        query = text("""
            SELECT package_name, app_name, is_blocked, daily_limit_minutes, is_always_allowed 
            FROM apt.apt_child_apps_b 
            WHERE child_id = :child_id;
        """)
        result = await db.execute(query, {"child_id": cid})
        rows = result.fetchall()
        
        rules_list = []
        for r in rows:
            rules_list.append({
                "package_name": r[0],
                "app_name": r[1] or r[0],
                "is_blocked": bool(r[2]),
                "daily_limit_minutes": int(r[3]) if r[3] is not None else -1,
                "is_always_allowed": bool(r[4])
            })
        
        return {"status": "success", "child_id": str(child_id), "app_policies": rules_list}
    except Exception as e:
        await db.rollback()
        logger.error(f"App Rules Fetch Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database failure fetching app rules.")


# ==========================================
# 📱 7. LOG APP USAGE TELEMETRY
# ==========================================
@router.post("/{child_id}/usage-report", status_code=status.HTTP_200_OK)
async def submit_app_usage_telemetry(
    child_id: str, 
    payload: SubmitUsagePayload, 
    db: AsyncSession = Depends(get_db)
):
    """Updates per-app usage timers and rolls up total minutes to daily screen time."""
    cid = await get_child_id(db, child_id)
    try:
        # Update individual app minutes
        update_app_usage = text("""
            UPDATE apt.apt_child_apps_b
            SET minutes_used_today = :minutes_used,
                last_updated_date = now()
            WHERE child_id = :child_id AND package_name = :package_name;
        """)
        
        for item in payload.usage_data:
            await db.execute(update_app_usage, {
                "child_id": cid,
                "package_name": item.package_name,
                "minutes_used": item.minutes_used
            })
        
        # Roll up total screen time into apt_screen_time_b
        total_minutes = sum(item.minutes_used for item in payload.usage_data)
        today = datetime.date.today()
        
        upsert_st_sql = text("""
            INSERT INTO apt.apt_screen_time_b (child_id, daily_limit_minutes, minutes_used, record_date, is_locked_remotely)
            VALUES (:child_id, 240, :total_minutes, :today, false)
            ON CONFLICT (child_id, record_date) 
            DO UPDATE SET minutes_used = EXCLUDED.minutes_used, last_updated_date = now();
        """)
        await db.execute(upsert_st_sql, {
            "child_id": cid, 
            "total_minutes": total_minutes,
            "today": today
        })
            
        await db.commit()
        return {"status": "success", "message": "Daily usage telemetry updated successfully."}
    except Exception as e:
        await db.rollback()
        logger.error(f"App Usage Telemetry Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database failure submitting usage telemetry.")


# ==========================================
# 🚨 8. ALERT: NEW APP INSTALLED BY CHILD
# ==========================================
@router.post("/{child_id}/new-install-alert", status_code=status.HTTP_201_CREATED)
async def alert_parent_of_new_installation(
    child_id: str,
    payload: NewInstallPayload,
    db: AsyncSession = Depends(get_db)
):
    """Registers newly downloaded app and logs notification for parent."""
    cid = await get_child_id(db, child_id)
    try:
        parent_lookup = text("SELECT parent_user_id FROM apt.apt_children_b WHERE child_id = :child_id LIMIT 1;")
        p_res = await db.execute(parent_lookup, {"child_id": cid})
        p_row = p_res.fetchone()
        parent_id = p_row[0] if p_row else None

        # Insert new app into apt.apt_child_apps_b
        app_register = text("""
            INSERT INTO apt.apt_child_apps_b (child_id, package_name, app_name, category, is_blocked)
            VALUES (:child_id, :pkg, :name, :cat, false)
            ON CONFLICT (child_id, package_name) DO NOTHING;
        """)
        await db.execute(app_register, {
            "child_id": cid, 
            "pkg": payload.package_name, 
            "name": payload.app_name, 
            "cat": payload.category
        })

        # Send notification to parent
        if parent_id:
            alert_msg = f"Your child installed a new app: '{payload.app_name}' ({payload.package_name})."
            notify_sql = text("""
                INSERT INTO apt.apt_parent_notification_b (parent_user_id, message, is_read, created_by, created_date)
                VALUES (:parent_id, :msg, FALSE, 'SYSTEM', now());
            """)
            await db.execute(notify_sql, {"parent_id": parent_id, "msg": alert_msg})
        
        await db.commit()
        return {"status": "success", "message": "New app installation recorded."}
    except Exception as e:
        await db.rollback()
        logger.error(f"New Install Alert Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database failure processing new install alert.")


# ==========================================
# ⌛ 9. RUNTIME ENGINE: TRACK MINUTE & ENFORCE LOCK
# ==========================================
@router.post("/{child_id}/track-app-time", status_code=status.HTTP_200_OK)
async def track_and_evaluate_app_time_allowance(
    child_id: str,
    payload: TrackTimePayload,
    db: AsyncSession = Depends(get_db)
):
    """The child device background runtime calls this every minute to evaluate app budget."""
    cid = await get_child_id(db, child_id)
    try:
        current_date = datetime.date.today()

        # Reset daily counters if day has rolled over
        reset_sql = text("""
            UPDATE apt.apt_child_apps_b 
            SET minutes_used_today = 0, last_reset_date = :today 
            WHERE child_id = :child_id AND (last_reset_date < :today OR last_reset_date IS NULL);
        """)
        await db.execute(reset_sql, {"child_id": cid, "today": current_date})

        # Increment minutes used for target app
        increment_sql = text("""
            UPDATE apt.apt_child_apps_b 
            SET minutes_used_today = minutes_used_today + :inc,
                last_updated_date = now()
            WHERE child_id = :child_id AND package_name = :pkg;
        """)
        await db.execute(increment_sql, {
            "inc": payload.minutes_to_increment, 
            "child_id": cid, 
            "pkg": payload.package_name
        })
        
        # Check rule conditions
        rules_sql = text("""
            SELECT minutes_used_today, daily_limit_minutes, is_blocked 
            FROM apt.apt_child_apps_b 
            WHERE child_id = :child_id AND package_name = :pkg;
        """)
        res = await db.execute(rules_sql, {"child_id": cid, "pkg": payload.package_name})
        row = res.fetchone()

        if not row:
            await db.commit()
            return {"package_name": payload.package_name, "action_lock_app": False}

        used_today, max_limit, admin_blocked = row
        time_limit_breached = (max_limit is not None and max_limit > 0) and (used_today >= max_limit)
        enforce_lockout = bool(admin_blocked or time_limit_breached)

        await db.commit()

        return {
            "package_name": payload.package_name,
            "minutes_used_today": used_today,
            "daily_limit_minutes": max_limit,
            "action_lock_app": enforce_lockout,
            "lock_reason": "Parent manual lock active" if admin_blocked else ("Daily app time limit exhausted" if time_limit_breached else "Authorized usage window")
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Track App Time Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error evaluating app time limits.")


# ==========================================
# 🚨 10. TRIGGER: APP UNINSTALLED BY CHILD
# ==========================================
@router.post("/{child_id}/uninstall-alert", status_code=status.HTTP_200_OK)
async def alert_parent_of_uninstallation(
    child_id: str, 
    payload: UninstallAppPayload, 
    db: AsyncSession = Depends(get_db)
):
    """Removes uninstalled app entry from apt.apt_child_apps_b."""
    cid = await get_child_id(db, child_id)
    try:
        app_removal = text("""
            DELETE FROM apt.apt_child_apps_b 
            WHERE child_id = :child_id AND package_name = :package_name;
        """)
        await db.execute(app_removal, {"child_id": cid, "package_name": payload.package_name})
        await db.commit()
        return {"status": "success", "message": "App uninstallation logged."}
    except Exception as e:
        await db.rollback()
        logger.error(f"App Uninstall Alert Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database failure logging app uninstallation.")