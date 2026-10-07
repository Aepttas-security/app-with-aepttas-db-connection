import asyncio
from sqlalchemy import text
from app.database import engine

async def inspect_postgres():
    async with engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'apt'
            ORDER BY table_name, ordinal_position;
        """))
        columns = res.fetchall()
        print("=== LIVE POSTGRESQL (apt schema) COLUMNS ===")
        current_table = None
        for table, col, dtype in columns:
            if table != current_table:
                print(f"\nTABLE: apt.{table}")
                current_table = table
            print(f"  - {col}: {dtype}")

if __name__ == "__main__":
    asyncio.run(inspect_postgres())
