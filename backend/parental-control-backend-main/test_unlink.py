import asyncio
import httpx

async def main():
    print("Testing device unlink endpoint...")
    child_id = "afcbc37d-1816-46e5-baf0-56f08f515d03"  # Test Child ID from database
    url = f"http://127.0.0.1:8002/api/child/{child_id}/unlink"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")

if __name__ == "__main__":
    asyncio.run(main())
