# caller_backend/routers/geolocation.py
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict
from datetime import datetime, timezone
import math
import logging
from database import get_db
from schemas import LocationData, NearbyRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Geolocation & Spoofing Detection"])

# In-memory location history fallback
cached_locations = []

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    try:
        R = 6371  # Earth radius in km
        lat1_rad = math.radians(float(lat1))
        lat2_rad = math.radians(float(lat2))
        delta_lat = math.radians(float(lat2 - lat1))
        delta_lon = math.radians(float(lon2 - lon1))
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad)
            * math.cos(lat2_rad)
            * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return 0.0

def detect_spoofing(curr: Dict, prev: Optional[Dict] = None) -> Dict:
    spoof_flags: List[str] = []
    spoof_confidence = "low"
    is_spoofed = False
    speed_kmh = 0.0

    if curr.get("is_mock_location", False):
        is_spoofed = True
        spoof_confidence = "high"
        spoof_flags.append("Mock location app detected on device")

    if prev:
        try:
            dist = calculate_distance(
                prev.get("latitude", 0), prev.get("longitude", 0),
                curr.get("latitude", 0), curr.get("longitude", 0)
            )
            prev_t = datetime.fromisoformat(prev.get("timestamp", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
            curr_t = datetime.fromisoformat(curr.get("timestamp", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))
            diff_hours = abs((curr_t - prev_t).total_seconds()) / 3600.0
            if diff_hours > 0:
                speed_kmh = dist / diff_hours
                if speed_kmh > 900:
                    is_spoofed = True
                    spoof_confidence = "high"
                    spoof_flags.append(f"Impossible speed: {round(speed_kmh)} km/h")
                elif speed_kmh > 500:
                    is_spoofed = True
                    spoof_confidence = "medium"
                    spoof_flags.append(f"Suspicious speed: {round(speed_kmh)} km/h")
        except Exception as e:
            logger.debug(f"Speed calculation error: {e}")

    lat = curr.get("latitude", 0)
    lon = curr.get("longitude", 0)
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        is_spoofed = True
        spoof_confidence = "medium"
        spoof_flags.append("Invalid coordinates detected")

    return {
        "is_spoofed": is_spoofed,
        "spoof_confidence": spoof_confidence,
        "spoof_reasons": spoof_flags,
        "speed_kmh": speed_kmh,
        "is_mock_location": curr.get("is_mock_location", False)
    }

@router.post("/api/v1/geolocation/current")
@router.post("/api/geo/current")
async def store_location(location: LocationData, request: Request, db: Session = Depends(get_db)):
    try:
        curr_dict = location.model_dump()
        if not curr_dict.get("ip"):
            curr_dict["ip"] = request.client.host if request.client else "127.0.0.1"
        if not curr_dict.get("timestamp"):
            curr_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

        prev_dict = cached_locations[0] if cached_locations else None
        spoof_info = detect_spoofing(curr_dict, prev_dict)

        record_id = int(datetime.now().timestamp() * 1000) % 1000000
        res_data = {
            "record_id": record_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": curr_dict["timestamp"],
            "is_spoofed": spoof_info["is_spoofed"],
            "spoof_confidence": spoof_info["spoof_confidence"],
            "spoof_reasons": spoof_info["spoof_reasons"],
            "is_mock_location": spoof_info["is_mock_location"],
            "speed_kmh": spoof_info["speed_kmh"],
            "accuracy": location.accuracy or 10.0,
            "provider": location.provider or "gps",
            "city": "Bengaluru",
            "country": "India",
            "address": "Koramangala, Bengaluru, Karnataka"
        }

        cached_locations.insert(0, res_data)
        if len(cached_locations) > 200:
            cached_locations.pop()

        return {
            "status": "success",
            "message": "Location stored successfully",
            "data": res_data
        }
    except Exception as e:
        logger.error(f"Error storing location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/geolocation/current")
@router.get("/api/geo/current")
async def get_live_location(db: Session = Depends(get_db)):
    if cached_locations:
        return {"status": "success", "data": cached_locations[0]}
    
    # Default fallback coordinate (Bengaluru)
    default_loc = {
        "record_id": 1,
        "latitude": 12.9352,
        "longitude": 77.6245,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_spoofed": False,
        "spoof_confidence": "low",
        "spoof_reasons": [],
        "is_mock_location": False,
        "speed_kmh": 0.0,
        "accuracy": 12.5,
        "provider": "gps",
        "city": "Bengaluru",
        "country": "India",
        "address": "Koramangala 5th Block, Bengaluru"
    }
    return {"status": "success", "data": default_loc}

@router.get("/api/v1/geolocation/history")
@router.get("/api/geo/history")
async def get_location_history(limit: int = 100, include_spoofed: bool = True):
    hist = cached_locations
    if not include_spoofed:
        hist = [h for h in hist if not h.get("is_spoofed")]
    return {
        "status": "success",
        "history": hist[:limit],
        "total": len(hist),
        "limit": limit
    }

@router.post("/api/v1/geolocation/nearby")
@router.post("/api/geo/nearby")
async def get_nearby_places(req: NearbyRequest):
    places = [
        {"place_name": "St. John's Hospital", "place_type": "Hospital", "distance_km": 1.2, "latitude": req.latitude + 0.008, "longitude": req.longitude + 0.005},
        {"place_name": "Koramangala Police Station", "place_type": "Police", "distance_km": 0.8, "latitude": req.latitude - 0.004, "longitude": req.longitude + 0.003},
        {"place_name": "Safe Haven Community Hub", "place_type": "SafeZone", "distance_km": 2.1, "latitude": req.latitude + 0.012, "longitude": req.longitude - 0.007},
    ]
    return {
        "status": "success",
        "places": places,
        "count": len(places),
        "location": {"latitude": req.latitude, "longitude": req.longitude, "radius_km": req.radius_km}
    }

@router.get("/api/v1/geolocation/stats")
@router.get("/api/geo/stats")
async def get_spoofing_stats():
    total = len(cached_locations)
    spoofed = sum(1 for c in cached_locations if c.get("is_spoofed"))
    mock_loc = sum(1 for c in cached_locations if c.get("is_mock_location"))
    return {
        "status": "success",
        "stats": {
            "total_locations": total,
            "spoofed_locations": spoofed,
            "mock_location_detected": mock_loc,
            "verified_locations": max(0, total - spoofed),
            "spoofing_percentage": round((spoofed / total * 100), 2) if total > 0 else 0
        }
    }

@router.get("/api/v1/geolocation/check")
@router.get("/api/geo/check")
async def check_spoofing(request: Request, latitude: float, longitude: float):
    loc_data = {
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    prev = cached_locations[0] if cached_locations else None
    result = detect_spoofing(loc_data, prev)
    return {
        "status": "success",
        "is_spoofed": result["is_spoofed"],
        "spoof_confidence": result["spoof_confidence"],
        "spoof_reasons": result["spoof_reasons"],
        "speed_kmh": result["speed_kmh"]
    }

@router.delete("/api/v1/geolocation/history")
@router.delete("/api/geo/history")
async def clear_history():
    global cached_locations
    cached_locations = []
    return {"status": "success", "message": "Location history cleared"}
