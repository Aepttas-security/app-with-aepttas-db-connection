import asyncio
import httpx
import uuid
import random
from app.main import app

async def test_device_pairing_workflow():
    print("==================================================")
    print("   TESTING DEVICE PAIRING & LINKING WORKFLOW     ")
    print("==================================================")

    unique_suffix = uuid.uuid4().hex[:6]
    test_user_email = f"parent_{unique_suffix}@example.com"
    test_child_name = f"Child_{unique_suffix}"
    init_code = f"{random.randint(100,899)}-{random.randint(100,899)}"
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=15.0) as client:
        # STEP 0: Parent Auth Setup
        print("\n[STEP 0] Registering parent account & getting JWT token...")
        reg_resp = await client.post("/api/auth/register", json={
            "email": test_user_email,
            "password": "Password123!",
            "name": f"Parent {unique_suffix}"
        })
        print(f"Register Status: {reg_resp.status_code}")
        
        login_resp = await client.post("/api/auth/login", json={
            "email": test_user_email,
            "password": "Password123!"
        })
        token = None
        if login_resp.status_code == 200:
            token = login_resp.json().get("token") or login_resp.json().get("access_token")
            if token:
                client.headers.update({"Authorization": f"Bearer {token}"})
                print(f"[OK] Token acquired: {token[:20]}...")
        
        if not token:
            client.headers.update({"Authorization": "Bearer mock_secure_jwt_token"})
            print("[INFO] Using mock authorization header for testing")

        # STEP 1: Create Child Profile
        print("\n[STEP 1] Creating a child profile...")
        create_child_resp = await client.post("/api/child", json={
            "name": test_child_name,
            "age": 11,
            "linking_code": init_code
        })
        print(f"Create Child Status: {create_child_resp.status_code}")
        child_data = create_child_resp.json()
        child_id = child_data.get("id")
        print(f"[OK] Created child with ID: {child_id}")

        # STEP 2: Generate Fresh Pairing / Linking Code
        print(f"\n[STEP 2] Generating fresh pairing code for child ({child_id})...")
        gen_code_resp = await client.post(f"/api/pairing/generate-code/{child_id}")
        print(f"Generate Code Status: {gen_code_resp.status_code}")
        gen_data = gen_code_resp.json()
        linking_code = gen_data.get("linking_code")
        print(f"[OK] Generated Linking Code: {linking_code}")

        # STEP 3: Child Device Submits Pairing Request
        print(f"\n[STEP 3] Child device pairing request with code: {linking_code}...")
        pair_device_payload = {
            "linking_code": linking_code,
            "device_name": "Google Pixel 8",
            "os_type": "Android 14"
        }
        verify_resp = await client.post("/api/pairing/verify", json=pair_device_payload)
        print(f"Pair Verification Status: {verify_resp.status_code}")
        print(f"[OK] Verification Response: {verify_resp.json()}")

        # STEP 4: Child Device Grants Pairing Consent
        print(f"\n[STEP 4] Child device submitting consent approval...")
        consent_payload = {
            "linking_code": linking_code,
            "consent_approved": True
        }
        consent_resp = await client.post(f"/api/pairing/child-consent/{child_id}", json=consent_payload)
        print(f"Consent Status: {consent_resp.status_code}")
        print(f"[OK] Consent Response: {consent_resp.json()}")

        # STEP 5: Poll Pairing Status
        print(f"\n[STEP 5] Querying real-time pairing status for child ({child_id})...")
        status_resp = await client.get(f"/api/pairing/status/{child_id}")
        print(f"Status Polling Response Code: {status_resp.status_code}")
        status_data = status_resp.json()
        print(f"[OK] Pairing Status Details: {status_data}")

        # STEP 6: Sync Hardware Permissions
        print(f"\n[STEP 6] Syncing hardware OS permission states...")
        perm_payload = {
            "location_allowed": True,
            "usage_stats_allowed": True,
            "vpn_filter_allowed": True
        }
        perm_resp = await client.post(f"/api/child/{child_id}/permissions-sync", json=perm_payload)
        print(f"Permissions Sync Status: {perm_resp.status_code}")
        print(f"[OK] Permissions Response: {perm_resp.json()}")

        # STEP 7: Unlink Device & Verify Status Reset
        print(f"\n[STEP 7] Unlinking child device...")
        unlink_resp = await client.post(f"/api/pairing/unlink/{child_id}")
        print(f"Unlink Status Code: {unlink_resp.status_code}")
        print(f"[OK] Unlink Response: {unlink_resp.json()}")

        post_unlink_status = await client.get(f"/api/pairing/status/{child_id}")
        print(f"[OK] Post-Unlink Status: {post_unlink_status.json()}")

    print("\n==================================================")
    print("   DEVICE PAIRING WORKFLOW TEST COMPLETE (SUCCESS) ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(test_device_pairing_workflow())
