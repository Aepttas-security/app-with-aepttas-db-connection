# app/services/map_service.py
import math
from typing import List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import uuid

class OpenStreetMapService:
    """Service for OpenStreetMap integration and geofence visualization"""
    
    @staticmethod
    def generate_geofence_polygon(
        center_lat: float,
        center_lon: float,
        radius_meters: float,
        points: int = 36
    ) -> List[Tuple[float, float]]:
        """
        Generate circle polygon points for geofence visualization
        Returns list of (latitude, longitude) pairs
        """
        R = 6371000.0  # Earth radius in meters
        polygon = []
        
        for i in range(points):
            bearing = (2 * math.pi * i) / points
            
            lat1 = math.radians(center_lat)
            lon1 = math.radians(center_lon)
            
            lat2 = math.asin(
                math.sin(lat1) * math.cos(radius_meters / R) +
                math.cos(lat1) * math.sin(radius_meters / R) * math.cos(bearing)
            )
            
            lon2 = lon1 + math.atan2(
                math.sin(bearing) * math.sin(radius_meters / R) * math.cos(lat1),
                math.cos(radius_meters / R) - math.sin(lat1) * math.sin(lat2)
            )
            
            polygon.append((
                math.degrees(lat2),
                math.degrees(lon2)
            ))
        
        return polygon
    
    @staticmethod
    def get_tile_urls() -> Dict[str, str]:
        """Returns OpenStreetMap tile server URLs"""
        return {
            "default": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "carto_light": "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
            "carto_dark": "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png",
            "satellite": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        }
    
    @staticmethod
    async def get_geofences_with_polygons(
        child_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch geofences and add polygon data for map visualization
        """
        try:
            # Query geofences from database
            try:
                query = text("""
                    SELECT 
                        geofence_uuid as id,
                        fence_name as name,
                        center_latitude as latitude,
                        center_longitude as longitude,
                        radius_meters
                    FROM apt_geofence_b
                    WHERE child_uuid = :child_id
                """)
                result = await db.execute(query, {"child_id": str(child_id)})
            except Exception:
                await db.rollback()
                query = text("""
                    SELECT 
                        geofence_uuid as id,
                        fence_name as name,
                        center_latitude as latitude,
                        center_longitude as longitude,
                        radius_meters
                    FROM apt_geofence_b
                    WHERE child_id = :child_id
                """)
                result = await db.execute(query, {"child_id": str(child_id)})
            
            rows = result.fetchall()
            
            geofences = []
            for row in rows:
                polygon = OpenStreetMapService.generate_geofence_polygon(
                    float(row.latitude),
                    float(row.longitude),
                    float(row.radius_meters)
                )
                
                geofences.append({
                    "id": str(row.id),
                    "name": row.name,
                    "latitude": float(row.latitude),
                    "longitude": float(row.longitude),
                    "radius_meters": float(row.radius_meters),
                    "polygon": polygon,  # List of [lat, lon] pairs
                    "center": [float(row.latitude), float(row.longitude)]
                })
            
            return geofences
            
        except Exception as e:
            print(f"[WARN] Failed to fetch geofences: {str(e)}")
            return []
    
    @staticmethod
    def format_location_for_map(
        latitude: float,
        longitude: float,
        geofences: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Format location data for map display including geofence polygons
        """
        result = {
            "position": {
                "latitude": latitude,
                "longitude": longitude
            },
            "geofences": geofences or []
        }
        return result
