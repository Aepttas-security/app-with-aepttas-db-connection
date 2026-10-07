import asyncio
from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.connect() as conn:
        print("=== SCHEMAS & TABLES ===")
        res = await conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema IN ('public', 'apt') OR table_name LIKE 'apt_%' OR table_name = 'child' OR table_name = 'child_profiles';
        """))
        for schema, name in res.fetchall():
            print(f"{schema}.{name}")

if __name__ == "__main__":
    asyncio.run(main())
