# app/services/osm_service.py
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# OSM policy requires a identifiable User-Agent
USER_AGENT_HEADER = {"User-Agent": "ParentalControlBackend/1.0 (contact@yourdomain.com)"}

# In-memory LRU cache to avoid re-querying identical stationary coordinates
GEOCODE_CACHE: dict[str, str] = {}


async def reverse_geocode_osm(lat: float, lon: float) -> str:
    """
    Converts coordinates into a human-readable street address using OSM Nominatim.
    Rounds coordinates to 4 decimal places (~11 meters) to utilize cache efficiently.
    """
    cache_key = f"{round(lat, 4)},{round(lon, 4)}"
    if cache_key in GEOCODE_CACHE:
        return GEOCODE_CACHE[cache_key]

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "zoom": 18,
                    "addressdetails": 1
                },
                headers=USER_AGENT_HEADER
            )
            
            if response.status_code == 200:
                data = response.json()
                address = data.get("display_name", f"{lat:.4f}, {lon:.4f}")
                
                # Cache up to 1000 lookups
                if len(GEOCODE_CACHE) > 1000:
                    GEOCODE_CACHE.clear()
                GEOCODE_CACHE[cache_key] = address
                return address
            else:
                logger.warning(f"OSM Nominatim returned status {response.status_code}")
                return f"{lat:.4f}, {lon:.4f}"
                
    except Exception as e:
        logger.error(f"OSM Reverse Geocoding error: {e}")
        return f"{lat:.4f}, {lon:.4f}"
