from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.services.child_service import get_child_id

router = APIRouter(prefix="/api/reports", tags=["Activity Reporting"])

@router.get("/{child_id}/summary")
async def get_child_activity_report(child_id: str, db: AsyncSession = Depends(get_db)):
    """Generates an aggregated behavioral dataset report for dashboard metrics visualizations."""
    cid = await get_child_id(db, child_id)
    
    total_screentime = 0
    blocked_apps = 0
    geofence_breaches = 0
    sos_alerts = 0
    top_apps = []
    
    # 1. Query total screen time from apt.apt_screen_time_b
    try:
        st_query = text("""
            SELECT minutes_used 
            FROM apt.apt_screen_time_b 
            WHERE child_id = :child_id 
            ORDER BY record_date DESC 
            LIMIT 1;
        """)
        st_result = await db.execute(st_query, {"child_id": cid})
        db_screentime = st_result.scalar()
        if db_screentime is not None:
            total_screentime = int(db_screentime)
    except Exception as e:
        await db.rollback()
        print(f"[INFO] Reporting screentime query notice: {e}")
        
    # 2. Query blocked apps count from apt.apt_child_apps_b
    try:
        blocked_query = text("""
            SELECT COUNT(*) 
            FROM apt.apt_child_apps_b 
            WHERE child_id = :child_id AND is_blocked = true;
        """)
        blocked_result = await db.execute(blocked_query, {"child_id": cid})
        blocked_apps = int(blocked_result.scalar() or 0)
    except Exception as e:
        await db.rollback()
        print(f"[INFO] Reporting blocked apps query notice: {e}")
        
    # 3. Query geofence breach count from apt.apt_geofence_b
    try:
        breach_query = text("""
            SELECT COUNT(*) 
            FROM apt.apt_geofence_b 
            WHERE child_id = :child_id;
        """)
        breach_result = await db.execute(breach_query, {"child_id": cid})
        geofence_breaches = int(breach_result.scalar() or 0)
    except Exception as e:
        await db.rollback()
        print(f"[INFO] Reporting breach query notice: {e}")
        
    # 4. Query unresolved SOS alerts count from apt.apt_sos_alerts_b
    try:
        sos_query = text("""
            SELECT COUNT(*) 
            FROM apt.apt_sos_alerts_b 
            WHERE child_id = :child_id AND is_resolved = false;
        """)
        sos_result = await db.execute(sos_query, {"child_id": cid})
        sos_alerts = int(sos_result.scalar() or 0)
    except Exception as e:
        await db.rollback()
        print(f"[INFO] Reporting SOS subquery notice: {e}")

    # 5. Query top apps by duration from apt.apt_child_apps_b
    try:
        top_apps_query = text("""
            SELECT app_name, COALESCE(usage_minutes, 0), COALESCE(category, 'General') 
            FROM apt.apt_child_apps_b 
            WHERE child_id = :child_id 
            ORDER BY usage_minutes DESC 
            LIMIT 5;
        """)
        top_apps_res = await db.execute(top_apps_query, {"child_id": cid})
        rows = top_apps_res.fetchall()
        for r in rows:
            top_apps.append({
                "app_name": r[0],
                "duration_minutes": int(r[1]),
                "category": r[2]
            })
    except Exception as e:
        await db.rollback()
        print(f"[INFO] Reporting top apps query notice: {e}")

    return {
        "status": "success",
        "child_id": str(child_id),
        "report_metrics": {
            "total_screentime_minutes": total_screentime,
            "blocked_app_attempts": blocked_apps,
            "geofence_boundary_breaches": geofence_breaches,
            "unresolved_sos_alerts": sos_alerts,
            "top_apps_by_duration": top_apps
        }
    }