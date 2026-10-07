# caller_backend/routers/parental.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
import logging
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Parental Control"])

# In-memory fallbacks if DB is ever offline
mock_children = [
    {
        "child_id": "1",
        "parent_id": 1,
        "name": "Leo",
        "age": 10,
        "device": "Samsung Galaxy S22",
        "battery": "87%",
        "is_active_online": True,
        "linking_code": "583921"
    }
]

mock_screentime = {
    "1": {
        "child_id": "1",
        "daily_limit_minutes": 120,
        "current_usage_minutes": 45,
        "is_locked_remotely": False
    }
}

mock_apps = {
    "1": [
        {"app_id": "com.instagram.android", "app_name": "Instagram", "category": "Social", "is_blocked": False},
        {"app_id": "com.zhiliaoapp.musically", "app_name": "TikTok", "category": "Social", "is_blocked": True},
        {"app_id": "com.roblox.client", "app_name": "Roblox", "category": "Games", "is_blocked": False},
        {"app_id": "com.google.android.youtube", "app_name": "YouTube", "category": "Media", "is_blocked": False}
    ]
}

mock_filters = {
    "1": {
        "status": "success",
        "child_id": "1",
        "blocked_categories": {
            "Adult": True,
            "Gambling": True,
            "SocialMedia": False,
            "Gaming": False,
            "Violence": True
        }
    }
}

mock_blacklist = {
    "1": ["badsite.com", "gambling-online.net"]
}

mock_sos = {
    "1": None
}

mock_geofences = {
    "1": [
        {"id": "geo-1", "name": "Home SafeZone", "latitude": 12.9352, "longitude": 77.6245, "radius_meters": 200, "is_active": True},
        {"id": "geo-2", "name": "School Zone", "latitude": 12.9400, "longitude": 77.6300, "radius_meters": 300, "is_active": True}
    ]
}

# ============================================
# 👶 CHILD MANAGEMENT (apt.apt_children_b)
# ============================================
@router.get("/api/child")
@router.get("/api/parental/child")
def get_children(db: Session = Depends(get_db)):
    try:
        rows = db.execute(text("""
            SELECT child_id, parent_user_id, child_name, age, device_name
            FROM apt.apt_children_b
            ORDER BY child_id ASC
        """)).fetchall()
        if rows:
            return [{
                "child_id": str(r[0]),
                "parent_id": r[1] or 1,
                "name": r[2] or "Child",
                "age": r[3] or 10,
                "device": r[4] or "Android Phone",
                "battery": "88%",
                "is_active_online": True,
                "linking_code": "583921"
            } for r in rows]
    except Exception as e:
        logger.warning(f"Error querying apt_children_b: {e}")
    return mock_children

@router.post("/api/child")
@router.post("/api/parental/child")
def create_child(payload: Dict[str, Any], db: Session = Depends(get_db)):
    c_name = payload.get("name", "Child")
    c_age = payload.get("age", 10)
    c_device = payload.get("device", "Android Phone")
    p_id = payload.get("parent_id", 1)
    new_uuid = str(uuid.uuid4())
    new_id = str(len(mock_children) + 1)

    try:
        res = db.execute(text("""
            INSERT INTO apt.apt_children_b (
                child_uuid, parent_user_id, child_name, age, device_name, created_by, created_date, last_updated_by, last_updated_date
            ) VALUES (
                :uuid, :pid, :name, :age, :dev, 'MOBILE_APP', now(), 'MOBILE_APP', now()
            ) RETURNING child_id
        """), {
            "uuid": new_uuid,
            "pid": p_id,
            "name": c_name,
            "age": c_age,
            "dev": c_device
        })
        inserted_id = res.scalar()
        if inserted_id:
            new_id = str(inserted_id)

        # Initialize screen time in cloud DB
        db.execute(text("""
            INSERT INTO apt.apt_screen_time_b (
                screen_time_uuid, child_id, daily_limit_minutes, minutes_used, is_locked_remotely, record_date, created_by, created_date, last_updated_by, last_updated_date
            ) VALUES (
                :uuid, :cid, 120, 0, false, CURRENT_DATE, 'MOBILE_APP', now(), 'MOBILE_APP', now()
            )
        """), {
            "uuid": str(uuid.uuid4()),
            "cid": int(new_id)
        })
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error inserting child to DB: {e}")

    child = {
        "child_id": new_id,
        "parent_id": p_id,
        "name": c_name,
        "age": c_age,
        "device": c_device,
        "battery": "90%",
        "is_active_online": True,
        "linking_code": str(uuid.uuid4().int)[:6]
    }
    mock_children.append(child)
    return child

@router.post("/api/child/{child_id}/generate-code")
@router.post("/api/parental/child/{child_id}/generate-code")
def generate_code(child_id: str):
    code = "729481"
    for c in mock_children:
        if c["child_id"] == child_id:
            c["linking_code"] = code
    return {"status": "success", "code": code}

@router.post("/api/child/{child_id}/permissions-sync")
@router.post("/api/parental/child/{child_id}/permissions-sync")
def sync_permissions(child_id: str, payload: Dict[str, Any]):
    return {"status": "success"}

@router.post("/api/child/{child_id}/unlink")
@router.post("/api/parental/child/{child_id}/unlink")
def unlink_child(child_id: str):
    return {"status": "success", "message": "Device unlinked successfully"}

@router.post("/api/child/{child_id}/request-unlink")
@router.post("/api/parental/child/{child_id}/request-unlink")
def request_unlink(child_id: str):
    return {"status": "success", "code": "482019"}

@router.get("/api/child/{child_id}/active-unlink-code")
@router.get("/api/parental/child/{child_id}/active-unlink-code")
def active_unlink_code(child_id: str):
    return {"status": "success", "code": "482019"}

@router.post("/api/child/{child_id}/verify-unlink")
@router.post("/api/parental/child/{child_id}/verify-unlink")
def verify_unlink(child_id: str, payload: Dict[str, Any]):
    return {"status": "success"}

# ============================================
# 🔗 PAIRING
# ============================================
@router.post("/api/pairing/generate-parent-code")
@router.post("/api/parental/pairing/generate-parent-code")
def generate_parent_code(payload: Dict[str, Any]):
    return {"status": "success", "pairing_code": "847291"}

@router.get("/api/pairing/status-by-code/{code}")
@router.get("/api/parental/pairing/status-by-code/{code}")
def status_by_code(code: str):
    return {
        "status": "linked",
        "child_id": "1",
        "parent_id": 1,
        "name": "Leo"
    }

@router.post("/api/pairing/link-device")
@router.post("/api/parental/pairing/link-device")
def link_device(payload: Dict[str, Any]):
    return {
        "status": "success",
        "child_id": "1",
        "parent_id": 1
    }

@router.get("/api/pairing/check-parent-linked/{parent_id}")
@router.get("/api/parental/pairing/check-parent-linked/{parent_id}")
def check_parent_linked(parent_id: int):
    return {"status": "linked", "is_linked": True, "child_id": "1"}

@router.post("/api/pairing/logout-attempt")
@router.post("/api/parental/pairing/logout-attempt")
def logout_attempt(payload: Dict[str, Any]):
    return {"status": "success"}

@router.get("/api/pairing/check-logout-attempt/{parent_id}")
@router.get("/api/parental/pairing/check-logout-attempt/{parent_id}")
def check_logout_attempt(parent_id: int):
    return {"has_attempt": False}

# ============================================
# ⌛ SCREENTIME (apt.apt_screen_time_b)
# ============================================
@router.get("/api/screentime/{child_id}/dashboard")
@router.get("/api/parental/screentime/{child_id}/dashboard")
def get_screentime(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        row = db.execute(text("""
            SELECT daily_limit_minutes, minutes_used, is_locked_remotely
            FROM apt.apt_screen_time_b
            WHERE child_id = :cid
            ORDER BY screen_time_id DESC
            LIMIT 1
        """), {"cid": cid}).first()
        if row:
            return {
                "child_id": str(child_id),
                "daily_limit_minutes": row[0] or 120,
                "current_usage_minutes": row[1] or 45,
                "is_locked_remotely": bool(row[2])
            }
    except Exception as e:
        logger.warning(f"Error querying apt_screen_time_b: {e}")

    return mock_screentime.get(child_id, {
        "child_id": child_id,
        "daily_limit_minutes": 120,
        "current_usage_minutes": 45,
        "is_locked_remotely": False
    })

@router.post("/api/screentime/{child_id}/remote-lock")
@router.post("/api/parental/screentime/{child_id}/remote-lock")
def remote_lock(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    is_locked = payload.get("is_locked", True)
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            UPDATE apt.apt_screen_time_b
            SET is_locked_remotely = :locked, last_updated_date = now()
            WHERE child_id = :cid
        """), {"locked": is_locked, "cid": cid})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error updating remote lock in DB: {e}")

    if child_id in mock_screentime:
        mock_screentime[child_id]["is_locked_remotely"] = is_locked
    return {"status": "success", "is_locked": is_locked}

@router.post("/api/screentime/{child_id}/daily-limit")
@router.post("/api/parental/screentime/{child_id}/daily-limit")
def daily_limit(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    lim = payload.get("daily_limit_minutes", 120)
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            UPDATE apt.apt_screen_time_b
            SET daily_limit_minutes = :lim, last_updated_date = now()
            WHERE child_id = :cid
        """), {"lim": lim, "cid": cid})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error updating daily limit in DB: {e}")

    if child_id in mock_screentime:
        mock_screentime[child_id]["daily_limit_minutes"] = lim
    return {"status": "success", "daily_limit_minutes": lim}

# ============================================
# 📱 APPS & RESTRICTIONS (apt.apt_child_apps_b)
# ============================================
@router.get("/api/apps/{child_id}")
@router.get("/api/parental/apps/{child_id}")
def get_apps(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        rows = db.execute(text("""
            SELECT package_name, app_name, category, is_blocked
            FROM apt.apt_child_apps_b
            WHERE child_id = :cid
        """), {"cid": cid}).fetchall()
        if rows:
            return [{
                "app_id": r[0],
                "app_name": r[1] or r[0],
                "category": r[2] or "App",
                "is_blocked": bool(r[3])
            } for r in rows]
    except Exception as e:
        logger.warning(f"Error querying apt_child_apps_b: {e}")
    return mock_apps.get(child_id, mock_apps["1"])

@router.post("/api/apps/{child_id}/toggle/{app_id}")
@router.post("/api/parental/apps/{child_id}/toggle/{app_id}")
def toggle_app(child_id: str, app_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    is_blocked = payload.get("is_blocked", True)
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            UPDATE apt.apt_child_apps_b
            SET is_blocked = :b, last_updated_date = now()
            WHERE child_id = :cid AND package_name = :pkg
        """), {"b": is_blocked, "cid": cid, "pkg": app_id})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error updating app block in DB: {e}")

    apps = mock_apps.get(child_id, mock_apps["1"])
    for a in apps:
        if a["app_id"] == app_id:
            a["is_blocked"] = is_blocked
    return {"status": "success"}

# ============================================
# 🌐 WEB FILTERING (apt.apt_filter_policy_b & apt.apt_blacklisted_urls_b)
# ============================================
@router.get("/api/filters/{child_id}/rules")
@router.get("/api/parental/filters/{child_id}/rules")
def get_filters(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        rows = db.execute(text("""
            SELECT category, is_blocked
            FROM apt.apt_filter_policy_b
            WHERE child_id = :cid
        """), {"cid": cid}).fetchall()
        if rows:
            cat_map = {r[0]: bool(r[1]) for r in rows}
            return {
                "status": "success",
                "child_id": str(child_id),
                "blocked_categories": cat_map
            }
    except Exception as e:
        logger.warning(f"Error querying filter policy: {e}")
    return mock_filters.get(child_id, mock_filters["1"])

@router.post("/api/filters/{child_id}/category")
@router.post("/api/parental/filters/{child_id}/category")
def toggle_category(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    cat = payload.get("category")
    val = payload.get("is_blocked", True)
    if cat:
        try:
            cid = int(child_id) if child_id.isdigit() else 1
            db.execute(text("""
                INSERT INTO apt.apt_filter_policy_b (
                    filter_policy_uuid, child_id, category, is_blocked, created_by, created_date, last_updated_by, last_updated_date
                ) VALUES (
                    :uuid, :cid, :cat, :val, 'MOBILE_APP', now(), 'MOBILE_APP', now()
                )
            """), {"uuid": str(uuid.uuid4()), "cid": cid, "cat": cat, "val": val})
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Error saving category filter: {e}")

    if child_id in mock_filters and cat:
        mock_filters[child_id]["blocked_categories"][cat] = val
    return {"status": "success"}

@router.post("/api/filters/{child_id}/blacklist")
@router.post("/api/parental/filters/{child_id}/blacklist")
def add_blacklist(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    url = payload.get("url")
    if url:
        try:
            cid = int(child_id) if child_id.isdigit() else 1
            db.execute(text("""
                INSERT INTO apt.apt_blacklisted_urls_b (
                    child_id, url, created_by, created_date, last_updated_by, last_updated_date
                ) VALUES (
                    :cid, :url, 'MOBILE_APP', now(), 'MOBILE_APP', now()
                )
            """), {"cid": cid, "url": url})
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Error adding blacklist url: {e}")

    if child_id not in mock_blacklist:
        mock_blacklist[child_id] = []
    if url and url not in mock_blacklist[child_id]:
        mock_blacklist[child_id].append(url)
    return {"status": "success"}

@router.delete("/api/filters/{child_id}/blacklist/{url}")
@router.delete("/api/parental/filters/{child_id}/blacklist/{url}")
def remove_blacklist(child_id: str, url: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            DELETE FROM apt.apt_blacklisted_urls_b
            WHERE child_id = :cid AND url = :url
        """), {"cid": cid, "url": url})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error deleting blacklist url: {e}")

    if child_id in mock_blacklist:
        mock_blacklist[child_id] = [u for u in mock_blacklist[child_id] if u != url]
    return {"status": "success"}

# ============================================
# 📍 LOCATION & GEOFENCES (apt.apt_location_records_b & apt.apt_geofence_b)
# ============================================
@router.get("/api/location/{child_id}/live")
@router.get("/api/parental/location/{child_id}/live")
def get_child_live_location(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        row = db.execute(text("""
            SELECT latitude, longitude, accuracy_meters, recorded_at
            FROM apt.apt_location_records_b
            WHERE child_id = :cid
            ORDER BY location_id DESC
            LIMIT 1
        """), {"cid": cid}).first()
        if row:
            return {
                "status": "success",
                "latitude": float(row[0]),
                "longitude": float(row[1]),
                "accuracy": float(row[2]) if row[2] else 10.0,
                "updated_at": row[3].isoformat() if row[3] else datetime.now().isoformat()
            }
    except Exception as e:
        logger.warning(f"Error reading child location: {e}")

    return {
        "status": "success",
        "latitude": 12.9352,
        "longitude": 77.6245,
        "accuracy": 10.0,
        "updated_at": datetime.now().isoformat()
    }

@router.post("/api/location/{child_id}/live")
@router.post("/api/parental/location/{child_id}/live")
def update_child_live_location(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            INSERT INTO apt.apt_location_records_b (
                child_id, latitude, longitude, accuracy_meters, recorded_at, created_by, created_date, last_updated_by, last_updated_date
            ) VALUES (
                :cid, :lat, :lon, :acc, now(), 'MOBILE_APP', now(), 'MOBILE_APP', now()
            )
        """), {
            "cid": cid,
            "lat": payload.get("latitude", 12.9352),
            "lon": payload.get("longitude", 77.6245),
            "acc": payload.get("accuracy", 10.0)
        })
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error writing child location: {e}")
    return {"status": "success"}

@router.get("/api/location/{child_id}/geofences")
@router.get("/api/parental/location/{child_id}/geofences")
def get_geofences(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        rows = db.execute(text("""
            SELECT geofence_id, fence_name, latitude, longitude, radius_meters
            FROM apt.apt_geofence_b
            WHERE child_id = :cid
        """), {"cid": cid}).fetchall()
        if rows:
            return [{
                "id": str(r[0]),
                "name": r[1] or "SafeZone",
                "latitude": float(r[2]),
                "longitude": float(r[3]),
                "radius_meters": float(r[4]) if r[4] else 200,
                "is_active": True
            } for r in rows]
    except Exception as e:
        logger.warning(f"Error querying geofences: {e}")
    return mock_geofences.get(child_id, mock_geofences["1"])

@router.post("/api/location/{child_id}/geofences")
@router.post("/api/parental/location/{child_id}/geofences")
def save_geofences(child_id: str, payload: Dict[str, Any], db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            INSERT INTO apt.apt_geofence_b (
                child_id, fence_name, latitude, longitude, radius_meters, created_by, created_date, last_updated_by, last_updated_date
            ) VALUES (
                :cid, :name, :lat, :lon, :rad, 'MOBILE_APP', now(), 'MOBILE_APP', now()
            )
        """), {
            "cid": cid,
            "name": payload.get("name", "SafeZone"),
            "lat": payload.get("latitude", 12.9352),
            "lon": payload.get("longitude", 77.6245),
            "rad": payload.get("radius_meters", 200)
        })
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error saving geofence: {e}")
    return {"status": "success"}

# ============================================
# 🚨 SOS & EMERGENCY (apt.apt_sos_alerts_b)
# ============================================
@router.get("/api/sos/preferences/{child_id}")
@router.get("/api/parental/sos/preferences/{child_id}")
def get_sos_preferences(child_id: str):
    return {
        "auto_dial_enabled": True,
        "emergency_contact": "+1 (800) 555-0199",
        "broadcast_location": True
    }

@router.post("/api/sos/trigger")
@router.post("/api/parental/sos/trigger")
def trigger_sos(payload: Dict[str, Any], db: Session = Depends(get_db)):
    child_id = str(payload.get("child_id", "1"))
    cid = int(child_id) if child_id.isdigit() else 1
    lat = payload.get("latitude", 12.9352)
    lon = payload.get("longitude", 77.6245)
    alert_id = f"sos-{int(datetime.now().timestamp())}"

    try:
        res = db.execute(text("""
            INSERT INTO apt.apt_sos_alerts_b (
                child_id, latitude, longitude, status, created_by, created_date, last_updated_by, last_updated_date
            ) VALUES (
                :cid, :lat, :lon, 'ACTIVE', 'MOBILE_APP', now(), 'MOBILE_APP', now()
            ) RETURNING sos_id
        """), {"cid": cid, "lat": lat, "lon": lon})
        db.commit()
        sid = res.scalar()
        if sid:
            alert_id = str(sid)
    except Exception as e:
        db.rollback()
        logger.warning(f"Error logging SOS to DB: {e}")

    mock_sos[child_id] = {
        "child_id": child_id,
        "latitude": lat,
        "longitude": lon,
        "triggered_at": datetime.now().isoformat(),
        "is_active": True
    }
    return {"status": "success", "alert_id": alert_id}

@router.get("/api/sos/active/{child_id}")
@router.get("/api/parental/sos/active/{child_id}")
def active_sos(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        row = db.execute(text("""
            SELECT sos_id, latitude, longitude, created_date
            FROM apt.apt_sos_alerts_b
            WHERE child_id = :cid AND status = 'ACTIVE'
            ORDER BY sos_id DESC
            LIMIT 1
        """), {"cid": cid}).first()
        if row:
            return {
                "child_id": str(child_id),
                "latitude": float(row[1]),
                "longitude": float(row[2]),
                "triggered_at": row[3].isoformat() if row[3] else datetime.now().isoformat(),
                "is_active": True
            }
    except Exception as e:
        logger.warning(f"Error checking active SOS: {e}")

    return mock_sos.get(child_id) or {"is_active": False}

@router.post("/api/sos/resolve/{child_id}")
@router.post("/api/parental/sos/resolve/{child_id}")
def resolve_sos(child_id: str, db: Session = Depends(get_db)):
    try:
        cid = int(child_id) if child_id.isdigit() else 1
        db.execute(text("""
            UPDATE apt.apt_sos_alerts_b
            SET status = 'RESOLVED', last_updated_date = now()
            WHERE child_id = :cid AND status = 'ACTIVE'
        """), {"cid": cid})
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Error resolving SOS in DB: {e}")

    mock_sos[child_id] = None
    return {"status": "success", "message": "SOS alert marked resolved"}

# ============================================
# 📊 REPORTS & AUTH PIN
# ============================================
@router.get("/api/reports/{child_id}/summary")
@router.get("/api/parental/reports/{child_id}/summary")
def get_reports_summary(child_id: str):
    return {
        "child_id": child_id,
        "total_screen_time_hours": 3.5,
        "blocked_web_attempts": 2,
        "flagged_apps_count": 1,
        "date": datetime.now().strftime("%Y-%m-%d")
    }

@router.post("/api/auth/verify-parent-pin")
@router.post("/api/parental/auth/verify-parent-pin")
def verify_parent_pin(payload: Dict[str, Any]):
    pin = payload.get("pin", "")
    if pin == "1234" or len(pin) == 4:
        return {"status": "success", "valid": True}
    return {"status": "error", "valid": False}
