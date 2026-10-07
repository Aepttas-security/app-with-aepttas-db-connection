import asyncio
from sqlalchemy import text
from app.database import engine

async def run_migrations():
    try:
        async with engine.begin() as conn:
            print("Adding is_tracking_enabled column...")
            await conn.execute(text("ALTER TABLE location ADD COLUMN is_tracking_enabled BOOLEAN DEFAULT TRUE NOT NULL;"))
    except Exception as e:
        print(f"Tracking error: {e}")
        
    try:
        async with engine.begin() as conn:
            print("Adding is_geofence_enabled column...")
            await conn.execute(text("ALTER TABLE location ADD COLUMN is_geofence_enabled BOOLEAN DEFAULT TRUE NOT NULL;"))
    except Exception as e:
        print(f"Geofence error: {e}")
            
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migrations())
