# security-backend/modules/geolocation/router.py
"""
FastAPI Router for Geolocation:
- POST /api/v1/geolocation/current (accepts live GPS payload from React Native app)
- POST /api/v1/geolocation/save (kept for full backwards compatibility)
- GET /api/v1/geolocation/current (returns latest valid GPS record)
- GET /api/v1/geolocation/history (returns actual GPS records only)
- POST /api/v1/geolocation/nearby (returns places around live coordinates; never saved to GPS history)
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import logging

try:
    from database import get_db
except ImportError:
    try:
        from app.database import get_db
    except ImportError:
        def get_db():
            yield None

from .service import geo_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/geolocation", tags=["Geolocation"])


class LiveGPSPayload(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = 10.0
    provider: Optional[str] = "gps"
    timestamp: Optional[str] = None
    device_id: Optional[str] = None
    platform: Optional[str] = "android"
    is_mock_location: Optional[bool] = False
    mock_location_reasons: Optional[List[str]] = []
    ip: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    isp: Optional[str] = None
    user_id: Optional[int] = 1


class NearbyPOIRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: Optional[float] = 5.0


@router.post("/current")
@router.post("/save")
async def save_current_location(payload: LiveGPSPayload, request: Request, db: Session = Depends(get_db)):
    """
    Accepts live GPS payload from React Native app.
    Saves live coordinates as device location in DB & live cache.
    """
    try:
        data = payload.model_dump()
        if not data.get("ip"):
            data["ip"] = request.client.host if request.client else "127.0.0.1"
        saved = geo_service.store_live_location(db, data)
        return {
            "status": "success",
            "message": "Live location recorded successfully",
            "data": saved
        }
    except Exception as e:
        logger.error(f"Error saving live location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current")
async def get_current_location(db: Session = Depends(get_db)):
    """
    Returns latest valid GPS record.
    Never allows old seeded/default Bangalore records to override live GPS!
    """
    try:
        live = geo_service.get_current_location(db)
        if not live:
            return {
                "status": "no_data",
                "message": "No live GPS coordinates received yet. Waiting for device fix.",
                "data": None
            }
        return {
            "status": "success",
            "data": live
        }
    except Exception as e:
        logger.error(f"Error fetching current location: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_location_history(limit: int = 100, db: Session = Depends(get_db)):
    """
    Returns actual GPS records history only.
    Excludes dummy records and nearby POIs.
    """
    try:
        history = geo_service.get_history(db, limit)
        return {
            "status": "success",
            "history": history,
            "total": len(history),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error fetching location history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nearby")
async def get_nearby_pois(req: NearbyPOIRequest, db: Session = Depends(get_db)):
    """
    Uses live latitude and longitude received from device.
    CRITICAL: Nearby POIs are NOT inserted into GPS history / database as fake location records.
    """
    try:
        places = geo_service.get_nearby_places(db, req.latitude, req.longitude, req.radius_km or 5.0)
        return {
            "status": "success",
            "places": places,
            "count": len(places),
            "location": {"latitude": req.latitude, "longitude": req.longitude, "radius_km": req.radius_km}
        }
    except Exception as e:
        logger.error(f"Error fetching nearby places: {e}")
        raise HTTPException(status_code=500, detail=str(e))
