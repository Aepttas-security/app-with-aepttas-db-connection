import time
from fastapi.testclient import TestClient

def test_geolocation_scan_pass(client: TestClient):
    response = client.post(
        "/api/geolocation/verify?device_id=device-alpha",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "accuracy": 10.0,
            "ip_address": "103.86.176.1", # Chennai IP
            "mock_location_detected": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-alpha"
    assert data["spoof_detected"] is False
    assert data["reason"] is None
    assert data["distance_km"] is not None
    assert data["distance_km"] < 1.0  # Mapped coordinates match GPS exactly

    # Verify retrieval via history endpoint
    history_resp = client.get("/api/geolocation/history?device_id=device-alpha")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data) == 1
    assert history_data[0]["spoof_detected"] is False

def test_geolocation_scan_mock_location(client: TestClient):
    response = client.post(
        "/api/geolocation/verify?device_id=device-beta",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "accuracy": 15.0,
            "ip_address": "103.86.176.1",
            "mock_location_detected": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spoof_detected"] is True
    assert "Mock location" in data["reason"]

def test_geolocation_scan_ip_mismatch(client: TestClient):
    # GPS reports Bengaluru, but IP reports Chennai
    response = client.post(
        "/api/geolocation/verify?device_id=device-gamma",
        json={
            "latitude": 12.9716, # Bengaluru GPS
            "longitude": 77.5946,
            "accuracy": 8.0,
            "ip_address": "103.86.176.1", # Chennai IP
            "mock_location_detected": False
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["spoof_detected"] is True
    assert "mismatch" in data["reason"]
    assert data["distance_km"] > 200.0  # Approx 290 km

def test_geolocation_scan_impossible_speed(client: TestClient):
    # First ping: Chennai GPS with Chennai IP (passes check)
    response1 = client.post(
        "/api/geolocation/verify?device_id=device-delta",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "accuracy": 5.0,
            "ip_address": "103.86.176.1",
            "mock_location_detected": False
        }
    )
    assert response1.status_code == 200
    assert response1.json()["spoof_detected"] is False

    # Second ping: Bengaluru GPS but no IP address (to avoid triggering IP mismatch)
    # The physical distance is ~290 km, and done immediately (0-1 seconds delta)
    response2 = client.post(
        "/api/geolocation/verify?device_id=device-delta",
        json={
            "latitude": 12.9716, # Bengaluru
            "longitude": 77.5946,
            "accuracy": 5.0,
            "ip_address": None,
            "mock_location_detected": False
        }
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["spoof_detected"] is True
    assert "Impossible travel speed" in data2["reason"]

def test_geolocation_history_not_found(client: TestClient):
    # Missing device_id parameter
    response = client.get("/api/geolocation/history")
    assert response.status_code == 400

    # Nonexistent device ID history should be empty list
    response2 = client.get("/api/geolocation/history?device_id=device-nonexistent")
    assert response2.status_code == 200
    assert response2.json() == []

def test_save_and_get_current_location(client: TestClient):
    # Save a location (Chennai)
    response = client.post(
        "/api/geolocation/save?device_id=device-test-loc",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "accuracy": 10.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-test-loc"
    assert data["city"] == "Chennai"
    assert data["country"] == "India"
    assert data["address"] is not None

    # Get current location
    response_curr = client.get("/api/geolocation/current?device_id=device-test-loc")
    assert response_curr.status_code == 200
    data_curr = response_curr.json()
    assert data_curr["city"] == "Chennai"

    # Get location history
    response_hist = client.get("/api/geolocation/location-history?device_id=device-test-loc")
    assert response_hist.status_code == 200
    data_hist = response_hist.json()
    assert len(data_hist) == 1
    assert data_hist[0]["city"] == "Chennai"

def test_current_location_not_found(client: TestClient):
    response = client.get("/api/geolocation/current?device_id=nonexistent-device")
    assert response.status_code == 404

def test_nearby_places_search(client: TestClient):
    # Search nearby places in Chennai (within 15km)
    response = client.post(
        "/api/geolocation/nearby?device_id=device-nearby-test",
        json={
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_km": 15.0
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert data["radius_km"] == 15.0
    assert len(data["places"]) > 0
    # Ensure it contains a place like "Chennai Central Railway Station"
    place_names = [p["place_name"] for p in data["places"]]
    assert "Chennai Central Railway Station" in place_names

