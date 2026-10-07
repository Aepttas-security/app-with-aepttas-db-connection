import asyncio
from app.database import engine, Base
import app.models.db_models

async def create():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("CREATE ALL COMPLETED")

if __name__ == "__main__":
    asyncio.run(create())
