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
        # Check for each CSV file
        files = {
            'data-1780992377554.csv': BlockedNumberDB,
            'data-1780992392170.csv': CallerDB,
            'data-1780992401557.csv': CallDB,
            'data-1780992341977.csv': AlertDB,
            'data-1780992413141.csv': ReportDB
        }
        
        for filename, model in files.items():
            if os.path.exists(filename):
                print(f"\nImporting {filename}...")
                with open(filename, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        try:
                            if model == BlockedNumberDB:
                                obj = BlockedNumberDB(
                                    phone_number=row['phone_number'],
                                    caller_name=row.get('caller_name'),
                                    block_reason=row['block_reason'],
                                    block_date=datetime.now(),
                                    is_permanent=True
                                )
                            elif model == CallerDB:
                                obj = CallerDB(
                                    phone_number=row['phone_number'],
                                    caller_name=row.get('caller_name'),
                                    reputation_score=float(row.get('reputation_score', 5.0)),
                                    total_reports=int(row.get('total_reports', 0)),
                                    call_frequency=int(row.get('call_frequency', 0)),
                                    risk_analysis=row.get('risk_analysis'),
                                    last_called=datetime.now()
                                )
                            elif model == CallDB:
                                risk_score = int(row.get('risk_score', 0))
                                obj = CallDB(
                                    caller_number=row['caller_number'],
                                    caller_name=row.get('caller_name'),
                                    receiver_number=row['receiver_number'],
                                    duration=int(row.get('duration', 0)),
                                    call_type=row.get('call_type', 'Incoming'),
                                    risk_score=risk_score,
                                    status=row.get('status', 'Safe'),
                                    threat_level=row.get('threat_level', 'Low'),
                                    is_blocked=risk_score >= 90,
                                    block_reason=f"Auto-blocked: Risk score {risk_score}" if risk_score >= 90 else None
                                )
                            elif model == AlertDB:
                                obj = AlertDB(
                                    caller_number=row['caller_number'],
                                    alert_type=row['alert_type'],
                                    threat_level=row.get('threat_level', 'Medium'),
                                    message=row['message'],
                                    is_read=False
                                )
                            elif model == ReportDB:
                                obj = ReportDB(
                                    caller_number=row['caller_number'],
                                    report_type=row['report_type'],
                                    description=row.get('description')
                                )
                            else:
                                continue
                            
                            db.add(obj)
                            count += 1
                        except Exception as e:
                            print(f"    Error on row {count}: {e}")
                    
                    db.commit()
                    print(f"  Imported {count} records for {model.__tablename__}")
            else:
                print(f"\nFile not found: {filename}")
        
        # Show final counts
        print("\n" + "="*50)
        print("FINAL COUNTS AFTER IMPORT:")
        print("="*50)
        print(f"Calls: {db.query(CallDB).count()}")
        print(f"Callers: {db.query(CallerDB).count()}")
        print(f"Alerts: {db.query(AlertDB).count()}")
        print(f"Reports: {db.query(ReportDB).count()}")
        print(f"Blocked Numbers: {db.query(BlockedNumberDB).count()}")
        
        # Show auto-blocked calls
        auto_blocked = db.query(CallDB).filter(CallDB.risk_score >= 90).count()
        print(f"Auto-blocked calls (risk >=90): {auto_blocked}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Checking CSV files...")
    csv_files = list_csv_files()
    
    if not csv_files:
        print("\n[WARNING] No CSV files found in current directory!")
        print("Please make sure your CSV files are in:")
        print(os.getcwd())
    else:
        print("\nChecking file contents...")
        for f in csv_files:
            check_csv_content(f)
        
        print("\n" + "="*50)
        response = input("Do you want to import these files? (yes/no): ")
        if response.lower() == 'yes':
            manual_import()