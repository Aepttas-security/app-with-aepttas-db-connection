import asyncio
from sqlalchemy import text
from app.database import engine

async def run():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT child_id FROM children LIMIT 1;"))
        row = result.fetchone()
        if row:
            child_id = row[0]
            print(f"Found child_id: {child_id}")
            
            import httpx
            base_url = "http://127.0.0.1:8000/api/location"
            async with httpx.AsyncClient() as client:
                print(f"1. Testing Toggle Location Tracking for {child_id}...")
                resp1 = await client.post(f"{base_url}/{child_id}/tracking/toggle", json={"is_enabled": False})
                print(f"Status: {resp1.status_code}, Response: {resp1.text}")
                
                print(f"\n2. Testing Toggle Geofence Tracking for {child_id}...")
                resp2 = await client.post(f"{base_url}/{child_id}/geofence/toggle", json={"is_enabled": False})
                print(f"Status: {resp2.status_code}, Response: {resp2.text}")
        else:
            print("No children found in database.")

if __name__ == "__main__":
    asyncio.run(run())
