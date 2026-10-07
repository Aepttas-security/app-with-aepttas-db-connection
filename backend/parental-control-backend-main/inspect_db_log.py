import asyncio
from sqlalchemy import text
from app.database import engine

async def inspect():
    async with engine.connect() as conn:
        print("=== 1. APT USERS (apt_users_b) ===")
        users = await conn.execute(text("SELECT user_id, username, email FROM apt_users_b ORDER BY user_id DESC LIMIT 10;"))
        for u in users.fetchall():
            print(f"User ID: {u[0]} | Username: {u[1]} | Email: {u[2]}")

        print("\n=== 2. APT CHILDREN (apt_children_b) ===")
        children = await conn.execute(text("SELECT child_id, child_uuid, parent_user_id, child_name, age, linking_code FROM apt_children_b ORDER BY child_id DESC LIMIT 10;"))
        rows = children.fetchall()
        if not rows:
            print("No children profiles found in apt_children_b.")
        for c in rows:
            print(f"Child ID: {c[0]} | UUID: {c[1]} | Parent ID: {c[2]} | Name: {c[3]} | Age: {c[4]} | Code: {c[5]}")

        print("\n=== 3. DEVICE PAIRINGS (apt_device_pairing_b) ===")
        pairings = await conn.execute(text("SELECT pairing_id, linking_code, parent_id, child_uuid, device_name, status, child_consent_given FROM apt_device_pairing_b ORDER BY pairing_id DESC LIMIT 10;"))
        p_rows = pairings.fetchall()
        if not p_rows:
            print("No pairing records found in apt_device_pairing_b.")
        for p in p_rows:
            print(f"Pairing ID: {p[0]} | Code: {p[1]} | Parent ID: {p[2]} | Child UUID: {p[3]} | Device: {p[4]} | Status: {p[5]} | Consent: {p[6]}")

        print("\n=== 4. SCREEN TIME SETTINGS (apt_screen_time_b) ===")
        st = await conn.execute(text("SELECT screen_time_id, child_id, daily_limit_minutes, minutes_used FROM apt_screen_time_b ORDER BY screen_time_id DESC LIMIT 10;"))
        st_rows = st.fetchall()
        if not st_rows:
            print("No screen time records found in apt_screen_time_b.")
        for s in st_rows:
            print(f"ID: {s[0]} | Child ID: {s[1]} | Limit: {s[2]}m | Used: {s[3]}m")

if __name__ == '__main__':
    asyncio.run(inspect())
