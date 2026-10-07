# app/services/geofence_service.py
import math
from typing import List, Dict, Any


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def check_geofence_breaches(child_lat: float, child_lon: float, geofences: List[Dict[str, Any]]) -> List[str]:
    """Returns a list of breached safe zones where child distance exceeds radius."""
    breaches = []
    for fence in geofences:
        center_lat = float(fence["latitude"])
        center_lon = float(fence["longitude"])
        radius = float(fence["radius_meters"])
        name = fence.get("name", "Safe Zone")

        distance = calculate_distance_meters(child_lat, child_lon, center_lat, center_lon)
        if distance > radius:
            breaches.append(name)
    return breaches
