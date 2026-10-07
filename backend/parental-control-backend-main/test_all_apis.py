import asyncio
import httpx
import uuid
import json

from app.main import app

BASE_URL = "http://test"

async def test_all_apis():
    print("--- STARTING COMPREHENSIVE API & DB TEST ---")
    
    test_user_id = str(uuid.uuid4())
    test_child_id = str(uuid.uuid4())
    test_email = f"test_{test_user_id[:8]}@example.com"
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=30.0) as client:
        # 0. Register and Login to get Auth Token
        print(f"\n[0] Registering and Logging in...")
        register_payload = {
            "email": test_email,
            "password": "password123",
            "name": f"Test Parent {test_user_id[:6]}"
        }
        await client.post("/api/auth/register", json=register_payload)
        
        login_payload = {
            "email": test_email,
            "password": "password123"
        }
        login_resp = await client.post("/api/auth/login", json=login_payload)
        if login_resp.status_code == 200:
            token = login_resp.json().get("token") or login_resp.json().get("access_token")
            # If the API returns a mock response, it might not have a token. Let's handle both.
            if token:
                client.headers.update({"Authorization": f"Bearer {token}"})
            print(f"[SUCCESS] Registered and logged in successfully! Response: {login_resp.json()}")
        else:
            print(f"[ERROR] Failed to login: {login_resp.text}")
            # If the backend is running in mock mode, it might not require auth, so we continue
            pass

        # 1. Test Child Creation
        print(f"\n[1] Creating a new child profile (Testing Children DB & API)...")
        child_payload = {
            "name": "Test Child",
            "age": 10,
            "device_model": "Test Phone 123",
            "battery_level": 100,
            "linking_code": "TST-123"
        }
        resp = await client.post("/api/child", json=child_payload)
        if resp.status_code in (200, 201):
            print(f"[SUCCESS] Child Profile created successfully! Response: {resp.json()}")
            test_child_id = resp.json().get("id")
        else:
            print(f"[ERROR] Failed to create child: {resp.text}")
            
        # 2. Test Location Tracking Update
        print(f"\n[2] Updating Live Location (Testing Location DB & API)...")
        loc_payload = {
            "child_id": test_child_id,
            "parent_id": test_user_id,
            "other": "test_data",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "current_address": "Test Address Chennai",
            "battery_percentage": 90
        }
        resp = await client.post(f"/api/location/{test_child_id}/live", json=loc_payload)
        if resp.status_code == 200:
            print(f"[SUCCESS] Location updated successfully! Response: {resp.json()}")
        else:
            print(f"[ERROR] Failed to update location: {resp.text}")
            
        # 3. Test Location Retrieval
        print(f"\n[3] Fetching Live Location (Testing Location DB Retrieval)...")
        resp = await client.get(f"/api/location/{test_child_id}/live")
        if resp.status_code == 200:
            print(f"[SUCCESS] Location fetched successfully! Response: {resp.json()}")
        else:
            print(f"[ERROR] Failed to fetch location: {resp.text}")
            
        # 4. Test Geofence Creation
        print(f"\n[4] Creating Geofence (Testing Geofence DB & API)...")
        geo_payload = {
            "name": "School Zone",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_meters": 150.0
        }
        resp = await client.post(f"/api/location/{test_child_id}/geofences", json=geo_payload)
        if resp.status_code in (200, 201):
            print(f"[SUCCESS] Geofence created successfully! Response: {resp.json()}")
        else:
            print(f"[ERROR] Failed to create geofence: {resp.text}")
            
        # 5. Test Filters Update
        print(f"\n[5] Updating Web Filters (Testing Filters DB & API)...")
        filter_payload = {
            "category_name": "Gaming",
            "is_blocked": True
        }
        resp = await client.post(f"/api/filters/{test_child_id}/category", json=filter_payload)
        if resp.status_code == 200:
            print(f"[SUCCESS] Filters updated successfully! Response: {resp.json()}")
        else:
            print(f"[ERROR] Failed to update filters: {resp.text}")
            
        # 6. Test Filters Retrieval
        print(f"\n[6] Fetching Web Filters (Testing Filters DB Retrieval)...")
        try:
            resp = await client.get(f"/api/filters/{test_child_id}/rules", timeout=10.0)
            if resp.status_code == 200:
                print(f"[SUCCESS] Filters fetched successfully! Response: {resp.json()}")
            else:
                print(f"[ERROR] Failed to fetch filters: {resp.text}")
        except httpx.ReadTimeout:
            print(f"[ERROR] Read timeout while fetching filters!")
            
    print("\n--- COMPREHENSIVE TEST COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(test_all_apis())
