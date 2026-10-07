# create_tables.py - Table creation script
from database import engine, SessionLocal, Base
from models import *
from datetime import datetime, timezone
import csv
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all existing tables"""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped successfully")

def create_all_tables():
    """Create all tables"""
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")

def parse_datetime(dt_str):
    """Parse datetime string safely"""
    if not dt_str or dt_str == 'NULL' or dt_str == '':
        return datetime.now()
    try:
        dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
    except:
        return datetime.now()

def parse_int(val):
    """Parse integer safely"""
    if not val or val == 'NULL' or val == '':
        return None
    try:
        return int(val)
    except:
        return None

def import_csv_data():
    """Import data from CSV files into database"""
    db = SessionLocal()
    
    try:
        print("="*50)
        print("IMPORTING DATA")
        print("="*50)
        
        # First, import callers (needed for foreign keys)
        if os.path.exists('data-1780992392170.csv'):
            print("\n📁 Importing callers from data-1780992392170.csv...")
            with open('data-1780992392170.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        existing = db.query(AptCallersB).filter(
                            AptCallersB.phone_number == row['phone_number']
                        ).first()
                        if not existing:
                            caller = AptCallersB(
                                phone_number=row['phone_number'],
                                caller_name=row.get('caller_name'),
                                is_spam_reported=str(row.get('is_spam_reported', 'False')).lower() == 'true',
                                risk_level_id=parse_int(row.get('risk_level_id'))
                            )
                            db.add(caller)
                            count += 1
                    except Exception as e:
                        logger.error(f"Error importing caller {row.get('phone_number')}: {e}")
                db.commit()
            print(f"   ✅ Imported {count} callers")
        
        # Import calls
        if os.path.exists('data-1780992401557.csv'):
            print("\n📁 Importing calls from data-1780992401557.csv...")
            with open('data-1780992401557.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        caller = db.query(AptCallersB).filter(
                            AptCallersB.phone_number == row['caller_number']
                        ).first()
                        
                        if not caller:
                            caller = AptCallersB(
                                phone_number=row['caller_number'],
                                caller_name=row.get('caller_name')
                            )
                            db.add(caller)
                            db.flush()
                        
                        call = AptCallsB(
                            user_id=parse_int(row.get('user_id', 1)),
                            caller_id=caller.caller_id,
                            call_type=row.get('call_type', 'INCOMING').upper(),
                            call_duration_seconds=parse_int(row.get('duration', 0)) or 0,
                            call_timestamp=parse_datetime(row.get('detection_date')),
                            status_id=parse_int(row.get('status_id'))
                        )
                        db.add(call)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error importing call: {e}")
                db.commit()
            print(f"   ✅ Imported {count} calls")
        
        # Import blocked numbers
        if os.path.exists('data-1780992377554.csv'):
            print("\n📁 Importing blocked numbers from data-1780992377554.csv...")
            with open('data-1780992377554.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        caller = db.query(AptCallersB).filter(
                            AptCallersB.phone_number == row['phone_number']
                        ).first()
                        
                        if not caller:
                            caller = AptCallersB(
                                phone_number=row['phone_number'],
                                caller_name=row.get('caller_name')
                            )
                            db.add(caller)
                            db.flush()
                        
                        blocked = AptBlockedNumbersB(
                            user_id=parse_int(row.get('user_id', 1)),
                            caller_id=caller.caller_id,
                            blocked_date=parse_datetime(row.get('block_date')),
                            reason=row.get('block_reason', 'Blocked by user')
                        )
                        db.add(blocked)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error importing blocked number: {e}")
                db.commit()
            print(f"   ✅ Imported {count} blocked numbers")
        
        # Import alerts
        if os.path.exists('data-1780992341977.csv'):
            print("\n📁 Importing alerts from data-1780992341977.csv...")
            with open('data-1780992341977.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        caller = db.query(AptCallersB).filter(
                            AptCallersB.phone_number == row['caller_number']
                        ).first()
                        
                        alert = AptAlertsB(
                            user_id=parse_int(row.get('user_id', 1)),
                            caller_id=caller.caller_id if caller else None,
                            severity_id=parse_int(row.get('severity_id', 2)),
                            alert_message=row.get('message', 'Alert triggered'),
                            is_acknowledged=str(row.get('is_read', 'False')).lower() == 'true'
                        )
                        db.add(alert)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error importing alert: {e}")
                db.commit()
            print(f"   ✅ Imported {count} alerts")
        
        # Import reports
        if os.path.exists('data-1780992413141.csv'):
            print("\n📁 Importing reports from data-1780992413141.csv...")
            with open('data-1780992413141.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    try:
                        caller = db.query(AptCallersB).filter(
                            AptCallersB.phone_number == row['caller_number']
                        ).first()
                        
                        if not caller:
                            caller = AptCallersB(
                                phone_number=row['caller_number']
                            )
                            db.add(caller)
                            db.flush()
                        
                        report = AptReportsB(
                            user_id=parse_int(row.get('user_id', 1)),
                            caller_id=caller.caller_id,
                            report_reason=row.get('description', row.get('report_type', 'Reported')),
                            status_id=parse_int(row.get('status_id'))
                        )
                        db.add(report)
                        count += 1
                    except Exception as e:
                        logger.error(f"Error importing report: {e}")
                db.commit()
            print(f"   ✅ Imported {count} reports")
        
        # Create default settings
        print("\n📁 Creating default settings...")
        settings = db.query(AptCallSettingsB).first()
        if not settings:
            settings = AptCallSettingsB(
                user_id=1,
                auto_block_spam=True,
                block_unknown_numbers=False
            )
            db.add(settings)
            db.commit()
            print("   ✅ Default settings created")
        else:
            print("   ✅ Settings already exist")
        
        print("\n" + "="*50)
        print("✅ IMPORT COMPLETE")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_data():
    """Verify imported data"""
    db = SessionLocal()
    try:
        print("\n" + "="*50)
        print("DATA VERIFICATION")
        print("="*50)
        
        calls = db.query(AptCallsB).count()
        callers = db.query(AptCallersB).count()
        alerts = db.query(AptAlertsB).count()
        reports = db.query(AptReportsB).count()
        blocked = db.query(AptBlockedNumbersB).count()
        settings = db.query(AptCallSettingsB).count()
        
        print(f"\n📊 TABLE COUNTS:")
        print(f"   apt_calls_b: {calls}")
        print(f"   apt_callers_b: {callers}")
        print(f"   apt_alerts_b: {alerts}")
        print(f"   apt_reports_b: {reports}")
        print(f"   apt_blocked_numbers_b: {blocked}")
        print(f"   apt_call_settings_b: {settings}")
        
        if calls > 0:
            print(f"\n📝 Sample calls:")
            sample = db.query(AptCallsB).limit(3).all()
            for s in sample:
                print(f"   ID: {s.call_id}, Type: {s.call_type}, Duration: {s.call_duration_seconds}s")
        
        if callers > 0:
            print(f"\n📝 Sample callers:")
            sample = db.query(AptCallersB).limit(3).all()
            for s in sample:
                print(f"   ID: {s.caller_id}, Phone: {s.phone_number}, Spam Reported: {s.is_spam_reported}")
        
        print("\n" + "="*50)
        
    finally:
        db.close()

if __name__ == "__main__":
    print("="*50)
    print("DATABASE SETUP")
    print("="*50)
    
    response = input("\nDo you want to drop existing tables? (yes/no): ").lower()
    if response == 'yes':
        drop_all_tables()
    
    create_all_tables()
    
    response = input("Do you want to import CSV data? (yes/no): ").lower()
    if response == 'yes':
        import_csv_data()
    
    verify_data()
    
    print("\n✅ DATABASE SETUP COMPLETE!")