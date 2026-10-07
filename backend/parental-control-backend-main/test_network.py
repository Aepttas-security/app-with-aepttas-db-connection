import asyncio
import uuid
import httpx

async def test_backend():
    print("Testing connection to Neon DB Backend...")
    base_url = "http://127.0.0.1:8000/api/location"
    
    test_child_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient() as client:
        print(f"1. Testing Toggle Location Tracking for {test_child_id}...")
        try:
            resp1 = await client.post(f"{base_url}/{test_child_id}/tracking/toggle", json={"is_enabled": False})
            print(f"Status: {resp1.status_code}")
            print(f"Response: {resp1.text}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            return
            
        print(f"\n2. Testing Toggle Geofence Tracking for {test_child_id}...")
        resp2 = await client.post(f"{base_url}/{test_child_id}/geofence/toggle", json={"is_enabled": False})
        print(f"Status: {resp2.status_code}")
        print(f"Response: {resp2.text}")
        
if __name__ == "__main__":
    asyncio.run(test_backend())
