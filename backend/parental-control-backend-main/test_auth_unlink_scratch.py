import asyncio
import httpx
import uuid
from app.main import app

async def test_auth_verify_pin():
    unique_suffix = uuid.uuid4().hex[:6]
    parent_email = f"unlink_parent_{unique_suffix}@example.com"
    child_email = f"child_{unique_suffix}@safeguard.com"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register parent
        reg_resp = await client.post("/api/auth/register", json={
            "email": parent_email,
            "password": "Password123!",
            "name": f"Unlink Parent {unique_suffix}"
        })
        assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"

        # 2. Login parent to get token
        login_resp = await client.post("/api/auth/login", json={
            "email": parent_email,
            "password": "Password123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")

        # 3. Create child
        child_resp = await client.post(
            "/api/auth/child/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": f"Unlink Child {unique_suffix}",
                "email": child_email,
                "password": "Password123!"
            }
        )
        assert child_resp.status_code == 201
        child_id = child_resp.json()["account_details"]["child_id"]

        # 4. Test Master PIN
        master_pin_resp = await client.post("/api/auth/verify-parent-pin", json={"pin": "1234"})
        print("Master PIN verification:", master_pin_resp.status_code, master_pin_resp.json())
        assert master_pin_resp.status_code == 200
        assert master_pin_resp.json()["verified"] is True

        # 5. Child requests device unlink code
        req_unlink = await client.post(f"/api/child/{child_id}/request-unlink")
        assert req_unlink.status_code == 201
        unlink_code = req_unlink.json()["unlink_code"]
        raw_digits = unlink_code.replace("-", "")

        # 6. Verify via raw digits without Auth header
        verify_raw = await client.post("/api/auth/verify-parent-pin", json={"pin": raw_digits})
        print("Verify PIN via raw digits (no auth header):", verify_raw.status_code, verify_raw.json())
        assert verify_raw.status_code == 200
        assert verify_raw.json()["verified"] is True

        # 7. Request fresh code and verify formatted code with Auth header
        req_unlink_2 = await client.post(f"/api/child/{child_id}/request-unlink")
        unlink_code_2 = req_unlink_2.json()["unlink_code"]

        verify_fmt = await client.post(
            "/api/auth/verify-parent-pin",
            headers={"Authorization": f"Bearer {token}"},
            json={"pin": unlink_code_2}
        )
        print("Verify PIN via formatted code (with auth header):", verify_fmt.status_code, verify_fmt.json())
        assert verify_fmt.status_code == 200
        assert verify_fmt.json()["verified"] is True

        print("\nALL UNLINK VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_auth_verify_pin())
