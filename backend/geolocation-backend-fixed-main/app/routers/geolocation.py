# routes/geolocation.py
"""FastAPI router for geolocation endpoints using PostgreSQL persistence.

All endpoints interact with the database via injected session and the
GeolocationService implementation.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import GeolocationScan
from app.services.geolocation import geo_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class LocationData(BaseModel):
    latitude: float
    longitude: float
    ip: Optional[str] = None
    is_mock_location: bool = False
    accuracy: Optional[float] = None
    provider: Optional[str] = None
    timestamp: Optional[str] = None
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    platform: Optional[str] = None
    mock_location_reasons: Optional[List[str]] = []
    user_id: Optional[int] = None
    program_id: Optional[int] = None
    attributes: Optional[dict] = {}
    raw_provider_flags: Optional[dict] = None
    created_by: Optional[str] = None

class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 5

@router.post("/api/v1/geolocation/current")
async def store_location(
    location: LocationData,
    request: Request,
    db: Session = Depends(get_db),
):
    """Store location data with spoofing detection.

    The client IP is filled in if not provided.
    """
    try:
        if not location.ip:
            location.ip = request.client.host
        location_dict = location.dict()
        result = geo_service.store_location(db, location_dict)
        return {
            "status": "success",
            "message": "Location stored successfully",
            "data": {
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
                "timestamp": result.get("timestamp"),
                "is_spoofed": result.get("is_spoofed"),
                "spoof_confidence": result.get("spoof_confidence"),
                "spoof_reasons": result.get("spoof_reasons"),
                "is_mock_location": result.get("is_mock_location"),
                "speed_kmh": result.get("speed_kmh"),
                "record_id": result.get("record_id"),
            },
        }
    except Exception as e:
        logger.error(f"Error storing location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store location: {str(e)}")

@router.get("/api/v1/geolocation/current")
async def get_live_location(db: Session = Depends(get_db)):
    """Retrieve the most recent location record.
    """
    try:
        live = geo_service.get_live_location(db)
        if not live:
            return {"status": "no_data", "message": "No live location available", "data": None}
        response_data = {
            "latitude": live.get("latitude"),
            "longitude": live.get("longitude"),
            "timestamp": live.get("timestamp"),
            "is_spoofed": live.get("is_spoofed"),
            "spoof_confidence": live.get("spoof_confidence"),
            "spoof_reasons": live.get("spoof_reasons"),
            "is_mock_location": live.get("is_mock_location"),
            "speed_kmh": live.get("speed_kmh"),
            "record_id": live.get("record_id"),
            "accuracy": live.get("accuracy"),
            "provider": live.get("provider"),
            "city": live.get("city"),
            "country": live.get("country"),
            "address": live.get("address"),
        }
        return {"status": "success", "data": response_data}
    except Exception as e:
        logger.error(f"Error getting live location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get live location: {str(e)}")

@router.get("/api/v1/geolocation/history")
async def get_location_history(
    limit: int = 100,
    include_spoofed: bool = True,
    db: Session = Depends(get_db),
):
    """Return recent location history.
    """
    try:
        history = geo_service.get_history(db, limit, include_spoofed)
        return {"status": "success", "history": history, "total": len(history), "limit": limit}
    except Exception as e:
        logger.error(f"Error getting location history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get location history: {str(e)}")

@router.post("/api/v1/geolocation/nearby")
async def get_nearby_places(request: NearbyRequest, db: Session = Depends(get_db)):
    """Fetch nearby places from the PostgreSQL table.
    """
    try:
        places = geo_service.get_nearby_places(db, request.latitude, request.longitude, request.radius_km)
        return {
            "status": "success",
            "places": places,
            "count": len(places),
            "location": {"latitude": request.latitude, "longitude": request.longitude, "radius_km": request.radius_km},
        }
    except Exception as e:
        logger.error(f"Error getting nearby places: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nearby places: {str(e)}")

@router.get("/api/v1/geolocation/stats")
async def get_spoofing_stats(db: Session = Depends(get_db)):
    """Return spoofing statistics aggregated from persisted records.
    """
    try:
        stats = geo_service.get_spoofing_stats(db)
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/api/v1/geolocation/check")
async def check_spoofing(request: Request, latitude: float, longitude: float, db: Session = Depends(get_db)):
    """Debug endpoint to evaluate spoofing detection for a coordinate pair.
    """
    try:
        location_data = {
            "latitude": latitude,
            "longitude": longitude,
            "ip": request.client.host,
            "timestamp": datetime.now().isoformat(),
        }
        previous = geo_service.get_live_location(db)
        result = geo_service.detect_spoofing(location_data, previous)
        return {
            "status": "success",
            "is_spoofed": result.get("is_spoofed"),
            "spoof_confidence": result.get("spoof_confidence"),
            "spoof_reasons": result.get("spoof_reasons"),
            "speed_kmh": result.get("speed_kmh"),
        }
    except Exception as e:
        logger.error(f"Error checking spoofing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check spoofing: {str(e)}")

@router.delete("/api/v1/geolocation/history")
async def clear_history(db: Session = Depends(get_db)):
    """Delete all location records – intended for testing only.
    """
    try:
        db.query(GeolocationScan).delete()
        db.commit()
        return {"status": "success", "message": "Location history cleared"}
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")