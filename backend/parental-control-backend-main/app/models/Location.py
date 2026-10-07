# app/models/Location.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class GeofenceCreateRequest(BaseModel):
    name: str = Field(..., example="School Zone")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(..., ge=50.0, le=5000.0, description="Radius boundary between 50m and 5km.")

class GeofenceZoneResponse(BaseModel):
    zone_id: int
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    is_active: bool

class LocationTrackingResponse(BaseModel):
    child_id: str
    parent_id: str
    other: str = None
    latitude: float
    longitude: float
    last_updated: str
    battery_percentage: int
    current_address: str

class MapDataResponse(BaseModel):
    status: str
    child_id: str
    current_location: Dict[str, Any]
    geofences: List[Dict[str, Any]]
    tile_servers: Dict[str, str]
    map_config: Dict[str, Any]

class GeofenceCheckRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class GeofenceCheckResponse(BaseModel):
    status: str
    child_id: str
    checked_coordinates: Dict[str, float]
    geofences_checked: int
    violations: List[Dict[str, Any]]
    is_safe: bool

class TileConfigResponse(BaseModel):
    status: str
    tile_servers: Dict[str, str]
    attribution: str
    default_server: str

class OfflineTileRequest(BaseModel):
    bounds: List[List[float]] = Field(..., description="[[min_lat, min_lon], [max_lat, max_lon]]")
    zoom_levels: List[int] = Field(default=[10, 11, 12, 13, 14, 15])

class OfflineTileResponse(BaseModel):
    status: str
    child_id: str
    total_tiles: int
    tiles: List[Dict[str, Any]]
    message: str

# Simulation tracking databases
MOCK_LOCATION_DB: Dict[int, dict] = {
    1: {  # Alex
        "latitude": 12.9716,
        "longitude": 77.5946,
        "last_updated": "Just now",
        "battery_percentage": 84,
        "current_address": "Nexus Mall, Block 4, Koramangala"
    },
    2: {  # Emma
        "latitude": 12.9279,
        "longitude": 77.6271,
        "last_updated": "2 mins ago",
        "battery_percentage": 42,
        "current_address": "Greenwood High School Campus"
    }
}

MOCK_GEOFENCES_DB: Dict[int, List[dict]] = {
    1: [
        {"zone_id": 101, "name": "Home Base", "latitude": 12.9716, "longitude": 77.5946, "radius_meters": 150.0, "is_active": True},
        {"zone_id": 102, "name": "Tuition Center", "latitude": 12.9801, "longitude": 77.6012, "radius_meters": 200.0, "is_active": True}
    ],
    2: [
        {"zone_id": 201, "name": "School Zone", "latitude": 12.9279, "longitude": 77.6271, "radius_meters": 300.0, "is_active": True}
    ]
}
GEOFENCE_ID_COUNTER = 300