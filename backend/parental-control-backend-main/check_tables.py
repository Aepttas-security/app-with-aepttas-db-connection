import asyncio
from sqlalchemy import text
from app.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='apt' ORDER BY table_name;"))
        tables = [r[0] for r in res.fetchall()]
        print("TABLES IN apt SCHEMA:", tables)

if __name__ == "__main__":
    asyncio.run(check())
