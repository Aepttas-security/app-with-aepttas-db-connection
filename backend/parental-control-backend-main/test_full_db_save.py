import asyncio
import httpx
import uuid
import random

async def test_full_parental_control_storage():
    print("==================================================")
    print("  TESTING FULL PARENTAL CONTROL DB PERSISTENCE   ")
    print("==================================================")

    unique_suffix = uuid.uuid4().hex[:6]
    test_user_email = f"parent_db_{unique_suffix}@example.com"
    test_child_name = f"Child_DB_{unique_suffix}"
    
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=15.0) as client:
        # 1. Register Parent User
        print("\n1. Registering parent account...")
        reg_resp = await client.post("/api/auth/register", json={
            "email": test_user_email,
            "password": "Password123!",
            "name": f"Parent {unique_suffix}"
        })
        assert reg_resp.status_code == 201
        p_user_id = reg_resp.json()["user_id"]
        print(f"   [SUCCESS] Registered Parent ID: {p_user_id}")

        # 2. Login Parent User
        print("\n2. Logging in parent account...")
        login_resp = await client.post("/api/auth/login", json={
            "email": test_user_email,
            "password": "Password123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"   [SUCCESS] Acquired Bearer Token: {token[:20]}...")

        # 3. Create Child Profile
        print("\n3. Creating child profile...")
        create_child_resp = await client.post("/api/child", json={
            "name": test_child_name,
            "age": 12,
            "linking_code": f"{random.randint(100,899)}-{random.randint(100,899)}"
        }, headers=headers)
        assert create_child_resp.status_code == 201
        child_id = create_child_resp.json()["id"]
        print(f"   [SUCCESS] Created Child Profile with UUID: {child_id}")

        # 4. List Children Profiles
        print("\n4. Fetching children list from DB...")
        list_child_resp = await client.get("/api/child", headers=headers)
        assert list_child_resp.status_code == 200
        children = list_child_resp.json()
        assert any(c["name"] == test_child_name for c in children)
        print(f"   [SUCCESS] Verified child in DB list. Total children count: {len(children)}")

        # 5. Set Daily Screentime Limit
        print("\n5. Updating daily screen time limit...")
        st_resp = await client.put(f"/api/screentime/{child_id}/daily-limit", json={
            "daily_limit_minutes": 180
        }, headers=headers)
        assert st_resp.status_code == 200
        print(f"   [SUCCESS] Screentime limit saved to DB: {st_resp.json()}")

        # 6. Remote Device Lock
        print("\n6. Setting remote device lock state...")
        lock_resp = await client.post(f"/api/screentime/{child_id}/remote-lock", json={
            "is_locked": True
        }, headers=headers)
        assert lock_resp.status_code == 200
        print(f"   [SUCCESS] Remote lock state saved to DB: {lock_resp.json()}")

        # 7. Add Installed App & Toggle Restriction
        print("\n7. Adding new app and toggling lock state...")
        add_app_resp = await client.post(f"/api/apps/{child_id}/new-install-alert", json={
            "package_name": "com.roblox.client",
            "app_name": "Roblox",
            "category": "Games"
        }, headers=headers)
        assert add_app_resp.status_code == 201
        print(f"   [SUCCESS] New app install alert saved to DB: {add_app_resp.json()}")

        toggle_app_resp = await client.post(f"/api/apps/{child_id}/toggle/1", json={
            "is_blocked": True
        }, headers=headers)
        assert toggle_app_resp.status_code == 200
        print(f"   [SUCCESS] App restriction toggle saved to DB: {toggle_app_resp.json()}")

        # 8. Filter Category Toggle
        print("\n8. Toggling web filter category...")
        cat_resp = await client.post(f"/api/filters/{child_id}/category", json={
            "category_name": "Adult Content",
            "is_blocked": True
        }, headers=headers)
        assert cat_resp.status_code == 200
        print(f"   [SUCCESS] Web filter category rule saved to DB: {cat_resp.json()}")

        # 9. Blacklist URL
        print("\n9. Blacklisting explicit URL...")
        url_resp = await client.post(f"/api/filters/{child_id}/blacklist", json={
            "url": "example-malicious-site.com"
        }, headers=headers)
        assert url_resp.status_code in [200, 201]
        print(f"   [SUCCESS] Blacklisted URL saved to DB: {url_resp.json()}")

        # 10. Create Geofence Safety Zone
        print("\n10. Creating Geofence Safety Zone...")
        geo_resp = await client.post(f"/api/location/{child_id}/geofences", json={
            "name": "Home Safe Zone",
            "latitude": 13.0827,
            "longitude": 80.2707,
            "radius_meters": 300
        }, headers=headers)
        assert geo_resp.status_code == 201
        print(f"   [SUCCESS] Geofence boundary saved to DB: {geo_resp.json()}")

        # 11. Location Telemetry Ping
        print("\n11. Transmitting child location ping telemetry...")
        ping_resp = await client.post(f"/api/location/{child_id}/live", json={
            "child_id": child_id,
            "latitude": 13.0827,
            "longitude": 80.2707,
            "current_address": "123 Cyber Tower, Silicon Valley",
            "battery_percentage": 88
        }, headers=headers)
        assert ping_resp.status_code == 200
        print(f"   [SUCCESS] Location telemetry ping saved to DB: {ping_resp.json()}")

    print("\n==================================================")
    print("   ALL PARENTAL CONTROL DB OPERATIONS SUCCESSFUL! ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_full_parental_control_storage())
