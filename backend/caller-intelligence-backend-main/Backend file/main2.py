# main.py - Complete working version with all endpoints
import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from database import engine, get_db, Base
from models import *
from schemas import *
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

# App Config
app = FastAPI(
    title="Call Management API",
    version="2.0.0",
    description="Mobile Security Suite 2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AUTH ====================
def verify_api_key(x_api_key: str = Header(None)):
    return "test-user"

# ==================== HELPERS ====================
def calculate_risk_score(caller_number: str, db: Session) -> int:
    caller = db.query(CallerDB).filter(CallerDB.phone_number == caller_number).first()
    score = 0
    if caller:
        score += min(caller.total_reports * 10, 50)
        score += max(0, int((10 - caller.reputation_score) * 5))
        if caller.call_frequency > 10:
            score += 20
        elif caller.call_frequency > 5:
            score += 10
    blocked = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == caller_number).first()
    if blocked:
        score += 30
    return min(score, 100)

def get_final_risk_score(app_risk_score: int, auto_risk_score: int):
    final_score = max(app_risk_score, auto_risk_score)
    if final_score >= 94:
        return final_score, "Critical Scam", "Critical"
    elif final_score >= 80:
        return final_score, "Scam", "High"
    elif final_score >= 60:
        return final_score, "Spam", "High"
    elif final_score >= 40:
        return final_score, "Suspicious", "Medium"
    else:
        return final_score, "Safe", "Low"

# ==================== 1. DASHBOARD ====================
@app.get("/api/dashboard", response_model=DashboardStats)
def get_dashboard(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    today = datetime.now(timezone.utc).date()
    today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    
    total_calls_today = db.query(CallDB).filter(CallDB.created_at >= today_start).count()
    spam_calls = db.query(CallDB).filter(
        CallDB.created_at >= today_start,
        CallDB.status.in_(["Spam", "Scam", "Critical Scam"])
    ).count()
    blocked_calls = db.query(CallDB).filter(
        CallDB.created_at >= today_start,
        CallDB.is_blocked == True
    ).count()
    
    all_calls_today = db.query(CallDB).filter(CallDB.created_at >= today_start).all()
    avg_risk = sum(c.risk_score for c in all_calls_today) / len(all_calls_today) if all_calls_today else 0
    security_score = max(0, 100 - avg_risk)
    
    recent_alerts = db.query(AlertDB).order_by(AlertDB.created_at.desc()).limit(5).all()
    
    return DashboardStats(
        total_calls_today=total_calls_today,
        spam_calls_detected=spam_calls,
        blocked_calls_count=blocked_calls,
        security_score=security_score,
        recent_alerts=recent_alerts
    )

# ==================== 2. LIVE CALL ANALYZE ====================
@app.post("/api/live-call/analyze")
def analyze_incoming_call(call: CallCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    blocked = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == call.caller_number).first()
    
    app_risk_score = call.risk_score
    auto_risk_score = calculate_risk_score(call.caller_number, db)
    final_score, status, threat_level = get_final_risk_score(app_risk_score, auto_risk_score)
    
    should_block = final_score >= 90 or blocked is not None
    block_reason = None
    if should_block:
        block_reason = f"Auto-blocked: Risk score {final_score}" if final_score >= 90 else f"Number is in blocked list"
    
    new_call = CallDB(
        caller_number=call.caller_number,
        caller_name=call.caller_name,
        receiver_number=call.receiver_number,
        duration=call.duration,
        call_type=call.call_type.value,
        risk_score=final_score,
        threat_level=threat_level,
        status=status,
        is_blocked=should_block,
        block_reason=block_reason,
        block_date=datetime.now(timezone.utc) if should_block else None
    )
    
    caller_record = db.query(CallerDB).filter(CallerDB.phone_number == call.caller_number).first()
    if not caller_record:
        caller_record = CallerDB(
            phone_number=call.caller_number,
            caller_name=call.caller_name,
            reputation_score=5.0,
            total_reports=0,
            call_frequency=1,
            risk_analysis=status,
            last_called=datetime.now(timezone.utc)
        )
        db.add(caller_record)
    else:
        caller_record.call_frequency += 1
        caller_record.last_called = datetime.now(timezone.utc)
        if call.caller_name:
            caller_record.caller_name = call.caller_name
    
    db.add(new_call)
    db.flush()
    
    new_report = ReportDB(
        call_id=new_call.id,
        caller_number=call.caller_number,
        report_type=status,
        description=f"Call analyzed - Risk: {final_score}, Status: {status}"
    )
    db.add(new_report)
    
    if final_score >= 80:
        alert = AlertDB(
            call_id=new_call.id,
            caller_number=call.caller_number,
            alert_type="High Risk Call",
            threat_level=threat_level,
            message=f"High risk call from {call.caller_number} - Risk: {final_score}",
            is_read=False
        )
        db.add(alert)
    
    if should_block and not blocked:
        new_blocked = BlockedNumberDB(
            phone_number=call.caller_number,
            caller_name=call.caller_name,
            block_reason=block_reason,
            is_permanent=True
        )
        db.add(new_blocked)
    
    db.commit()
    db.refresh(new_call)
    
    return {
        "call_id": new_call.id,
        "report_id": new_report.id,
        "caller_number": call.caller_number,
        "app_risk_score": app_risk_score,
        "auto_calculated_risk": auto_risk_score,
        "final_risk_score": final_score,
        "status": status,
        "threat_level": threat_level,
        "is_blocked": should_block,
        "block_reason": block_reason,
        "auto_blocked": should_block and not blocked,
        "message": "Call analyzed and stored successfully"
    }

# ==================== 3. CALLER INTELLIGENCE ====================
@app.get("/api/caller/{phone_number}", response_model=CallerResponse)
def get_caller_intelligence(phone_number: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    caller = db.query(CallerDB).filter(CallerDB.phone_number == phone_number).first()
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found")
    return caller

@app.get("/api/caller/{phone_number}/risk-analysis")
def get_risk_analysis(phone_number: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    caller = db.query(CallerDB).filter(CallerDB.phone_number == phone_number).first()
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found")
    auto_risk = calculate_risk_score(phone_number, db)
    is_blocked = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == phone_number).first() is not None
    return {
        "caller_details": caller,
        "reputation_score": caller.reputation_score,
        "auto_calculated_risk": auto_risk,
        "call_frequency": caller.call_frequency,
        "risk_score": auto_risk,
        "is_blocked": is_blocked,
        "recent_calls": db.query(CallDB).filter(CallDB.caller_number == phone_number).count()
    }

# ==================== 4. CALL HISTORY ====================
@app.get("/api/calls", response_model=List[CallResponse])
def get_call_history(call_type: Optional[str] = None, search: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    query = db.query(CallDB)
    if call_type:
        query = query.filter(CallDB.call_type == call_type)
    if search:
        query = query.filter(
            (CallDB.caller_number.contains(search)) |
            (CallDB.receiver_number.contains(search)) |
            (CallDB.caller_name.contains(search))
        )
    return query.order_by(CallDB.created_at.desc()).offset(skip).limit(limit).all()

# ==================== 5. SPAM/BLOCKED CALLS ====================
@app.get("/api/spam-calls", response_model=List[CallResponse])
def get_spam_calls(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(CallDB).filter(CallDB.status.in_(["Spam", "Scam", "Critical Scam", "Blocked"])).order_by(CallDB.created_at.desc()).offset(skip).limit(limit).all()

@app.get("/api/blocked-calls", response_model=List[CallResponse])
def get_blocked_calls(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(CallDB).filter(CallDB.is_blocked == True).order_by(CallDB.created_at.desc()).offset(skip).limit(limit).all()

# ==================== 6. BLOCKED NUMBERS ====================
@app.get("/api/blocked-numbers", response_model=List[BlockedNumberResponse])
def get_blocked_numbers(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    return db.query(BlockedNumberDB).order_by(BlockedNumberDB.block_date.desc()).offset(skip).limit(limit).all()

@app.post("/api/blocked-numbers", response_model=BlockedNumberResponse)
def block_number(block_data: BlockedNumberCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    existing = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == block_data.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Number already blocked")
    blocked = BlockedNumberDB(**block_data.model_dump())
    db.add(blocked)
    db.commit()
    db.refresh(blocked)
    return blocked

@app.delete("/api/blocked-numbers/{phone_number}")
def unblock_number(phone_number: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    blocked = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == phone_number).first()
    if not blocked:
        raise HTTPException(status_code=404, detail="Number not blocked")
    db.delete(blocked)
    db.commit()
    return {"message": f"Number {phone_number} unblocked successfully"}

# ==================== 7. ALERTS ====================
@app.get("/api/alerts", response_model=List[AlertResponse])
def get_alerts(alert_type: Optional[str] = None, threat_level: Optional[str] = None, unread_only: bool = False, skip: int = 0, limit: int = 50, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    query = db.query(AlertDB)
    if alert_type:
        query = query.filter(AlertDB.alert_type == alert_type)
    if threat_level:
        query = query.filter(AlertDB.threat_level == threat_level)
    if unread_only:
        query = query.filter(AlertDB.is_read == False)
    return query.order_by(AlertDB.created_at.desc()).offset(skip).limit(limit).all()

@app.put("/api/alerts/{alert_id}/read")
def mark_alert_read(alert_id: int, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    alert = db.query(AlertDB).filter(AlertDB.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}

# ==================== 8. REPORTS ====================
@app.post("/api/reports", response_model=ReportResponse)
def report_caller(report: ReportCreate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    new_report = ReportDB(**report.model_dump())
    db.add(new_report)
    
    caller = db.query(CallerDB).filter(CallerDB.phone_number == report.caller_number).first()
    if not caller:
        caller = CallerDB(phone_number=report.caller_number, reputation_score=5.0, total_reports=0)
        db.add(caller)
    
    caller.total_reports += 1
    caller.reputation_score = max(0, caller.reputation_score - 0.5)
    
    if caller.total_reports >= 3 or caller.reputation_score <= 3.0:
        existing = db.query(BlockedNumberDB).filter(BlockedNumberDB.phone_number == report.caller_number).first()
        if not existing:
            blocked = BlockedNumberDB(
                phone_number=report.caller_number,
                caller_name=caller.caller_name,
                block_reason=f"Auto-blocked due to {caller.total_reports} reports",
                is_permanent=True
            )
            db.add(blocked)
    
    alert = AlertDB(
        caller_number=report.caller_number,
        alert_type=report.report_type.value,
        threat_level="Medium",
        message=f"New {report.report_type.value} report from user",
        is_read=False
    )
    db.add(alert)
    
    db.commit()
    db.refresh(new_report)
    return new_report

# ==================== 9. SETTINGS ====================
@app.get("/api/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    settings = db.query(SettingsDB).first()
    if not settings:
        settings = SettingsDB(
            auto_block_calls=True,
            notifications_enabled=True,
            detection_sensitivity=70,
            privacy_mode=False,
            auto_block_threshold=80
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@app.put("/api/settings")
def update_settings(settings_update: SettingsUpdate, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    settings = db.query(SettingsDB).first()
    if not settings:
        settings = SettingsDB()
        db.add(settings)
    
    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    
    settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(settings)
    return settings

# ============ NUMBER SEARCH - SINGLE ============
@app.get("/api/number-search/{phone_number}")
def search_number(phone_number: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Search for a phone number in the database"""
    # Clean the phone number - remove spaces, dashes, parentheses, plus signs
    clean_number = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
    print(f"🔍 Searching for: {phone_number} (cleaned: {clean_number})")
    
    try:
        # Get ALL callers and check each one
        all_callers = db.query(CallerDB).all()
        
        result = None
        for caller in all_callers:
            # Clean the stored phone number
            stored_clean = caller.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace("+", "")
            
            # Check if the cleaned number matches or contains the search
            if clean_number in stored_clean or stored_clean in clean_number:
                result = caller
                print(f"✅ Found match: {caller.caller_name} - {caller.phone_number}")
                break
        
        # Also try direct database query as fallback
        if not result:
            result = db.query(CallerDB).filter(
                (CallerDB.phone_number.ilike(f"%{clean_number}%")) |
                (CallerDB.phone_number.ilike(f"%{phone_number}%"))
            ).first()
        
        if result:
            print(f"✅ Found: {result.caller_name} - {result.phone_number}")
            return {
                "caller_name": result.caller_name or "Unknown Caller",
                "phone_number": result.phone_number,
                "risk_score": result.reputation_score or 50,
                "is_blocked": False,
                "call_frequency": result.call_frequency or 0,
                "carrier": getattr(result, 'carrier', 'Unknown'),
                "location": getattr(result, 'location', 'Unknown'),
                "reputation_score": result.reputation_score or 50,
            }
    except Exception as e:
        print(f"❌ Search error: {e}")
    
    # Return default if not found
    return {
        "caller_name": "Unknown Caller",
        "phone_number": phone_number,
        "risk_score": 30,
        "is_blocked": False,
        "call_frequency": 0,
        "carrier": "Unknown",
        "location": "Unknown",
        "reputation_score": 30,
    }
# ==================== 10a. ADD NEW USER ====================
@app.post("/api/users/add")
def add_new_user(
    user_data: dict,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Add a new user/caller to the database"""
    
    phone_number = user_data.get("phone_number")
    caller_name = user_data.get("caller_name")
    
    if not phone_number or not caller_name:
        raise HTTPException(status_code=400, detail="Phone number and name are required")
    
    # Check if number already exists
    existing = db.query(CallerDB).filter(CallerDB.phone_number == phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Number already exists")
    
    # Create new caller
    new_caller = CallerDB(
        phone_number=phone_number,
        caller_name=caller_name,
        reputation_score=5.0,
        total_reports=0,
        call_frequency=0,
        risk_analysis="Normal",
        last_called=datetime.now(timezone.utc)
    )
    
    db.add(new_caller)
    db.commit()
    db.refresh(new_caller)
    
    return {
        "message": "User added successfully",
        "caller": {
            "id": new_caller.id,
            "phone_number": new_caller.phone_number,
            "caller_name": new_caller.caller_name
        }
    }
# ==================== 10b. NUMBER SEARCH - ALL RESULTS ====================
@app.get("/api/number-search/{phone_number}/all")
def search_all_numbers(phone_number: str, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Return all matching numbers"""
    clean_number = ''.join(filter(str.isdigit, phone_number))
    
    # Get all matching callers
    callers = db.query(CallerDB).filter(
        CallerDB.phone_number.like(f'%{clean_number}%')
    ).all()
    
    results = []
    for caller in callers:
        blocked = db.query(BlockedNumberDB).filter(
            BlockedNumberDB.phone_number == caller.phone_number
        ).first()
        
        results.append({
            "phone_number": caller.phone_number,
            "caller_name": caller.caller_name or "Unknown Caller",
            "reputation_score": caller.reputation_score,
            "risk_score": calculate_risk_score(caller.phone_number, db),
            "risk_analysis": caller.risk_analysis or "Unknown",
            "total_reports": caller.total_reports,
            "call_frequency": caller.call_frequency,
            "is_blocked": blocked is not None
        })
    
    return results
# ==================== 10b. SCAM ALERTS ====================
@app.get("/api/scam-alerts")
def get_scam_alerts(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    """Get latest scam alerts/news"""
    mock_alerts = [
        {
            "id": "1",
            "title": "🚨 New IRS Scam Alert",
            "description": "Scammers are calling claiming to be from the IRS. They demand immediate payment via gift cards. Never share personal information over the phone.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "critical",
            "source": "FTC Alert"
        },
        {
            "id": "2",
            "title": "⚠️ Bank OTP Phishing",
            "description": "New scam targeting bank customers. Callers ask for OTP codes to 'verify' your account. Banks never ask for OTP over the phone.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "high",
            "source": "Cyber Security"
        },
        {
            "id": "3",
            "title": "📱 Tech Support Scam",
            "description": "Fake Microsoft support calls claiming your computer has a virus. Legitimate tech companies never initiate unsolicited support calls.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "medium",
            "source": "Tech Safety"
        },
        {
            "id": "4",
            "title": "💳 Credit Card Fraud Alert",
            "description": "Scammers pretending to be from your bank about suspicious transactions. Always hang up and call the number on the back of your card.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "high",
            "source": "Bank Security"
        },
        {
            "id": "5",
            "title": "📦 Package Delivery Scam",
            "description": "Fake delivery notifications asking for payment to release packages. Legitimate delivery services never ask for payment over the phone.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "medium",
            "source": "Postal Alert"
        },
        {
            "id": "6",
            "title": "🔴 Emergency Alert: New Scam Pattern",
            "description": "A new wave of scams targeting elderly citizens has been detected. Scammers are posing as family members in distress.",
            "date": datetime.now(timezone.utc).isoformat(),
            "severity": "critical",
            "source": "National Security"
        }
    ]
    return mock_alerts
# ==================== 11. ANALYTICS ====================
@app.get("/api/analytics/daily")
def get_daily_stats(days: int = 7, db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    stats = []
    for i in range(days):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        
        total_calls = db.query(CallDB).filter(CallDB.created_at.between(day_start, day_end)).count()
        spam_calls = db.query(CallDB).filter(
            CallDB.created_at.between(day_start, day_end),
            CallDB.status.in_(["Spam", "Scam", "Critical Scam"])
        ).count()
        blocked_calls = db.query(CallDB).filter(
            CallDB.created_at.between(day_start, day_end),
            CallDB.is_blocked == True
        ).count()
        
        stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total_calls": total_calls,
            "spam_calls": spam_calls,
            "blocked_calls": blocked_calls,
            "safe_calls": total_calls - spam_calls
        })
    return stats

@app.get("/api/analytics/blocked-stats")
def get_blocked_stats(db: Session = Depends(get_db), api_key: str = Depends(verify_api_key)):
    total_blocked_calls = db.query(CallDB).filter(CallDB.is_blocked == True).count()
    auto_blocked_calls = db.query(CallDB).filter(CallDB.is_blocked == True, CallDB.block_reason.like("Auto-blocked%")).count()
    manual_blocked_calls = total_blocked_calls - auto_blocked_calls
    
    return {
        "total_blocked_calls": total_blocked_calls,
        "auto_blocked_calls": auto_blocked_calls,
        "manual_blocked_calls": manual_blocked_calls,
        "auto_block_percentage": (auto_blocked_calls / total_blocked_calls * 100) if total_blocked_calls > 0 else 0
    }

# ==================== 12. HEALTH CHECK ====================
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/health")
def health():
    return {"status": "success", "message": "Backend Connected"}

# ==================== 13. DB TEST ====================
@app.get("/db-test")
def db_test(db: Session = Depends(get_db)):
    from sqlalchemy import text
    result = db.execute(text("SELECT current_database()"))
    return {"status": "Connected", "database": result.scalar()}

print("✅ Backend ready!")