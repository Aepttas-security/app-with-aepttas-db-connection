"""
Script to inspect the latest registered users and activity logs from Render PostgreSQL
"""
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://apt_callmgmt_app:Call%40intern_aepttas@dpg-dail4sh5efls73dvr100-a.oregon-postgres.render.com:5432/aepttas_xdr?sslmode=require&channel_binding=disable"

def check_latest_users():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 60)
    print("           LATEST REGISTERED / ACTIVE USERS          ")
    print("=" * 60)
    
    cur.execute("""
        SELECT user_id, username, email, phone_number, is_active, created_date, last_updated_date
        FROM apt.apt_users_b
        ORDER BY user_id DESC
        LIMIT 10;
    """)
    users = cur.fetchall()
    
    if not users:
        print("No users found in database.")
    else:
        for u in users:
            print(f"ID:           {u['user_id']}")
            print(f"Username:     {u['username']}")
            print(f"Email:        {u['email']}")
            print(f"Phone:        {u['phone_number']}")
            print(f"Active:       {u['is_active']}")
            print(f"Created:      {u['created_date']}")
            print(f"Last Updated: {u['last_updated_date']}")
            print("-" * 60)

    # Check recent activity logs if any exist
    try:
        cur.execute("""
            SELECT id, action, details, timestamp
            FROM apt.apt_activity_logs_b
            ORDER BY id DESC
            LIMIT 5;
        """)
        activities = cur.fetchall()
        if activities:
            print("\n" + "=" * 60)
            print("                 RECENT ACTIVITY LOGS                ")
            print("=" * 60)
            for a in activities:
                print(f"Time: {a['timestamp']} | Action: {a['action']} | Details: {a['details']}")
    except Exception:
        pass

    conn.close()

if __name__ == "__main__":
    check_latest_users()
