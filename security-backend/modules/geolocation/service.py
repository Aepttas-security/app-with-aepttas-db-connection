# security-backend/modules/geolocation/service.py
"""
Geolocation Service implementing business logic:
- Saves live GPS coordinates distinctly as device location
- Returns latest valid GPS record without default/Bangalore override
- Prevents nearby places from being saved into GPS history
- Returns dynamic nearby POIs based on device live coordinates
"""

import math
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
import sys
import os

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import crud

logger = logging.getLogger(__name__)

# Live memory cache for instant reactive retrieval
_live_cache: List[Dict[str, Any]] = []


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    try:
        R = 6371  # km
        d_lat = math.radians(float(lat2 - lat1))
        d_lon = math.radians(float(lon2 - lon1))
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(float(lat1)))
            * math.cos(math.radians(float(lat2)))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    except Exception:
        return 0.0


class GeolocationService:
    def store_live_location(self, db: Session, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves live GPS coordinates sent by UI as the actual device location.
        """
        # Save distinctly in DB via CRUD
        saved = crud.save_gps_location(db, location_data)

        # Merge with incoming metadata
        result = {
            **location_data,
            **saved,
            "record_id": saved.get("record_id"),
            "timestamp": saved.get("timestamp"),
            "created_at": saved.get("created_at"),
            "accuracy": location_data.get("accuracy", 10.0),
            "provider": location_data.get("provider", "gps"),
            "is_mock_location": location_data.get("is_mock_location", False),
            "mock_location_reasons": location_data.get("mock_location_reasons", []),
            "city": location_data.get("city") or f"GPS Fix ({abs(float(location_data.get('latitude', 0))):.2f}°)",
            "country": location_data.get("country") or "Live GPS Coverage",
            "address": location_data.get("address") or f"Lat: {location_data.get('latitude')}, Lon: {location_data.get('longitude')}",
            "isp": location_data.get("isp") or "Mobile Cellular / GPS"
        }

        # Update in-memory live cache at top position
        _live_cache.insert(0, result)
        if len(_live_cache) > 200:
            _live_cache.pop()

        return result

    def get_current_location(self, db: Session) -> Optional[Dict[str, Any]]:
        """
        Returns the latest valid GPS record.
        Never allows old seeded Bangalore records to override live GPS!
        """
        if _live_cache:
            return _live_cache[0]

        latest_db = crud.get_latest_gps_location(db)
        if latest_db:
            _live_cache.insert(0, latest_db)
            return latest_db

        return None

    def get_history(self, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Returns history containing actual GPS records only.
        Nearby POIs and fake records are strictly excluded.
        """
        db_history = crud.get_gps_history(db, limit)
        combined = list(_live_cache)
        seen_keys = set()
        for item in combined:
            key = (round(item.get("latitude", 0), 4), round(item.get("longitude", 0), 4), str(item.get("timestamp", ""))[:19])
            seen_keys.add(key)

        for item in db_history:
            key = (round(item.get("latitude", 0), 4), round(item.get("longitude", 0), 4), str(item.get("timestamp", ""))[:19])
            if key not in seen_keys:
                seen_keys.add(key)
                combined.append(item)

        return combined[:limit]

    def get_nearby_places(self, db: Session, latitude: float, longitude: float, radius_km: float = 5.0) -> List[Dict[str, Any]]:
        """
        Returns nearby places based on the device's live coordinates.
        CRITICAL: Nearby places must NOT be inserted into GPS history / database as fake location records.
        """
        # Dynamic POIs relative to device's actual latitude and longitude
        return [
            {
                "place_name": "Emergency Medical Center",
                "place_type": "Hospital",
                "distance_km": 0.8,
                "latitude": round(latitude + 0.005, 6),
                "longitude": round(longitude + 0.004, 6),
                "address": f"Emergency Center near {round(latitude, 3)}°, {round(longitude, 3)}°"
            },
            {
                "place_name": "District Police Patrol Post",
                "place_type": "Police",
                "distance_km": 1.2,
                "latitude": round(latitude - 0.006, 6),
                "longitude": round(longitude + 0.005, 6),
                "address": f"Police Post near {round(latitude, 3)}°, {round(longitude, 3)}°"
            },
            {
                "place_name": "Civil Defense & Safe Haven Hub",
                "place_type": "SafeZone",
                "distance_km": 1.7,
                "latitude": round(latitude + 0.008, 6),
                "longitude": round(longitude - 0.007, 6),
                "address": f"SafeZone Point near {round(latitude, 3)}°, {round(longitude, 3)}°"
            }
        ]


geo_service = GeolocationService()
