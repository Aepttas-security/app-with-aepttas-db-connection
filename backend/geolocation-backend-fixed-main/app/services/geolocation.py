# services/geolocation.py
"""Geolocation service with PostgreSQL persistence.

Provides methods to store location records, retrieve the latest location,
fetch location history, get nearby places from the `apt.apt_nearby_places_b`
table, and compute spoofing statistics.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import GeolocationScan, NearbyPlace

logger = logging.getLogger(__name__)


class GeolocationService:
    def __init__(self) -> None:
        # No in‑memory state required – all data is persisted in PostgreSQL.
        pass

    # ---------------------------------------------------------------------
    # Spoofing detection (unchanged logic)
    # ---------------------------------------------------------------------
    def detect_spoofing(self, current_location: Dict, previous_location: Optional[Dict] = None) -> Dict:
        """Detect GPS spoofing using multiple heuristics.

        Returns a dictionary containing:
        * is_spoofed (bool)
        * spoof_confidence (low/medium/high)
        * spoof_reasons (list)
        * speed_kmh (float)
        * is_mock_location (bool)
        * detection_methods_used (int)
        """
        spoof_flags: List[str] = []
        spoof_confidence = "low"
        is_spoofed = False
        speed_kmh = 0.0

        # Method 1 – mock location flag
        if current_location.get("is_mock_location", False):
            is_spoofed = True
            spoof_confidence = "high"
            spoof_flags.append("Mock location app detected on device")

        # Method 2 – impossible speed
        if previous_location:
            try:
                distance = self._calculate_distance(
                    previous_location.get("latitude", 0),
                    previous_location.get("longitude", 0),
                    current_location.get("latitude", 0),
                    current_location.get("longitude", 0),
                )
                prev_time_str = previous_location.get("timestamp", datetime.now(timezone.utc).isoformat())
                curr_time_str = current_location.get("timestamp", datetime.now(timezone.utc).isoformat())
                prev_time = datetime.fromisoformat(prev_time_str.replace("Z", "+00:00"))
                curr_time = datetime.fromisoformat(curr_time_str.replace("Z", "+00:00"))
                time_diff = abs((curr_time - prev_time).total_seconds()) / 3600  # hours
                if time_diff > 0:
                    speed_kmh = distance / time_diff
                    if speed_kmh > 900:
                        is_spoofed = True
                        spoof_confidence = "high"
                        spoof_flags.append(f"Impossible speed: {round(speed_kmh)} km/h")
                    elif speed_kmh > 500:
                        is_spoofed = True
                        spoof_confidence = "medium"
                        spoof_flags.append(f"Suspicious speed: {round(speed_kmh)} km/h")
                    elif speed_kmh > 200:
                        if not is_spoofed:
                            is_spoofed = True
                            spoof_confidence = "low"
                            spoof_flags.append(f"Unusual speed: {round(speed_kmh)} km/h")
            except Exception as e:
                logger.error(f"Error calculating speed: {e}")

        # Method 3 – impossible geographical jump
        if previous_location:
            try:
                distance = self._calculate_distance(
                    previous_location.get("latitude", 0),
                    previous_location.get("longitude", 0),
                    current_location.get("latitude", 0),
                    current_location.get("longitude", 0),
                )
                if distance > 1000:
                    is_spoofed = True
                    spoof_confidence = "high"
                    spoof_flags.append(f"Impossible geographical jump: {round(distance)} km")
            except Exception as e:
                logger.error(f"Error checking geographical jump: {e}")

        # Method 4 – invalid coordinates
        lat = current_location.get("latitude", 0)
        lon = current_location.get("longitude", 0)
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            is_spoofed = True
            spoof_confidence = "medium"
            spoof_flags.append("Invalid coordinates detected")

        # Method 5 – unrealistic accuracy
        accuracy = current_location.get("accuracy", 0)
        if accuracy and accuracy > 1000:
            if not is_spoofed:
                is_spoofed = True
                spoof_confidence = "medium"
            spoof_flags.append(f"Suspicious GPS accuracy: {round(accuracy)} meters")

        return {
            "is_spoofed": is_spoofed,
            "spoof_confidence": spoof_confidence,
            "spoof_reasons": spoof_flags,
            "speed_kmh": speed_kmh,
            "is_mock_location": current_location.get("is_mock_location", False),
            "detection_methods_used": len(spoof_flags),
        }

    # ---------------------------------------------------------------------
    # Helper distance calculation (Haversine)
    # ---------------------------------------------------------------------
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0.0

    # ---------------------------------------------------------------------
    # Persistence helpers
    # ---------------------------------------------------------------------
    def store_location(self, db: Session, location_data: Dict) -> Dict:
        """Persist a location record and return a lightweight response.

        Steps:
        1. Ensure a timestamp exists.
        2. Retrieve the most recent record for spoofing comparison.
        3. Run spoofing detection.
        4. Insert a new ``GeolocationScan`` row.
        5. Commit and return selected fields for the frontend.
        """
        try:
            if "timestamp" not in location_data:
                location_data["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Fetch previous record for spoofing comparison
            previous = (
                db.query(GeolocationScan)
                .order_by(desc(GeolocationScan.location_record_id))
                .limit(1)
                .first()
            )
            previous_dict = None
            if previous:
                previous_dict = {
                    "latitude": previous.latitude,
                    "longitude": previous.longitude,
                    "timestamp": previous.gps_timestamp.isoformat() if previous.gps_timestamp else None,
                }

            spoofing_results = self.detect_spoofing(location_data, previous_dict)

            # Build ORM object – map only columns defined in the DDL
            scan = GeolocationScan(
                device_id=location_data.get("device_id"),
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude"),
                accuracy=location_data.get("accuracy"),
                speed_kmh=location_data.get("speed_kmh"),
                provider=location_data.get("provider"),
                platform=location_data.get("platform", "").lower() if location_data.get("platform") else None,
                app_version=location_data.get("app_version"),
                city=location_data.get("city"),
                country=location_data.get("country"),
                address=location_data.get("address"),
                gps_timestamp=location_data.get("timestamp"),
                is_spoofed=spoofing_results["is_spoofed"],
                spoof_confidence=spoofing_results["spoof_confidence"],
                spoof_reasons=spoofing_results["spoof_reasons"],
                raw_provider_flags=location_data.get("raw_provider_flags"),
                user_id=location_data.get("user_id"),
                program_id=location_data.get("program_id"),
                attributes=location_data.get("attributes", {}),
                is_active=True,
                created_by=location_data.get("created_by", "system"),
            )
            db.add(scan)
            db.commit()
            db.refresh(scan)

            return {
                "latitude": scan.latitude,
                "longitude": scan.longitude,
                "timestamp": scan.gps_timestamp,
                "is_spoofed": scan.is_spoofed,
                "spoof_confidence": scan.spoof_confidence,
                "spoof_reasons": scan.spoof_reasons,
                "is_mock_location": location_data.get("is_mock_location", False),
                "speed_kmh": scan.speed_kmh,
                "record_id": scan.location_record_id,
            }
        except Exception as e:
            logger.error(f"Error storing location: {e}")
            raise

    def get_live_location(self, db: Session) -> Optional[Dict]:
        """Return the most recent location record, or ``None`` if none exist."""
        record = (
            db.query(GeolocationScan)
            .order_by(desc(GeolocationScan.location_record_id))
            .limit(1)
            .first()
        )
        if not record:
            return None
        return {
            "latitude": record.latitude,
            "longitude": record.longitude,
            "timestamp": record.gps_timestamp,
            "is_spoofed": record.is_spoofed,
            "spoof_confidence": record.spoof_confidence,
            "spoof_reasons": record.spoof_reasons,
            "is_mock_location": getattr(record, "is_mock_location", False),
            "speed_kmh": record.speed_kmh,
            "record_id": record.location_record_id,
            "accuracy": record.accuracy,
            "provider": record.provider,
            "ip": getattr(record, "ip", None),
            "city": record.city,
            "country": record.country,
            "isp": getattr(record, "isp", None),
        }

    def get_history(self, db: Session, limit: int = 100, include_spoofed: bool = True) -> List[Dict]:
        """Return recent location records respecting the ``include_spoofed`` flag.

        The DDL does not contain a ``threat_level`` column, so that filter is omitted.
        """
        query = db.query(GeolocationScan).order_by(desc(GeolocationScan.location_record_id)).limit(limit)
        if not include_spoofed:
            query = query.filter(GeolocationScan.is_spoofed == False)  # noqa: E712
        rows = query.all()
        history: List[Dict] = []
        for r in rows:
            history.append(
                {
                    "record_id": r.location_record_id,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "timestamp": r.gps_timestamp,
                    "is_spoofed": r.is_spoofed,
                    "spoof_confidence": r.spoof_confidence,
                    "spoof_reasons": r.spoof_reasons,
                    "is_mock_location": getattr(r, "is_mock_location", False),
                    "speed_kmh": r.speed_kmh,
                    "accuracy": r.accuracy,
                    "provider": r.provider,
                    "city": r.city,
                    "country": r.country,
                    "ip": getattr(r, "ip", None),
                    "isp": getattr(r, "isp", None),
                }
            )
        return history

    def get_nearby_places(self, db: Session, latitude: float, longitude: float, radius_km: float = 5) -> List[Dict]:
        """Fetch nearby places from ``apt.apt_nearby_places_b``.

        Loads all rows, computes haversine distance, and returns up to 20 places
        within the requested radius, ordered by distance.
        """
        places: List[Dict] = []
        all_places: List[NearbyPlace] = db.query(NearbyPlace).all()
        for p in all_places:
            dist = self._calculate_distance(latitude, longitude, p.latitude, p.longitude)
            if dist <= radius_km:
                places.append(
                    {
                        "place_name": p.place_name,
                        "place_type": p.place_type,
                        "distance_km": round(dist, 2),
                        "latitude": p.latitude,
                        "longitude": p.longitude,
                        "attributes": p.attributes,
                    }
                )
        places.sort(key=lambda x: x["distance_km"])
        return places[:20]

    def get_spoofing_stats(self, db: Session) -> Dict:
        """Calculate simple spoofing statistics from persisted records."""
        total = db.query(func.count(GeolocationScan.location_record_id)).scalar() or 0
        if total == 0:
            return {
                "total_locations": 0,
                "spoofed_locations": 0,
                "mock_location_detected": 0,
                "verified_locations": 0,
                "spoofing_percentage": 0,
            }
        spoofed = (
            db.query(func.count(GeolocationScan.location_record_id))
            .filter(GeolocationScan.is_spoofed == True)  # noqa: E712
            .scalar()
        )
        mock_loc = (
            db.query(func.count(GeolocationScan.location_record_id))
            .filter(getattr(GeolocationScan, "is_mock_location", False) == True)  # type: ignore
            .scalar()
        )
        return {
            "total_locations": total,
            "spoofed_locations": spoofed or 0,
            "mock_location_detected": mock_loc or 0,
            "verified_locations": total - (spoofed or 0),
            "spoofing_percentage": round(((spoofed or 0) / total) * 100, 2) if total else 0,
        }

# Export a singleton instance for router imports.
geo_service = GeolocationService()