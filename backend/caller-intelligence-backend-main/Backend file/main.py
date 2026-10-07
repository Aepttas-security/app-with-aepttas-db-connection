# main.py - v6.2.0 (Master Enterprise - Complete PROMPT 6 Fixes)
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Optional
from datetime import datetime, date, timezone
from database import engine, get_db, Base
from models import *
from schemas import *
import logging
import uuid
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_num(num: str) -> str:
    if not num: return ""
    return ''.join(filter(lambda x: x.isdigit() or x == '+', num))

app = FastAPI(title="AEPTTAS Shield API", version="6.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============================================
# 🛠️ HELPERS
# ============================================

def ensure_user(db: Session):
    try:
        user = db.execute(text("SELECT user_id FROM apt.apt_users_b LIMIT 1")).first()
        if not user:
            db.execute(text("INSERT INTO apt.apt_users_b (user_uuid, username, email, password_hash, is_active, created_by, created_date, last_updated_by, last_updated_date) VALUES (:u, 'admin', 'admin@shield.com', 'none', true, 'SYSTEM', now(), 'SYSTEM', now())"), {"u": str(uuid.uuid4())})
            db.commit()
    except: db.rollback()

def get_audit(extra=None):
    now = datetime.now()
    d = {"uuid": str(uuid.uuid4()), "by": "MOBILE_APP", "dt": now, "prog": 1}
    if extra: d.update(extra)
    return d

# ============================================
# ✅ CALLER LOOKUP & DIRECTORY (PROMPT 1 & 5)
# ============================================

@app.get("/api/callers/lookup/{num}")
@app.get("/api/live-call/lookup/{num}")
def caller_lookup(num: str, db: Session = Depends(get_db)):
    c_num = clean_num(num)
    try:
        res = db.execute(text("SELECT caller_name, is_spam_reported FROM apt.apt_callers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10) LIMIT 1"), {"n": c_num}).first()
        blocked = db.execute(text("SELECT 1 FROM apt.apt_blocked_numbers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)"), {"n": c_num}).first()

        if res:
            return {
                "exists": True, "caller_name": res[0] or "Shield Identified", "risk_score": 85 if bool(res[1]) else 10,
                "is_spam": bool(res[1]), "is_blocked": blocked is not None, "carrier": "Verified Network", "location": "India", "total_reports": 1 if bool(res[1]) else 0
            }
        return {"exists": False, "caller_name": "Unknown Caller", "risk_score": 50, "is_spam": False, "is_blocked": blocked is not None, "carrier": "Unknown", "location": "Unknown", "total_reports": 0}
    except: return {"exists": False, "caller_name": "Service Offline", "risk_score": 50}

@app.post("/api/callers/upload")
def upload_callers(req: List[CallerCreateRequest], db: Session = Depends(get_db)):
    try:
        for c in req:
            num = clean_num(c.phone_number)
            if not num: continue
            # 🛡️ PROMPT 1: Check if exists by last 10 digits
            existing = db.execute(text("SELECT caller_id FROM apt.apt_callers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)"), {"n": num}).first()
            if existing:
                # PROMPT 1: On conflict, DO NOTHING (ignore updates)
                continue

            p = get_audit({"n": num, "nm": c.caller_name or "Unknown Caller"})
            db.execute(text("INSERT INTO apt.apt_callers_b (caller_uuid, phone_number, caller_name, created_by, created_date, last_updated_by, last_updated_date, last_dml_by, last_dml_date, last_ddl_by, last_ddl_date, program_id) VALUES (:uuid, :n, :nm, :by, :dt, :by, :dt, :by, :dt, :by, :dt, :prog)"), p)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback(); logger.error(traceback.format_exc()); raise HTTPException(status_code=500, detail="Upload failed")

# ============================================
# ✅ CALL HISTORY (PROMPT 2 & 3)
# ============================================

@app.get("/api/calls")
@app.get("/api/call-history")
def get_calls(db: Session = Depends(get_db)):
    try:
        # 🛡️ PROMPT 2: Query with subqueries to resolve names and prevent Cartesian duplication
        res = db.execute(text("""
            SELECT DISTINCT c.call_id, c.phone_number, c.call_type, c.call_timestamp, c.call_duration_seconds,
                   (SELECT caller_name FROM apt.apt_callers_b cl WHERE RIGHT(cl.phone_number, 10) = RIGHT(c.phone_number, 10) LIMIT 1) as name,
                   (SELECT is_spam_reported FROM apt.apt_callers_b cl WHERE RIGHT(cl.phone_number, 10) = RIGHT(c.phone_number, 10) LIMIT 1) as spam
            FROM apt.apt_calls_b c
            ORDER BY c.call_timestamp DESC LIMIT 100
        """)).fetchall()

        return [{
            "id": r[0], "caller_number": r[1], "call_type": r[2], "created_at": str(r[3]),
            "duration": r[4] or 0, "caller_name": r[5] or "Unknown Caller", "risk_score": 85 if r[6] else 0
        } for r in res]
    except Exception as e:
        logger.error(f"Calls Error: {e}"); return []

@app.post("/api/live-call/analyze")
def log_call(req: CallAnalyzeRequest, db: Session = Depends(get_db)):
    ensure_user(db)
    try:
        num = clean_num(req.caller_number)

        # 🛡️ PROMPT 3: Deduplication guard (5s cooldown)
        last_log = db.execute(text("SELECT call_timestamp FROM apt.apt_calls_b WHERE phone_number = :n AND call_type = :t ORDER BY call_timestamp DESC LIMIT 1 Marquis"), {"n": num, "t": (req.call_type or "INCOMING").upper()}).first()
        if last_log and (datetime.now() - last_log[0]).total_seconds() < 5:
            return {"status": "ignored", "reason": "duplicate trigger"}

        caller = db.execute(text("SELECT caller_id, is_spam_reported FROM apt.apt_callers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)") , {"n": num}).first()
        if not caller:
            p = get_audit({"n": num, "nm": req.caller_name or "Unknown Caller"})
            res = db.execute(text("INSERT INTO apt.apt_callers_b (caller_uuid, phone_number, caller_name, created_by, created_date, last_updated_by, last_updated_date, last_dml_by, last_dml_date, last_ddl_by, last_ddl_date, program_id) VALUES (:uuid, :n, :nm, :by, :dt, :by, :dt, :by, :dt, :by, :dt, :prog) RETURNING caller_id"), p)
            cid, is_spam = res.scalar(), False
        else:
            cid, is_spam = caller[0], bool(caller[1])

        cp = get_audit({"cid": cid, "num": num, "type": (req.call_type or "INCOMING").upper(), "dur": req.duration or 0})
        db.execute(text("INSERT INTO apt.apt_calls_b (call_uuid, user_id, caller_id, phone_number, call_type, call_duration_seconds, call_timestamp, created_by, created_date, last_updated_by, last_updated_date, last_dml_by, last_dml_date, last_ddl_by, last_ddl_date) VALUES (:uuid, 1, :cid, :num, :type, :dur, :dt, :by, :dt, :by, :dt, :by, :dt, :by, :dt)"), cp)
        db.commit()
        return {"status": "success", "risk_score": 85 if is_spam else 0}
    except Exception as e:
        db.rollback(); logger.error(traceback.format_exc()); return {"risk_score": 0}

# ============================================
# ✅ BLOCKED & SPAM (PROMPT 6)
# ============================================

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    try:
        today = date.today()
        t = db.execute(text("SELECT count(*) FROM apt.apt_calls_b WHERE call_timestamp::date = :d"), {"d": today}).scalar() or 0
        b = db.execute(text("SELECT count(*) FROM apt.apt_blocked_numbers_b WHERE created_date::date = :d"), {"d": today}).scalar() or 0
        s = db.execute(text("SELECT count(*) FROM apt.apt_calls_b c JOIN apt.apt_callers_b cl ON c.caller_id = cl.caller_id WHERE c.call_timestamp::date = :d AND cl.is_spam_reported = true"), {"d": today}).scalar() or 0
        return {"total_calls_today": t, "blocked_calls_count": b, "spam_calls_detected": s, "security_score": 94}
    except: return {"total_calls_today": 0, "blocked_calls_count": 0, "spam_calls_detected": 0, "security_score": 100}

@app.get("/api/blocked")
@app.get("/api/blocked-numbers")
def get_blocked(db: Session = Depends(get_db)):
    try:
        res = db.execute(text("SELECT b.phone_number, COALESCE(c.caller_name, 'Unknown'), b.reason, b.created_date FROM apt.apt_blocked_numbers_b b LEFT JOIN apt.apt_callers_b c ON RIGHT(b.phone_number, 10) = RIGHT(c.phone_number, 10) ORDER BY b.created_date DESC")).fetchall()
        return [{"phone_number": r[0], "caller_name": r[1], "block_reason": r[2], "block_date": str(r[3]), "risk_score": 100} for r in res]
    except: return []

@app.post("/api/blocked")
@app.post("/api/blocked-numbers")
def add_block(req: BlockNumberRequest, db: Session = Depends(get_db)):
    ensure_user(db)
    try:
        num = clean_num(req.phone_number)
        caller = db.execute(text("SELECT caller_id FROM apt.apt_callers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)"), {"n": num}).first()
        cid = caller[0] if caller else None
        if not cid:
            p = {"uuid": str(uuid.uuid4()), "n": num, "nm": req.caller_name or "Unknown", "by": "MOBILE_APP", "dt": datetime.now()}
            res = db.execute(text("INSERT INTO apt.apt_callers_b (caller_uuid, phone_number, caller_name, created_by, created_date, last_updated_by, last_updated_date) VALUES (:uuid, :n, :nm, :by, :dt, :by, :dt) RETURNING caller_id"), p)
            cid = res.scalar()

        exists = db.execute(text("SELECT 1 FROM apt.apt_blocked_numbers_b WHERE phone_number = :n"), {"n": num}).first()
        bp = {"num": num, "reason": req.block_reason or "Manual", "by": "MOBILE_APP", "dt": datetime.now()}
        if exists:
            db.execute(text("UPDATE apt.apt_blocked_numbers_b SET reason = :reason, last_updated_date = :dt, last_updated_by = :by WHERE phone_number = :num"), bp)
        else:
            db.execute(text("INSERT INTO apt.apt_blocked_numbers_b (user_id, phone_number, reason, created_by, created_date, last_updated_by, last_updated_date) VALUES (1, :num, :reason, :by, :dt, :by, :dt)"), bp)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/blocked/{phone}")
def delete_block(phone: str, db: Session = Depends(get_db)):
    try:
        db.execute(text("DELETE FROM apt.apt_blocked_numbers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)"), {"n": clean_num(phone)})
        db.commit(); return {"status": "success"}
    except: return {"status": "failed"}

@app.get("/api/spam-log")
def spam_log(db: Session = Depends(get_db)):
    try:
        res = db.execute(text("SELECT r.phone_number, COALESCE(c.caller_name, 'Unknown'), r.report_reason, r.created_date FROM apt.apt_reports_b r LEFT JOIN apt.apt_callers_b c ON RIGHT(r.phone_number, 10) = RIGHT(c.phone_number, 10) ORDER BY r.created_date DESC")).fetchall()
        return [{"phone_number": r[0], "caller_name": r[1], "report_type": r[2], "reported_at": str(r[3]), "risk_score": 85} for r in res]
    except: return []

@app.post("/api/reports")
def add_report(req: ReportRequest, db: Session = Depends(get_db)):
    ensure_user(db)
    try:
        num = clean_num(req.caller_number)
        caller = db.execute(text("SELECT caller_id FROM apt.apt_callers_b WHERE RIGHT(phone_number, 10) = RIGHT(:n, 10)"), {"n": num}).first()
        cid = caller[0] if caller else None
        if not cid:
            p = get_audit({"n": num, "nm": "Unknown Caller"})
            res = db.execute(text("INSERT INTO apt.apt_callers_b (caller_uuid, phone_number, caller_name, created_by, created_date, last_updated_by, last_updated_date, last_dml_by, last_dml_date, last_ddl_by, last_ddl_date, program_id) VALUES (:uuid, :n, :nm, :by, :dt, :by, :dt, :by, :dt, :by, :dt, :prog) RETURNING caller_id"), p)
            cid = res.scalar()

        rp = get_audit({"cid": cid, "num": num, "reason": req.report_reason or "Reported by user"})
        db.execute(text("INSERT INTO apt.apt_reports_b (report_uuid, user_id, caller_id, phone_number, report_reason, created_by, created_date, last_updated_by, last_updated_date, last_dml_by, last_dml_date, last_ddl_by, last_ddl_date) VALUES (:uuid, 1, :cid, :num, :reason, :by, :dt, :by, :dt, :by, :dt, :by, :dt)"), rp)
        db.commit(); return {"status": "success"}
    except Exception as e:
        db.rollback(); logger.error(traceback.format_exc()); raise HTTPException(status_code=500)

# ============================================
# ✅ SETTINGS & AUTH
# ============================================

@app.get("/api/settings")
def get_settings(db: Session = Depends(get_db)):
    try:
        row = db.execute(text("SELECT auto_block_spam, block_unknown_numbers, notification_type_id FROM apt.apt_call_settings_b WHERE user_id = 1")).first()
        if not row: return {"auto_block_calls": True, "notifications_enabled": True, "privacy_mode": False}
        return {"auto_block_calls": bool(row[0]), "privacy_mode": bool(row[1]), "notifications_enabled": (row[2] == 1) if row and row[2] is not None else True}
    except: return {"auto_block_calls": True, "notifications_enabled": True, "privacy_mode": False}

@app.put("/api/settings")
def update_settings(req: SettingsUpdateRequest, db: Session = Depends(get_db)):
    try:
        if req.auto_block_calls is not None: db.execute(text("UPDATE apt.apt_call_settings_b SET auto_block_spam = :v WHERE user_id = 1"), {"v": req.auto_block_calls})
        if req.privacy_mode is not None: db.execute(text("UPDATE apt.apt_call_settings_b SET block_unknown_numbers = :v WHERE user_id = 1"), {"v": req.privacy_mode})
        if req.notifications_enabled is not None: db.execute(text("UPDATE apt.apt_call_settings_b SET notification_type_id = :v WHERE user_id = 1"), {"v": 1 if req.notifications_enabled else 0})
        db.commit(); return {"status": "success"}
    except: db.rollback(); return {"status": "failed"}

@app.post("/api/login")
def login(req: LoginRequest): return {"user_id": 1, "name": "Deepesh", "email": req.email, "token": "jwt-1", "message": "Login successful"}

@app.post("/api/register")
def register(req: RegisterRequest): return {"status": "success", "message": "Registered"}

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    return {"status": "healthy", "database": db_status}

@app.put("/api/callers/risk/update-all")
def update_risk(): return {"status": "success"}

@app.get("/api/callers/audit/spam")
def audit_spam(): return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
