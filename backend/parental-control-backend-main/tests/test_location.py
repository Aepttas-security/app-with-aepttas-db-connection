# tests/test_location.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child
from app.routers.location import calculate_haversine_meters
from app.services.geofence_service import calculate_distance_meters, check_geofence_breaches
from app.services.osm_service import reverse_geocode_osm, GEOCODE_CACHE


def test_haversine_formula_correctness():
    """AAA Pattern: Unit Test for Haversine Distance Calculation."""
    # Arrange - Distance between New York (40.7128, -74.0060) and Boston (42.3601, -71.0589) ~ 306 km
    ny_lat, ny_lng = 40.7128, -74.0060
    bos_lat, bos_lng = 42.3601, -71.0589

    # Act
    dist_meters = calculate_haversine_meters(ny_lat, ny_lng, bos_lat, bos_lng)

    # Assert
    assert 300000 < dist_meters < 320000  # Between 300km and 320km


def test_geofence_service_distance_and_breach_detection():
    """AAA Pattern: Unit Test for Geofence Service Breach Calculations."""
    # Arrange - Child is at 13.0850, 80.2750 (Center is 13.0827, 80.2707, radius 200m)
    child_lat, child_lon = 13.0850, 80.2750
    fences = [
        {"name": "School Zone", "latitude": 13.0827, "longitude": 80.2707, "radius_meters": 200.0},
        {"name": "City Wide Zone", "latitude": 13.0827, "longitude": 80.2707, "radius_meters": 5000.0}
    ]

    # Act
    dist = calculate_distance_meters(13.0827, 80.2707, child_lat, child_lon)
    breaches = check_geofence_breaches(child_lat, child_lon, fences)

    # Assert
    assert dist > 200.0
    assert "School Zone" in breaches
    assert "City Wide Zone" not in breaches


@pytest.mark.asyncio
async def test_osm_reverse_geocoding_lru_cache():
    """AAA Pattern: Unit Test for OSM Reverse Geocoding Cache."""
    # Arrange
    lat, lon = 37.7749, -122.4194
    cache_key = f"{round(lat, 4)},{round(lon, 4)}"
    GEOCODE_CACHE[cache_key] = "Market St, San Francisco, CA"

    # Act
    addr = await reverse_geocode_osm(lat, lon)

    # Assert
    assert addr == "Market St, San Francisco, CA"


@pytest.mark.asyncio
async def test_should_process_location_ping_and_evaluate_geofence(
    async_client: AsyncClient,
    test_child_profile: Child
):
    """AAA Pattern: Telemetry Location Ping Processing."""
    # Arrange
    payload = {
        "child_id": str(test_child_profile.child_id),
        "latitude": 37.7749,
        "longitude": -122.4194,
        "current_address": "Market St, San Francisco, CA",
        "battery_percentage": 92
    }

    # Act
    response = await async_client.post(
        f"/api/location/{test_child_profile.child_id}/live",
        json=payload
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "geofence_evaluation" in data


@pytest.mark.asyncio
async def test_should_ingest_location_telemetry_with_osm_resolution(
    async_client: AsyncClient,
    test_child_profile: Child
):
    """AAA Pattern: Location Telemetry Ingestion Endpoint."""
    # Arrange
    payload = {
        "child_id": str(test_child_profile.child_id),
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy_meters": 5.0,
        "battery_percentage": 95
    }

    # Act
    response = await async_client.post(
        "/api/location/telemetry",
        json=payload
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "address" in data
    assert "breaches" in data


@pytest.mark.asyncio
async def test_should_fetch_latest_and_history_location_breadcrumbs(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Fetch Latest Location & Location History Breadcrumbs."""
    # Act - Latest
    latest_res = await async_client.get(
        f"/api/location/{test_child_profile.child_id}/latest",
        headers=auth_headers
    )
    assert latest_res.status_code == 200
    assert "latitude" in latest_res.json()

    # Act - History
    history_res = await async_client.get(
        f"/api/location/{test_child_profile.child_id}/history",
        headers=auth_headers
    )
    assert history_res.status_code == 200
    assert "trail" in history_res.json()


@pytest.mark.asyncio
async def test_should_fetch_child_live_location_for_parent(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Dashboard Fetches Live Location."""
    # Act
    response = await async_client.get(
        f"/api/location/{test_child_profile.child_id}/live",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["child_id"] == str(test_child_profile.child_id)


@pytest.mark.asyncio
async def test_should_create_geofence_safe_zone(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Creates Geofence Boundary."""
    # Arrange
    payload = {
        "name": "School Safe Zone",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius_meters": 500.0
    }

    # Act
    response = await async_client.post(
        f"/api/location/{test_child_profile.child_id}/geofences",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["geofence_details"]["name"] == "School Safe Zone"


@pytest.mark.asyncio
async def test_should_list_active_geofences_for_child(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: List Geofence Zones."""
    # Act
    response = await async_client.get(
        f"/api/location/{test_child_profile.child_id}/geofences",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_should_fetch_tile_server_config(async_client: AsyncClient):
    """AAA Pattern: OpenStreetMap Tile Server Config."""
    # Act
    response = await async_client.get("/api/location/tile-config")

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "tile_server_url" in response.json()
