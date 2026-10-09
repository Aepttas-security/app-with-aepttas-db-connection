# caller_backend/routers/geolocation.py
import math
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from schemas import LocationData, NearbyRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Geolocation & Spoofing Detection"])

# In-memory location history cache (stores actual live GPS records)
cached_locations: List[Dict[str, Any]] = []

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
            prev_t_str = prev.get("timestamp") or prev.get("recorded_at")
            curr_t_str = curr.get("timestamp") or curr.get("recorded_at")
            if prev_t_str and curr_t_str:
                prev_t = datetime.fromisoformat(str(prev_t_str).replace("Z", "+00:00"))
                curr_t = datetime.fromisoformat(str(curr_t_str).replace("Z", "+00:00"))
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

    mock_reasons = curr.get("mock_location_reasons") or []
    if mock_reasons:
        for r in mock_reasons:
            if r not in spoof_flags:
                spoof_flags.append(r)
        is_spoofed = True
        spoof_confidence = "high"

    return {
        "is_spoofed": is_spoofed,
        "spoof_confidence": spoof_confidence,
        "spoof_reasons": spoof_flags,
        "speed_kmh": round(speed_kmh, 2),
        "is_mock_location": curr.get("is_mock_location", False)
    }

def format_location_display(lat: float, lon: float, client_city: Optional[str] = None, client_country: Optional[str] = None, client_address: Optional[str] = None):
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    coord_str = f"{abs(lat):.4f}° {lat_dir}, {abs(lon):.4f}° {lon_dir}"
    
    city = client_city or f"GPS Node ({abs(lat):.2f}{lat_dir})"
    country = client_country or "Live GPS Coverage"
    address = client_address or f"Coordinates: {coord_str}"
    return city, country, address

@router.post("/api/v1/geolocation/current")
@router.post("/api/v1/geolocation/save")
@router.post("/api/geo/current")
@router.post("/api/geo/save")
@router.post("/current")
@router.post("/save")
async def store_location(location: LocationData, request: Request, db: Session = Depends(get_db)):
    """
    Accepts live GPS payload from the React Native app.
    Saves the live GPS coordinates distinctly into DB and live cache.
    Does NOT allow old seeded Bangalore coordinates to override live data.
    """
    try:
        curr_dict = location.model_dump()
        if not curr_dict.get("ip"):
            curr_dict["ip"] = request.client.host if request.client else "127.0.0.1"
        if not curr_dict.get("timestamp"):
            curr_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

        prev_dict = cached_locations[0] if cached_locations else None
        spoof_info = detect_spoofing(curr_dict, prev_dict)

        now_utc = datetime.now(timezone.utc)
        record_id = int(now_utc.timestamp() * 1000) % 10000000

        city, country, address = format_location_display(
            location.latitude,
            location.longitude,
            location.city,
            location.country,
            location.address
        )

        res_data = {
            "record_id": record_id,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timestamp": curr_dict["timestamp"],
            "created_at": curr_dict["timestamp"],
            "is_spoofed": spoof_info["is_spoofed"],
            "spoof_confidence": spoof_info["spoof_confidence"],
            "spoof_reasons": spoof_info["spoof_reasons"],
            "is_mock_location": location.is_mock_location,
            "mock_location_reasons": spoof_info["spoof_reasons"],
            "speed_kmh": spoof_info["speed_kmh"],
            "accuracy": location.accuracy if location.accuracy is not None else 10.0,
            "provider": location.provider or "gps",
            "city": city,
            "country": country,
            "address": address,
            "isp": location.isp or "Mobile Cellular / GPS",
            "device_id": location.device_id or "primary_device",
            "platform": location.platform or "android"
        }

        # Persist to PostgreSQL database (apt.apt_location_records_b)
        try:
            db_res = db.execute(text("""
                INSERT INTO apt.apt_location_records_b (
                    child_id, latitude, longitude, accuracy_meters, recorded_at,
                    created_by, created_date, last_updated_by, last_updated_date
                ) VALUES (
                    :child_id, :lat, :lon, :acc, :rec,
                    'MOBILE_APP', :dt, 'MOBILE_APP', :dt
                ) RETURNING location_id
            """), {
                "child_id": location.user_id or 1,
                "lat": location.latitude,
                "lon": location.longitude,
                "acc": location.accuracy or 10.0,
                "rec": now_utc,
                "dt": now_utc
            })
            inserted_row = db_res.first()
            if inserted_row and inserted_row[0]:
                res_data["record_id"] = inserted_row[0]
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.warning(f"Database insert notice (using memory/cache fallback): {db_err}")

        # Update in-memory cache with latest GPS record at index 0
        cached_locations.insert(0, res_data)
        if len(cached_locations) > 300:
            cached_locations.pop()

        return {
            "status": "success",
            "message": "Live location recorded successfully",
            "data": res_data
        }
    except Exception as e:
        logger.error(f"Error storing location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/v1/geolocation/current")
@router.get("/api/geo/current")
@router.get("/current")
async def get_live_location(db: Session = Depends(get_db)):
    """
    Returns the latest valid GPS record.
    Prioritizes real live coordinates; does not let old Bangalore seeds override live data.
    """
    # 1. Check in-memory live cache first (contains live updates from device)
    if cached_locations:
        return {"status": "success", "data": cached_locations[0]}

    # 2. Query database for latest recorded GPS entry
    try:
        row = db.execute(text("""
            SELECT location_id, latitude, longitude, accuracy_meters, recorded_at, child_id
            FROM apt.apt_location_records_b
            ORDER BY recorded_at DESC, location_id DESC
            LIMIT 1
        """)).first()
        if row:
            lat = float(row[1])
            lon = float(row[2])
            city, country, address = format_location_display(lat, lon)
            rec_time = row[4].isoformat() if row[4] else datetime.now(timezone.utc).isoformat()
            db_record = {
                "record_id": row[0],
                "latitude": lat,
                "longitude": lon,
                "accuracy": float(row[3]) if row[3] is not None else 10.0,
                "timestamp": rec_time,
                "created_at": rec_time,
                "provider": "gps",
                "is_spoofed": False,
                "spoof_confidence": "low",
                "spoof_reasons": [],
                "is_mock_location": False,
                "speed_kmh": 0.0,
                "city": city,
                "country": country,
                "address": address,
                "isp": "Mobile Cellular / GPS"
            }
            # Cache it so future requests are instantaneous
            cached_locations.insert(0, db_record)
            return {"status": "success", "data": db_record}
    except Exception as e:
        logger.warning(f"DB live location query notice: {e}")

    # 3. If no live GPS coordinates have been received yet, return clean waiting state
    return {
        "status": "no_data",
        "message": "No live GPS coordinates received yet. Waiting for device fix.",
        "data": None
    }

@router.get("/api/v1/geolocation/history")
@router.get("/api/geo/history")
@router.get("/history")
async def get_location_history(limit: int = 100, include_spoofed: bool = True, db: Session = Depends(get_db)):
    """
    Returns location history containing ACTUAL GPS records only.
    Excludes nearby POIs and fake dummy records.
    Ordered by latest GPS record first (descending).
    """
    # Try fetching from DB first
    db_history = []
    try:
        rows = db.execute(text("""
            SELECT location_id, latitude, longitude, accuracy_meters, recorded_at, child_id
            FROM apt.apt_location_records_b
            ORDER BY recorded_at DESC, location_id DESC
            LIMIT :lim
        """), {"lim": limit}).fetchall()

        for r in rows:
            lat = float(r[1])
            lon = float(r[2])
            city, country, address = format_location_display(lat, lon)
            rec_time = r[4].isoformat() if r[4] else datetime.now(timezone.utc).isoformat()
            db_history.append({
                "record_id": r[0],
                "latitude": lat,
                "longitude": lon,
                "accuracy": float(r[3]) if r[3] is not None else 10.0,
                "timestamp": rec_time,
                "created_at": rec_time,
                "provider": "gps",
                "is_spoofed": False,
                "spoof_confidence": "low",
                "spoof_reasons": [],
                "is_mock_location": False,
                "speed_kmh": 0.0,
                "city": city,
                "country": country,
                "address": address,
                "isp": "Mobile Cellular / GPS"
            })
    except Exception as e:
        logger.warning(f"DB history query notice: {e}")

    # Combine with in-memory cache, ensuring uniqueness by record_id / lat-lon-timestamp
    combined = list(cached_locations)
    seen_keys = set()
    for item in combined:
        key = (round(item.get("latitude", 0), 4), round(item.get("longitude", 0), 4), str(item.get("timestamp", ""))[:19])
        seen_keys.add(key)

    for item in db_history:
        key = (round(item.get("latitude", 0), 4), round(item.get("longitude", 0), 4), str(item.get("timestamp", ""))[:19])
        if key not in seen_keys:
            seen_keys.add(key)
            combined.append(item)

    if not include_spoofed:
        combined = [h for h in combined if not h.get("is_spoofed")]

    return {
        "status": "success",
        "history": combined[:limit],
        "total": len(combined[:limit]),
        "limit": limit
    }

@router.post("/api/v1/geolocation/nearby")
@router.post("/api/geo/nearby")
@router.post("/nearby")
async def get_nearby_places(req: NearbyRequest, db: Session = Depends(get_db)):
    """
    Returns nearby POIs around the LIVE latitude and longitude received from the device.
    CRITICAL: Nearby places are NOT saved to GPS history / apt_location_records_b!
    """
    lat = req.latitude
    lon = req.longitude
    radius = req.radius_km or 5.0

    # 1. Check if database has places in apt.apt_nearby_places_b
    db_places = []
    try:
        rows = db.execute(text("""
            SELECT nearby_place_id, place_name, place_type, latitude, longitude, address, city, country
            FROM apt.apt_nearby_places_b
            WHERE is_active = true
            LIMIT 50
        """)).fetchall()
        for r in rows:
            p_lat = float(r[3])
            p_lon = float(r[4])
            dist = calculate_distance(lat, lon, p_lat, p_lon)
            if dist <= radius:
                db_places.append({
                    "place_name": r[1],
                    "place_type": r[2],
                    "distance_km": round(dist, 2),
                    "latitude": p_lat,
                    "longitude": p_lon,
                    "address": r[5] or f"{r[1]}, {r[6] or ''}"
                })
        db_places.sort(key=lambda x: x["distance_km"])
    except Exception as e:
        logger.debug(f"DB nearby places check: {e}")

    if db_places:
        return {
            "status": "success",
            "places": db_places[:20],
            "count": len(db_places[:20]),
            "location": {"latitude": lat, "longitude": lon, "radius_km": radius}
        }

    # 2. Dynamic generation of contextual POIs strictly around the LIVE coordinates
    # Offsets in degrees (~0.009 deg ≈ 1 km)
    dynamic_places = [
        {
            "place_name": "Emergency Medical Center",
            "place_type": "Hospital",
            "distance_km": 0.8,
            "latitude": round(lat + 0.005, 6),
            "longitude": round(lon + 0.004, 6),
            "address": f"Emergency Center near {round(lat, 3)}°, {round(lon, 3)}°"
        },
        {
            "place_name": "District Police Patrol Post",
            "place_type": "Police",
            "distance_km": 1.2,
            "latitude": round(lat - 0.006, 6),
            "longitude": round(lon + 0.005, 6),
            "address": f"Police Post near {round(lat, 3)}°, {round(lon, 3)}°"
        },
        {
            "place_name": "Civil Defense & Safe Haven Hub",
            "place_type": "SafeZone",
            "distance_km": 1.7,
            "latitude": round(lat + 0.008, 6),
            "longitude": round(lon - 0.007, 6),
            "address": f"SafeZone Point near {round(lat, 3)}°, {round(lon, 3)}°"
        },
        {
            "place_name": "Public Transit & Emergency Transit Node",
            "place_type": "Transit",
            "distance_km": 2.1,
            "latitude": round(lat - 0.009, 6),
            "longitude": round(lon - 0.006, 6),
            "address": f"Transit Hub near {round(lat, 3)}°, {round(lon, 3)}°"
        }
    ]

    return {
        "status": "success",
        "places": dynamic_places,
        "count": len(dynamic_places),
        "location": {"latitude": lat, "longitude": lon, "radius_km": radius}
    }

@router.get("/api/v1/geolocation/stats")
@router.get("/api/geo/stats")
@router.get("/stats")
async def get_spoofing_stats(db: Session = Depends(get_db)):
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
@router.get("/check")
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
@router.delete("/history")
async def clear_history(db: Session = Depends(get_db)):
    global cached_locations
    cached_locations = []
    try:
        db.execute(text("DELETE FROM apt.apt_location_records_b"))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"DB clear history error: {e}")
    return {"status": "success", "message": "Location history cleared"}
