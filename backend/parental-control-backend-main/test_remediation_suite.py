# test_remediation_suite.py
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
import httpx

from app.database import async_session
from sqlalchemy import text

BASE_URL = "http://127.0.0.1:8000"

async def test_suite():
    print("=" * 80)
    print("STARTING PHASE 2 REMEDIATION INTEGRATION TEST SUITE")
    print("=" * 80)

    # 1. REGISTER PARENT A & PARENT B
    parent_a_email = f"parent_a_{uuid.uuid4().hex[:6]}@test.com"
    parent_a_name = f"ParentA_{uuid.uuid4().hex[:6]}"
    parent_a_pwd = "SecurePassword123!"

    parent_b_email = f"parent_b_{uuid.uuid4().hex[:6]}@test.com"
    parent_b_name = f"ParentB_{uuid.uuid4().hex[:6]}"
    parent_b_pwd = "SecurePassword123!"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Register Parent A
        res_a = await client.post("/api/auth/register", json={
            "name": parent_a_name,
            "email": parent_a_email,
            "password": parent_a_pwd
        })
        print(f"[TEST 1] Parent A Registration: HTTP {res_a.status_code} - {res_a.json()}")
        assert res_a.status_code == 201, f"Expected 201, got {res_a.status_code}"

        # Register Parent B
        res_b = await client.post("/api/auth/register", json={
            "name": parent_b_name,
            "email": parent_b_email,
            "password": parent_b_pwd
        })
        print(f"[TEST 1] Parent B Registration: HTTP {res_b.status_code} - {res_b.json()}")
        assert res_b.status_code == 201

        # Direct DB Verification of Password Hashing
        async with async_session() as db:
            query = text("SELECT password_hash FROM apt_users_b WHERE email = :email")
            row = (await db.execute(query, {"email": parent_a_email})).fetchone()
            assert row is not None
            assert row[0].startswith("$2b$") or row[0].startswith("$2a$"), f"Password hash is not bcrypt: {row[0]}"
            print(f"[TEST 1] Verified bcrypt password hashing in DB for {parent_a_email}")

        # 2. LOGIN & JWT TEST
        login_res_a = await client.post("/api/auth/login", json={
            "email": parent_a_email,
            "password": parent_a_pwd
        })
        print(f"[TEST 2] Parent A Login: HTTP {login_res_a.status_code}")
        assert login_res_a.status_code == 200
        token_a = login_res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        login_res_b = await client.post("/api/auth/login", json={
            "email": parent_b_email,
            "password": parent_b_pwd
        })
        assert login_res_b.status_code == 200
        token_b = login_res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Test Invalid Login
        bad_login = await client.post("/api/auth/login", json={
            "email": parent_a_email,
            "password": "WrongPassword!"
        })
        print(f"[TEST 2] Invalid Password Login: HTTP {bad_login.status_code}")
        assert bad_login.status_code == 401

        # Test Missing/Invalid JWT Token
        bad_jwt = await client.get("/api/child", headers={"Authorization": "Bearer invalid_token_xyz"})
        print(f"[TEST 2] Invalid JWT Request: HTTP {bad_jwt.status_code}")
        assert bad_jwt.status_code == 401

        # 3. CREATE CHILD & RESOLVE UUID -> BIGINT (RULES 1 & 2)
        child_res = await client.post("/api/child", headers=headers_a, json={
            "name": "ChildA",
            "age": 10,
            "linking_code": f"{uuid.uuid4().hex[:6]}"
        })
        print(f"[TEST 3] Create Child Profile: HTTP {child_res.status_code} - {child_res.json()}")
        assert child_res.status_code == 201
        child_uuid_a = child_res.json()["id"]

        # Direct DB Verification of BIGINT child_id mapping
        async with async_session() as db:
            q_child = text("SELECT child_id, child_uuid, parent_user_id FROM apt_children_b WHERE CAST(child_uuid AS TEXT) = :u OR child_uuid::text = :u;")
            c_row = (await db.execute(q_child, {"u": str(child_uuid_a)})).fetchone()
            assert c_row is not None
            bigint_child_id = c_row[0]
            print(f"[TEST 3] Resolved child_uuid '{child_uuid_a}' -> BIGINT child_id {bigint_child_id} (Parent user_id: {c_row[2]})")

        # 4. PARENT OWNERSHIP AUTHORIZATION TEST (RULE 2)
        # Parent A accesses Child A screentime -> Expect 200
        st_res_a = await client.get(f"/api/screentime/{child_uuid_a}/dashboard", headers=headers_a)
        print(f"[TEST 4] Parent A Accesses Child A Screentime: HTTP {st_res_a.status_code}")
        assert st_res_a.status_code == 200

        # Parent B accesses Child A screentime -> Expect 403 Forbidden
        st_res_b = await client.get(f"/api/screentime/{child_uuid_a}/dashboard", headers=headers_b)
        print(f"[TEST 4] Parent B Accesses Child A Screentime: HTTP {st_res_b.status_code}")
        assert st_res_b.status_code == 403, f"Expected 403 Forbidden, got {st_res_b.status_code}"

        # 5. RANDOM NON-EXISTENT CHILD UUID TEST (RULE 1)
        rand_uuid = str(uuid.uuid4())
        rand_res = await client.get(f"/api/screentime/{rand_uuid}/dashboard", headers=headers_a)
        print(f"[TEST 5] Random Child UUID Screentime Request: HTTP {rand_res.status_code}")
        assert rand_res.status_code == 404, f"Expected 404 Not Found, got {rand_res.status_code}"

        # 6. INSTALLED APPLICATIONS TEST (RULE 5 & 8)
        apps_res = await client.get(f"/api/apps/{child_uuid_a}", headers=headers_a)
        print(f"[TEST 6] List Apps (empty DB): HTTP {apps_res.status_code} - {apps_res.json()}")
        assert apps_res.status_code == 200
        assert isinstance(apps_res.json(), list)

        # Sync Apps
        sync_res = await client.post(f"/api/apps/{child_uuid_a}/sync", json={
            "apps": [
                {"package_name": "com.roblox.client", "app_name": "Roblox", "category": "Gaming"},
                {"package_name": "com.instagram.android", "app_name": "Instagram", "category": "Social"}
            ]
        })
        print(f"[TEST 6] Sync Apps: HTTP {sync_res.status_code} - {sync_res.json()}")
        assert sync_res.status_code == 200

        # List Apps after sync
        apps_res_2 = await client.get(f"/api/apps/{child_uuid_a}", headers=headers_a)
        print(f"[TEST 6] List Apps after Sync: HTTP {apps_res_2.status_code} - {len(apps_res_2.json())} apps found")
        assert len(apps_res_2.json()) == 2

        # 7. WEB CONTENT FILTER TEST (RULE 7 & 9)
        filter_res = await client.post(f"/api/filters/{child_uuid_a}/category", headers=headers_a, json={
            "category_name": "Adult",
            "is_blocked": True
        })
        print(f"[TEST 7] Toggle Category Filter: HTTP {filter_res.status_code}")
        assert filter_res.status_code == 200

        bl_res = await client.post(f"/api/filters/{child_uuid_a}/blacklist", headers=headers_a, json={
            "url": "malicious-test-site.com"
        })
        print(f"[TEST 7] Add Blacklist URL: HTTP {bl_res.status_code}")
        assert bl_res.status_code == 201

        rules_res = await client.get(f"/api/filters/{child_uuid_a}/rules", headers=headers_a)
        print(f"[TEST 7] Fetch Rules: HTTP {rules_res.status_code} - {rules_res.json()}")
        assert rules_res.status_code == 200
        assert "malicious-test-site.com" in rules_res.json()["blacklisted_urls"]

        # 8. LOCATION & SOS ALERTS TEST (RULE 8 & 9)
        loc_ping = await client.post(f"/api/location/{child_uuid_a}/live", json={
            "child_id": str(child_uuid_a),
            "latitude": 13.0827,
            "longitude": 80.2707,
            "current_address": "Test School Campus",
            "battery_percentage": 90
        })
        print(f"[TEST 8] Location Ping: HTTP {loc_ping.status_code}")
        assert loc_ping.status_code == 200

        loc_fetch = await client.get(f"/api/location/{child_uuid_a}/live", headers=headers_a)
        print(f"[TEST 8] Fetch Live Location: HTTP {loc_fetch.status_code} - {loc_fetch.json()}")
        assert loc_fetch.status_code == 200
        assert loc_fetch.json()["current_address"] == "Test School Campus"

        sos_trigger = await client.post("/api/sos/trigger", json={
            "child_id": str(child_uuid_a),
            "current_latitude": 13.0827,
            "current_longitude": 80.2707,
            "emergency_message": "Help required at Test Location"
        })
        print(f"[TEST 8] Trigger SOS Alert: HTTP {sos_trigger.status_code}")
        assert sos_trigger.status_code == 201

        sos_active = await client.get(f"/api/sos/active/{child_uuid_a}", headers=headers_a)
        print(f"[TEST 8] Fetch Active SOS Alarms: HTTP {sos_active.status_code} - panic_active: {sos_active.json()['is_panic_active']}")
        assert sos_active.status_code == 200
        assert sos_active.json()["is_panic_active"] is True

        # 9. UNLINK LIFECYCLE TEST (RULE 10)
        req_unlink = await client.post(f"/api/child/{child_uuid_a}/request-unlink")
        print(f"[TEST 9] Request Device Unlink: HTTP {req_unlink.status_code} - {req_unlink.json()}")
        assert req_unlink.status_code == 201
        generated_unlink_code = req_unlink.json()["unlink_code"]

        # Fetch Active Unlink Code as Parent A
        active_unlink = await client.get(f"/api/child/{child_uuid_a}/active-unlink-code", headers=headers_a)
        print(f"[TEST 9] Parent Fetch Active Unlink Code: HTTP {active_unlink.status_code} - {active_unlink.json()}")
        assert active_unlink.status_code == 200
        assert active_unlink.json()["unlink_code"] == generated_unlink_code

        # Attempt Unlink with Invalid Code (e.g. 1234 or 9999) -> Expect Rejection
        bad_unlink = await client.post(f"/api/child/{child_uuid_a}/verify-unlink", json={
            "unlink_code": "999999"
        })
        print(f"[TEST 9] Submit Invalid Unlink Code: HTTP {bad_unlink.status_code}")
        assert bad_unlink.status_code == 400

        # Submit Valid Unlink Code
        good_unlink = await client.post(f"/api/child/{child_uuid_a}/verify-unlink", json={
            "unlink_code": generated_unlink_code
        })
        print(f"[TEST 9] Submit Valid Unlink Code: HTTP {good_unlink.status_code} - {good_unlink.json()}")
        assert good_unlink.status_code == 200
        assert good_unlink.json()["unlinked"] is True

        # Attempt Reusing Valid Code -> Expect Rejection
        reuse_unlink = await client.post(f"/api/child/{child_uuid_a}/verify-unlink", json={
            "unlink_code": generated_unlink_code
        })
        print(f"[TEST 9] Reuse Unlink Code: HTTP {reuse_unlink.status_code}")
        assert reuse_unlink.status_code == 400

        # Direct DB Verification of Pairing Table State
        async with async_session() as db:
            q_unl = text("SELECT status, is_active FROM apt_device_pairing_b WHERE child_id = :cid ORDER BY pairing_id DESC LIMIT 1;")
            unl_row = (await db.execute(q_unl, {"cid": bigint_child_id})).fetchone()
            assert unl_row is not None
            assert unl_row[0] == "UNLINKED"
            assert unl_row[1] is False or unl_row[1] == 0
            print(f"[TEST 9] Verified direct DB apt_device_pairing_b record: status={unl_row[0]}, is_active={unl_row[1]}")


    print("=" * 80)
    print("ALL REMEDIATION SUITE TESTS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_suite())
