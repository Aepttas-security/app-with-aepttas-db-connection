# init_db.py
from database import init_db, test_db_connection
import sys

def main():
    print("=" * 50)
    print("🔧 INITIALIZING DATABASE")
    print("=" * 50)
    
    print("\n📊 Testing connection...")
    result = test_db_connection()
    if result and result.get('status') == 'success':
        print("✅ Connection successful!")
        print("\n📊 Creating tables...")
        init_db()
        print("✅ Database initialized successfully!")
    else:
        print("❌ Connection failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
