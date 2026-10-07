# migrate_add_phone_number.py - Add phone_number columns to database
from database import engine
from sqlalchemy import text

def add_phone_number_columns():
    """Add phone_number column to tables that don't have it"""

    with engine.connect() as conn:
        print("="*60)
        print("🔧 Adding phone_number columns to tables")
        print("="*60)

        # 1. Add to apt_calls_b
        try:
            conn.execute(text("""
                ALTER TABLE apt.apt_calls_b
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)
            """))
            print("✅ Added phone_number to apt_calls_b")
        except Exception as e:
            print(f"⚠️ apt_calls_b: {e}")

        # 2. Add to apt_blocked_numbers_b
        try:
            conn.execute(text("""
                ALTER TABLE apt.apt_blocked_numbers_b
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)
            """))
            print("✅ Added phone_number to apt_blocked_numbers_b")
        except Exception as e:
            print(f"⚠️ apt_blocked_numbers_b: {e}")

        # 3. Add to apt_alerts_b
        try:
            conn.execute(text("""
                ALTER TABLE apt.apt_alerts_b
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)
            """))
            print("✅ Added phone_number to apt_alerts_b")
        except Exception as e:
            print(f"⚠️ apt_alerts_b: {e}")

        # 4. Add to apt_reports_b
        try:
            conn.execute(text("""
                ALTER TABLE apt.apt_reports_b
                ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20)
            """))
            print("✅ Added phone_number to apt_reports_b")
        except Exception as e:
            print(f"⚠️ apt_reports_b: {e}")

        conn.commit()
        print("\n✅ Columns added successfully!")

def populate_phone_numbers_from_callers():
    """Populate phone_number columns from apt_callers_b"""

    with engine.connect() as conn:
        print("\n" + "="*60)
        print("📝 Populating phone_number from apt_callers_b")
        print("="*60)

        # Update apt_calls_b
        try:
            result = conn.execute(text("""
                UPDATE apt.apt_calls_b
                SET phone_number = c.phone_number
                FROM apt.apt_callers_b c
                WHERE apt_calls_b.caller_id = c.caller_id
                AND apt_calls_b.phone_number IS NULL
            """))
            print(f"✅ Updated apt_calls_b: {result.rowcount} rows")
        except Exception as e:
            print(f"⚠️ apt_calls_b population: {e}")

        # Update apt_blocked_numbers_b
        try:
            result = conn.execute(text("""
                UPDATE apt.apt_blocked_numbers_b
                SET phone_number = c.phone_number
                FROM apt.apt_callers_b c
                WHERE apt_blocked_numbers_b.caller_id = c.caller_id
                AND apt_blocked_numbers_b.phone_number IS NULL
            """))
            print(f"✅ Updated apt_blocked_numbers_b: {result.rowcount} rows")
        except Exception as e:
            print(f"⚠️ apt_blocked_numbers_b population: {e}")

        # Update apt_alerts_b
        try:
            result = conn.execute(text("""
                UPDATE apt.apt_alerts_b
                SET phone_number = c.phone_number
                FROM apt.apt_callers_b c
                WHERE apt_alerts_b.caller_id = c.caller_id
                AND apt_alerts_b.phone_number IS NULL
            """))
            print(f"✅ Updated apt_alerts_b: {result.rowcount} rows")
        except Exception as e:
            print(f"⚠️ apt_alerts_b population: {e}")

        # Update apt_reports_b
        try:
            result = conn.execute(text("""
                UPDATE apt.apt_reports_b
                SET phone_number = c.phone_number
                FROM apt.apt_callers_b c
                WHERE apt_reports_b.caller_id = c.caller_id
                AND apt_reports_b.phone_number IS NULL
            """))
            print(f"✅ Updated apt_reports_b: {result.rowcount} rows")
        except Exception as e:
            print(f"⚠️ apt_reports_b population: {e}")

        conn.commit()
        print("\n✅ Data population completed!")

def verify_columns():
    """Verify phone_number columns exist"""

    with engine.connect() as conn:
        print("\n" + "="*60)
        print("🔍 Verifying phone_number columns")
        print("="*60)

        tables = ['apt_calls_b', 'apt_blocked_numbers_b', 'apt_alerts_b', 'apt_reports_b']

        for table in tables:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'apt'
                AND table_name = :table
                AND column_name = 'phone_number'
            """), {"table": table}).first()

            if result:
                # Count non-null values
                count = conn.execute(text(f"""
                    SELECT COUNT(*) FROM apt.{table} WHERE phone_number IS NOT NULL
                """)).scalar()
                print(f"✅ {table}: phone_number exists ({count} rows populated)")
            else:
                print(f"❌ {table}: phone_number NOT found")

if __name__ == "__main__":
    print("="*60)
    print("🔧 MIGRATION: Add phone_number to all tables")
    print("="*60)

    # Step 1: Add columns
    add_phone_number_columns()

    # Step 2: Populate data from callers
    populate_phone_numbers_from_callers()

    # Step 3: Verify
    verify_columns()

    print("\n" + "="*60)
    print("✅ Migration complete!")