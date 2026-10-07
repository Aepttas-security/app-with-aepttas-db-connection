# app/models/Screentime.py
from pydantic import BaseModel, Field

class SetDailyLimitRequest(BaseModel):
    daily_limit_minutes: int = Field(..., ge=0, le=1440, description="Cannot exceed 24 hours (1440 mins).")

class LockOverrideRequest(BaseModel):
    is_locked: bool

class ScreenTimeDashboardResponse(BaseModel):
    child_id: str
    daily_limit_minutes: int
    current_usage_minutes: int
    is_locked_remotely: bool

# Initial mockup metrics matching your exact UI display requirements
MOCK_SCREENTIME_DB = {
    1: {  # Alex
        "daily_limit_minutes": 240,     # tracks the 4-hour mark limit
        "current_usage_minutes": 135,   # tracks the 2h 15m active use
        "is_locked_remotely": False
    },
    2: {  # Emma
        "daily_limit_minutes": 120,     # tracks a 2-hour limit
        "current_usage_minutes": 45,    # tracks 45 minutes active use
        "is_locked_remotely": False
    }
}