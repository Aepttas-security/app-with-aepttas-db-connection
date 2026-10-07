# check_and_import.py - CLEAN VERSION

import os
import csv
from database import SessionLocal
from models import *
from datetime import datetime

def list_csv_files():
    """List all CSV files in current directory"""
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    print(f"Found {len(csv_files)} CSV files:")
    for f in csv_files:
        size = os.path.getsize(f)
        print(f"  - {f} ({size} bytes)")
    return csv_files

def check_csv_content(filename):
    """Check content of CSV file"""
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return False

    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"  {filename}: {len(rows)} rows")
        if len(rows) > 0:
            print(f"  Columns: {', '.join(reader.fieldnames)}")
            print(f"  First row: {rows[0]}")
        return len(rows) > 0

def manual_import():
    """Manually import data with better error handling"""
    db = SessionLocal()

    try:
        files = {
            'data-1780992377554.csv': AptBlockedNumbersB,
            'data-1780992392170.csv': AptCallersB,
            'data-1780992401557.csv': AptCallsB,
            'data-1780992341977.csv': AptAlertsB,
            'data-1780992413141.csv': AptReportsB
        }

        for filename, model in files.items():
            if os.path.exists(filename):
                print(f"\n📁 Importing {filename}...")
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        try:
                            if model == AptBlockedNumbersB:
                                obj = AptBlockedNumbersB(
                                    phone_number=row['phone_number'],
                                    caller_name=row.get('caller_name'),
                                    block_reason=row.get('block_reason', 'Blocked by user'),
                                    blocked_date=datetime.now(),
                                    reason=row.get('block_reason', 'Blocked by user')
                                )
                            elif model == AptCallersB:
                                obj = AptCallersB(
                                    phone_number=row['phone_number'],
                                    caller_name=row.get('caller_name'),
                                    is_spam_reported=row.get('is_spam_reported', 'False') == 'True'
                                )
                            elif model == AptCallsB:
                                obj = AptCallsB(
                                    user_id=1,
                                    caller_id=1,
                                    call_type=row.get('call_type', 'INCOMING').upper(),
                                    call_duration_seconds=int(row.get('duration', 0)),
                                    call_timestamp=datetime.now()
                                )
                            elif model == AptAlertsB:
                                obj = AptAlertsB(
                                    user_id=1,
                                    severity_id=int(row.get('severity_id', 2)),
                                    alert_message=row.get('message', 'Alert'),
                                    is_acknowledged=False
                                )
                            elif model == AptReportsB:
                                obj = AptReportsB(
                                    user_id=1,
                                    report_reason=row.get('description', row.get('report_type', 'Reported'))
                                )
                            else:
                                continue

                            db.add(obj)
                            count += 1
                        except Exception as e:
                            print(f"    Error on row {count}: {e}")

                    db.commit()
                    print(f"  ✅ Imported {count} records for {model.__tablename__}")
            else:
                print(f"\n⚠️ File not found: {filename}")

        # Show final counts
        print("\n" + "="*50)
        print("📊 FINAL COUNTS AFTER IMPORT:")
        print("="*50)
        print(f"   Calls: {db.query(AptCallsB).count()}")
        print(f"   Callers: {db.query(AptCallersB).count()}")
        print(f"   Alerts: {db.query(AptAlertsB).count()}")
        print(f"   Reports: {db.query(AptReportsB).count()}")
        print(f"   Blocked Numbers: {db.query(AptBlockedNumbersB).count()}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔍 Checking CSV files...")
    csv_files = list_csv_files()

    if not csv_files:
        print("\n⚠️ No CSV files found in current directory!")
        print(f"   Current directory: {os.getcwd()}")
    else:
        print("\n📄 Checking file contents...")
        for f in csv_files:
            check_csv_content(f)

        print("\n" + "="*50)
        response = input("Do you want to import these files? (yes/no): ")
        if response.lower() == 'yes':
            manual_import()