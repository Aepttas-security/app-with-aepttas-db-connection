import asyncio
from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema');
        """))
        tables = result.fetchall()
        print("=== TABLES IN DB ===")
        for schema, table in tables:
            print(f"Schema: {schema} | Table: {table}")

        print("\n=== COLUMNS IN apt_device_pairing_b ===")
        result_cols = await conn.execute(text("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name LIKE '%pairing%' OR table_name = 'child'
            ORDER BY table_name, ordinal_position;
        """))
        for table, column, dtype in result_cols.fetchall():
            print(f"Table: {table} | Column: {column} ({dtype})")


if __name__ == "__main__":
    asyncio.run(main())
