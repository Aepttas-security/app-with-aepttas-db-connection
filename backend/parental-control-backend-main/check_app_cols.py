import asyncio
from sqlalchemy import text
from app.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'apt' AND table_name LIKE '%app%'
            ORDER BY table_name, ordinal_position;
        """))
        for r in res.fetchall():
            print(r)

if __name__ == "__main__":
    asyncio.run(check())
