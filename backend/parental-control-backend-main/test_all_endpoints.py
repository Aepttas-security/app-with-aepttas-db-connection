import asyncio
import httpx
import uuid
import json
from app.main import app

BASE_URL = "http://test"

async def test_everything():
    print("==================================================")
    print("    COMPREHENSIVE FULL API ENDPOINT SUITE TEST    ")
    print("==================================================")
    
    try:
        from app.database import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print(f"[INFO] DB table verification notice: {e}")

    
    test_user_id = str(uuid.uuid4())
    test_child_id = str(uuid.uuid4())
    test_email = f"test_{test_user_id[:8]}@example.com"
    
    passed = 0
    failed = 0

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=30.0) as client:

        async def run_test(name, method, url, **kwargs):
            nonlocal passed, failed
            try:
                if method.upper() == "GET":
                    resp = await client.get(url, **kwargs)
                elif method.upper() == "POST":
                    resp = await client.post(url, **kwargs)
                elif method.upper() == "PUT":
                    resp = await client.put(url, **kwargs)
                elif method.upper() == "DELETE":
                    resp = await client.delete(url, **kwargs)
                
                if resp.status_code in (200, 201):
                    print(f"[PASS] {name} -> {resp.status_code}")
                    passed += 1
                else:
                    print(f"[FAIL] {name} -> Status: {resp.status_code}, Body: {resp.text[:150]}")
                    failed += 1
            except Exception as e:
                print(f"[ERR]  {name} -> Exception: {str(e)[:150]}")
                failed += 1

        print("\n--- 1. GENERAL & DOCS ENDPOINTS ---")
        await run_test("Root Index", "GET", "/")
        await run_test("OpenAPI Specification", "GET", "/openapi.json")
        await run_test("Swagger UI Docs", "GET", "/docs")

        print("\n--- 2. AUTH ENDPOINTS ---")
        await run_test("Register User", "POST", "/api/auth/register", json={"email": test_email, "password": "Password123!", "name": "Test Parent"})
        await run_test("Login User", "POST", "/api/auth/login", json={"email": test_email, "password": "Password123!"})
        await run_test("Debug DB Users", "GET", "/api/auth/debug-db-users")

        print("\n--- 3. CHILD PROFILE ENDPOINTS ---")
        await run_test("Create Child Profile", "POST", "/api/child", json={"name": "Alex", "age": 12, "device_model": "iPhone 13", "battery_level": 85, "linking_code": "TST-999"})
        await run_test("Get Children List", "GET", "/api/child")
        await run_test("Generate Linking Code", "POST", f"/api/child/{test_child_id}/generate-code")
        await run_test("Permissions Sync", "POST", f"/api/child/{test_child_id}/permissions-sync", json={"location": True, "screentime": True})

        print("\n--- 4. MAPS & LOCATION ENDPOINTS ---")
        await run_test("Tile Server Configuration", "GET", "/api/location/tile-config")
        await run_test("Child Map Data & Polygons", "GET", f"/api/location/{test_child_id}/map-data")
        await run_test("Live Coordinate Stream", "GET", f"/api/location/{test_child_id}/live")
        await run_test("Post Live Coordinate Ping", "POST", f"/api/location/{test_child_id}/live", json={"child_id": test_child_id, "parent_id": test_user_id, "latitude": 13.0827, "longitude": 80.2707, "current_address": "Greenwood School", "battery_percentage": 88})
        await run_test("Check Geofence Status", "POST", f"/api/location/{test_child_id}/check-geofences", json={"latitude": 13.0827, "longitude": 80.2707})
        await run_test("Request Offline Map Tiles", "POST", f"/api/location/{test_child_id}/offline-tiles", json={"bounds": [[13.0, 80.0], [13.1, 80.1]], "zoom_levels": [10, 11]})
        await run_test("Create Geofence Zone", "POST", f"/api/location/{test_child_id}/geofences", json={"name": "School Safety Perimeter", "latitude": 13.0827, "longitude": 80.2707, "radius_meters": 200.0})
        await run_test("List Active Geofences", "GET", f"/api/location/{test_child_id}/geofences")

        print("\n--- 5. SCREENTIME ENDPOINTS ---")
        await run_test("Screentime Dashboard", "GET", f"/api/screentime/{test_child_id}/dashboard")
        await run_test("Remote Screen Lock", "POST", f"/api/screentime/{test_child_id}/remote-lock", json={"is_locked": True})
        await run_test("Update Daily Limit", "PUT", f"/api/screentime/{test_child_id}/daily-limit", json={"daily_limit_minutes": 180})

        print("\n--- 6. APPLICATION MANAGEMENT ENDPOINTS ---")
        await run_test("Get App Inventory", "GET", f"/api/apps/{test_child_id}")
        await run_test("Get App Rules", "GET", f"/api/apps/{test_child_id}/rules")
        await run_test("Toggle App Block State", "PUT", f"/api/apps/{test_child_id}/toggle-block", json={"app_id": "com.instagram.android", "is_blocked": True})

        print("\n--- 7. WEB & CONTENT FILTERING ENDPOINTS ---")
        await run_test("Get Web Filter Rules", "GET", f"/api/filters/{test_child_id}/rules")
        await run_test("Update Filter Category", "POST", f"/api/filters/{test_child_id}/category", json={"category_name": "Gaming", "is_blocked": True})
        await run_test("Update URL Blacklist", "POST", f"/api/filters/{test_child_id}/blacklist", json={"url": "untrusted-domain.com", "action": "ADD"})

        print("\n--- 8. REPORTS & ANALYTICS ---")
        await run_test("Child Summary Report", "GET", f"/api/reports/{test_child_id}/summary")

        print("\n--- 9. SOS & PAIRING ENDPOINTS ---")
        await run_test("Get Active SOS Alerts", "GET", f"/api/sos/active/{test_child_id}")
        await run_test("Get Active SOS Alerts (Custom ID)", "GET", "/api/sos/active/child_manoj_598")
        await run_test("Get Global SOS Feed", "GET", "/api/sos/feed")
        await run_test("Put SOS Preferences (Custom ID)", "PUT", "/api/sos/preferences/child_manoj_598", json={"sound_alarm": True})
        await run_test("Put SOS Preferences (Root)", "PUT", "/api/sos/preferences/", json={"sound_alarm": True})
        await run_test("Generate Code (Custom String ID)", "POST", "/api/child/child_manoj_598/generate-code")
        await run_test("Generate Code (Empty Path Seg)", "POST", "/api/child/generate-code")
        print("\n--- 10. SCANNER ENDPOINTS ---")
        await run_test("Upload & Scan APK", "POST", "/api/scan")
        await run_test("Get Scans List", "GET", "/api/scans")
        await run_test("Get Quarantine List", "GET", "/api/quarantine")
        await run_test("Get Dashboard Metrics", "GET", "/api/dashboard")
        await run_test("Get Active Alerts", "GET", "/api/alerts")

    print("\n==================================================")
    print(f"   SUMMARY: {passed} PASSED, {failed} FAILED")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_everything())
