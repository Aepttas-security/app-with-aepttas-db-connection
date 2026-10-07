# app/routers/location.py
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.models.db_models import User
from app.services.jwt import get_current_parent
from app.services.child_service import get_child_id, verify_parent_ownership
from app.services.osm_service import reverse_geocode_osm
from app.services.geofence_service import check_geofence_breaches

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/location", tags=["Child Location & OSM"])


class LocationTelemetryPayload(BaseModel):
    child_id: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    battery_percentage: Optional[int] = Field(100, ge=0, le=100)


class GeofenceCreatePayload(BaseModel):
    fence_name: str
    center_latitude: float = Field(..., ge=-90.0, le=90.0)
    center_longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(..., ge=10.0, le=50000.0)


# 1. INGEST CHILD TELEMETRY
@router.post("/telemetry", status_code=status.HTTP_200_OK)
async def ingest_child_location(
    payload: LocationTelemetryPayload, 
    db: AsyncSession = Depends(get_db)
):
    """Ingests live GPS coordinates, resolves OSM street address, and evaluates geofences."""
    try:
        cid = await get_child_id(db, payload.child_id)

        # 1. Reverse Geocode with OpenStreetMap Nominatim
        resolved_address = await reverse_geocode_osm(payload.latitude, payload.longitude)

        # 2. Insert into apt_child_location_b matching your exact columns
        insert_loc_sql = text("""
            INSERT INTO apt.apt_child_location_b (
                child_id, 
                latitude, 
                longitude, 
                current_address, 
                battery_percentage, 
                recorded_date
            )
            VALUES (
                :cid, 
                :lat, 
                :lon, 
                :address, 
                :battery, 
                NOW()
            );
        """)
        await db.execute(insert_loc_sql, {
            "cid": cid,
            "lat": payload.latitude,
            "lon": payload.longitude,
            "address": resolved_address,
            "battery": payload.battery_percentage
        })

        # 3. Check active geofences matching center_latitude / center_longitude / fence_name
        fence_query = text("""
            SELECT fence_name, center_latitude, center_longitude, radius_meters 
            FROM apt.apt_geofence_b 
            WHERE child_id = :cid AND is_active = true;
        """)
        fence_res = await db.execute(fence_query, {"cid": cid})
        fences = [
            {
                "name": r[0], 
                "latitude": float(r[1]), 
                "longitude": float(r[2]), 
                "radius_meters": float(r[3])
            } 
            for r in fence_res.fetchall()
        ]

        breached_zones = check_geofence_breaches(payload.latitude, payload.longitude, fences)

        # 4. Create Parent Notification if geofence is breached
        if breached_zones:
            alert_msg = f"Boundary Alert: Child has exited safe zone(s): {', '.join(breached_zones)}"
            notify_sql = text("""
                INSERT INTO apt.apt_parent_notification_b (
                    parent_user_id, 
                    message, 
                    is_read, 
                    created_by, 
                    sent_date
                )
                SELECT 
                    parent_user_id, 
                    :msg, 
                    false, 
                    'GEOFENCE_ENGINE', 
                    NOW()
                FROM apt.apt_children_b 
                WHERE child_id = :cid;
            """)
            await db.execute(notify_sql, {"cid": cid, "msg": alert_msg})

        await db.commit()
        return {
            "status": "success", 
            "current_address": resolved_address, 
            "breaches": breached_zones
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Telemetry ingestion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist location telemetry.")


# 2. GET LATEST CHILD POSITION FOR PARENT
@router.get("/{child_id}/latest", status_code=status.HTTP_200_OK)
async def get_latest_child_location(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Fetches the latest recorded GPS point and OSM street address."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    query = text("""
        SELECT latitude, longitude, current_address, battery_percentage, recorded_date 
        FROM apt.apt_child_location_b 
        WHERE child_id = :cid 
        ORDER BY recorded_date DESC 
        LIMIT 1;
    """)
    result = await db.execute(query, {"cid": cid})
    row = result.fetchone()

    if not row:
        return {
            "child_id": str(child_id),
            "latitude": 13.0827,
            "longitude": 80.2707,
            "address": "No location recorded yet",
            "battery_percentage": 100,
            "recorded_date": None
        }

    return {
        "child_id": str(child_id),
        "latitude": float(row[0]),
        "longitude": float(row[1]),
        "address": row[2] or "Address unavailable",
        "battery_percentage": row[3] or 100,
        "recorded_date": row[4]
    }


# 3. GET LOCATION HISTORY (BREADCRUMB TRAIL)
@router.get("/{child_id}/history", status_code=status.HTTP_200_OK)
async def get_location_history(
    child_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Returns past location points for historical trail visualization."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    query = text("""
        SELECT latitude, longitude, current_address, battery_percentage, recorded_date 
        FROM apt.apt_child_location_b 
        WHERE child_id = :cid 
        ORDER BY recorded_date DESC 
        LIMIT :limit;
    """)
    result = await db.execute(query, {"cid": cid, "limit": limit})
    rows = result.fetchall()

    trail = [
        {
            "latitude": float(r[0]),
            "longitude": float(r[1]),
            "address": r[2],
            "battery_percentage": r[3],
            "recorded_date": r[4]
        }
        for r in rows
    ]
    return {"child_id": str(child_id), "trail": trail}


# 4. GEOFENCE MANAGEMENT ENDPOINTS
@router.post("/{child_id}/geofences", status_code=status.HTTP_201_CREATED)
async def create_geofence(
    child_id: str,
    payload: GeofenceCreatePayload,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Creates a new geofence safe zone for a child."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    sql = text("""
        INSERT INTO apt.apt_geofence_b (
            child_id, fence_name, center_latitude, center_longitude, radius_meters, is_active, created_date
        )
        VALUES (:cid, :name, :lat, :lon, :radius, true, NOW())
        RETURNING geofence_id, fence_name, center_latitude, center_longitude, radius_meters, is_active;
    """)
    res = await db.execute(sql, {
        "cid": cid,
        "name": payload.fence_name,
        "lat": payload.center_latitude,
        "lon": payload.center_longitude,
        "radius": payload.radius_meters
    })
    await db.commit()
    row = res.fetchone()
    return {
        "status": "success",
        "geofence": {
            "geofence_id": row[0],
            "fence_name": row[1],
            "center_latitude": float(row[2]),
            "center_longitude": float(row[3]),
            "radius_meters": float(row[4]),
            "is_active": row[5]
        }
    }


@router.get("/{child_id}/geofences", status_code=status.HTTP_200_OK)
async def get_geofences(
    child_id: str,
    db: AsyncSession = Depends(get_db),
    current_parent: User = Depends(get_current_parent)
):
    """Lists all active geofence zones for a child."""
    cid = await get_child_id(db, child_id)
    await verify_parent_ownership(db, cid, current_parent.id)

    sql = text("""
        SELECT geofence_id, fence_name, center_latitude, center_longitude, radius_meters, is_active
        FROM apt.apt_geofence_b
        WHERE child_id = :cid AND is_active = true;
    """)
    res = await db.execute(sql, {"cid": cid})
    rows = res.fetchall()

    return [
        {
            "geofence_id": r[0],
            "fence_name": r[1],
            "center_latitude": float(r[2]),
            "center_longitude": float(r[3]),
            "radius_meters": float(r[4]),
            "is_active": r[5]
        }
        for r in rows
    ]


# 5. MAP TILE CONFIGURATION
@router.get("/tile-config", status_code=status.HTTP_200_OK)
async def get_tile_server_config():
    """Returns tile server config for Leaflet/OSM clients."""
    return {
        "status": "success",
        "tile_server_url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "&copy; OpenStreetMap contributors",
        "max_zoom": 19
    }
