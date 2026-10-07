import asyncio
from sqlalchemy.future import select
from app.database import async_session
from app.models.db_models import User, Child, GeofenceZoneTable, ScreentimeSettingsTable, FilterPolicyTable, DevicePairingTable

async def test_all_db_operations():
    async with async_session() as session:
        try:
            print("1. Creating User...")
            user = User(
                name="Test Web Parent",
                email="test_web_sync@example.com",
                password_hash="SecurePassword123!"
            )
            session.add(user)
            await session.flush()
            print(f"   [SUCCESS] Created User ID: {user.id}")

            print("2. Creating Child Profile...")
            child = Child(
                parent_id=user.id,
                child_name="Leo",
                age=11,
                linking_code="WEB-888"
            )
            session.add(child)
            await session.flush()
            print(f"   [SUCCESS] Created Child ID: {child.child_id}")

            print("3. Creating Geofence Zone...")
            fence = GeofenceZoneTable(
                child_id=child.child_id,
                zone_name="Home Safety Zone",
                latitude=13.0827,
                longitude=80.2707,
                radius_meters=300
            )
            session.add(fence)

            print("4. Creating Screen Time Rule...")
            st = ScreentimeSettingsTable(
                child_id=child.child_id,
                daily_limit_minutes=180,
                minutes_used=30
            )
            session.add(st)

            await session.commit()
            print("=== ALL DATABASE TRANSACTIONS COMMITTED SUCCESSFULLY ===")
        except Exception as e:
            await session.rollback()
            print("!!! TRANSACTION FAILED !!! Error:", str(e))

if __name__ == "__main__":
    asyncio.run(test_all_db_operations())
