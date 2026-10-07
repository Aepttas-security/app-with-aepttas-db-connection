# schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============================================
# 📦 ENUMS
# ============================================

class CallTypeEnum(str, Enum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    MISSED = "MISSED"
    BLOCKED = "BLOCKED"

class ReportTypeEnum(str, Enum):
    SPAM = "Spam"
    SCAM = "Scam"
    HARASSMENT = "Harassment"
    FRAUD = "Fraud"
    OTHER = "Other"

# ============================================
# 📦 REQUEST MODELS (What Frontend Sends)
# ============================================

class CallAnalyzeRequest(BaseModel):
    """
    Request model for /api/live-call/analyze
    This is what the frontend sends when analyzing a call
    """
    caller_number: str = Field(..., description="The phone number of the caller (required)")
    caller_name: Optional[str] = Field(None, description="Name of the caller (optional)")
    receiver_number: Optional[str] = Field("Unknown", description="Your phone number (optional)")
    duration: Optional[int] = Field(0, description="Call duration in seconds (optional)")
    call_type: Optional[str] = Field("Incoming", description="Incoming, Outgoing, or Missed (optional)")
    risk_score: Optional[int] = Field(0, description="Risk score from app 0-100 (optional)")
    user_id: Optional[int] = Field(1, description="User ID (optional)")
    identification_source: Optional[str] = Field(None, description="Source of ID (optional)")
    status: Optional[str] = Field(None, description="Call status (optional)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "caller_number": "+1 (555) 019-2831",
                "caller_name": "Father Leo",
                "receiver_number": "+1 (555) 000-0000",
                "duration": 45,
                "call_type": "Incoming",
                "risk_score": 5,
                "user_id": 1
            }
        }
    )

class LoginRequest(BaseModel):
    """Request model for /api/login"""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "email": "test@gmail.com",
                "password": "Test@123"
            }
        }
    )

class RegisterRequest(BaseModel):
    """Request model for /api/register"""
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    password: str = Field(..., description="User's password (min 6 characters)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "name": "Test User",
                "email": "test@gmail.com",
                "password": "Test@123"
            }
        }
    )

class BlockNumberRequest(BaseModel):
    """Request model for /api/blocked-numbers (POST)"""
    phone_number: str = Field(..., description="Phone number to block")
    caller_name: Optional[str] = Field(None, description="Name of the caller")
    block_reason: Optional[str] = Field("Blocked by user", description="Reason for blocking")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "phone_number": "+1 (555) 123-4567",
                "caller_name": "Spam Caller",
                "block_reason": "Telemarketing spam"
            }
        }
    )

class ReportRequest(BaseModel):
    """Request model for /api/reports (POST)"""
    caller_number: str = Field(..., description="Phone number being reported")
    report_reason: Optional[str] = Field("Reported by user", description="Reason for reporting")
    call_id: Optional[int] = Field(None, description="Associated call ID (optional)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "caller_number": "+1 (555) 123-4567",
                "report_reason": "Scam call - pretended to be from bank",
                "call_id": 1
            }
        }
    )

class SettingsUpdateRequest(BaseModel):
    """Request model for /api/settings (PUT)"""
    auto_block_calls: Optional[bool] = Field(None, description="Enable auto-block for high risk calls")
    block_unknown_numbers: Optional[bool] = Field(None, description="Block calls from unknown numbers")
    notifications_enabled: Optional[bool] = Field(None, description="Enable notifications")
    privacy_mode: Optional[bool] = Field(None, description="Enable privacy mode")
    auto_block_threshold: Optional[int] = Field(None, ge=0, le=100, description="Risk threshold for auto-block (0-100)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "auto_block_calls": True,
                "block_unknown_numbers": False,
                "notifications_enabled": True,
                "privacy_mode": False,
                "auto_block_threshold": 80
            }
        }
    )

class CallerCreateRequest(BaseModel):
    """Request model for /api/callers (POST)"""
    phone_number: str = Field(..., description="Phone number to add")
    caller_name: Optional[str] = Field("Unknown Caller", description="Name of the caller")
    is_spam_reported: Optional[bool] = Field(False, description="Whether this number is reported as spam")
    risk_level_id: Optional[int] = Field(1, description="Risk level ID (1-3)")

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "phone_number": "+1 (555) 123-4567",
                "caller_name": "New Contact",
                "is_spam_reported": False,
                "risk_level_id": 1
            }
        }
    )

class CallCreateRequest(BaseModel):
    """Request model for creating a call record"""
    caller_number: str = Field(..., description="Phone number of the caller")
    caller_name: Optional[str] = Field(None, description="Name of the caller")
    receiver_number: str = Field(..., description="Your phone number")
    duration: int = Field(0, description="Call duration in seconds")
    call_type: CallTypeEnum = Field(CallTypeEnum.INCOMING, description="Type of call")
    risk_score: int = Field(0, description="Risk score (0-100)")
    user_id: int = Field(1, description="User ID")

# ============================================
# 📦 RESPONSE MODELS (What Backend Returns)
# ============================================

class CallBase(BaseModel):
    """Base call model"""
    caller_number: str
    caller_name: Optional[str] = None
    receiver_number: str
    duration: int = 0
    call_type: CallTypeEnum = CallTypeEnum.INCOMING
    risk_score: int = 0

class CallCreate(CallBase):
    user_id: int = 1
    caller_id: Optional[int] = None

class CallResponse(BaseModel):
    """Response model for call history"""
    call_id: int
    caller_number: str
    caller_name: Optional[str] = None
    receiver_number: str
    duration: int
    call_type: str
    risk_score: int
    status: str
    threat_level: str
    is_blocked: bool
    block_reason: Optional[str] = None
    detection_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CallerResponse(BaseModel):
    """Response model for caller intelligence"""
    id: int
    phone_number: str
    caller_name: Optional[str] = None
    reputation_score: float
    total_reports: int
    call_frequency: int
    risk_analysis: Optional[str] = None
    last_called: Optional[datetime] = None
    carrier: Optional[str] = None
    location: Optional[str] = None
    is_blocked: bool = False
    risk_score: Optional[int] = None
    threat_level: Optional[str] = None
    status: Optional[str] = None
    is_spam_reported: Optional[bool] = None
    risk_level_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class CallerRiskAnalysisResponse(BaseModel):
    """Response model for risk analysis"""
    caller_id: int
    caller_uuid: Optional[str] = None
    phone_number: str
    caller_name: Optional[str] = None
    app_risk_score: int
    auto_calculated_risk: int
    final_risk_score: int
    status: str
    threat_level: str
    is_blocked: bool
    block_reason: Optional[str] = None
    blocked_date: Optional[str] = None
    is_spam_reported: bool
    risk_level_id: int
    total_reports: int
    total_calls: int
    call_frequency: int
    last_called: Optional[str] = None
    recent_calls: List[dict] = []
    carrier: str
    location: str
    reputation_score: float
    risk_analysis: str
    created_date: Optional[str] = None
    updated_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReportCreate(BaseModel):
    """Request model for creating a report"""
    call_id: Optional[int] = None
    caller_number: str
    report_type: ReportTypeEnum
    description: Optional[str] = None

class ReportResponse(BaseModel):
    """Response model for reports"""
    id: int
    call_id: Optional[int] = None
    caller_number: str
    report_type: str
    description: Optional[str] = None
    submitted_at: Optional[datetime] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AlertResponse(BaseModel):
    """Response model for alerts"""
    id: int
    call_id: Optional[int] = None
    caller_number: str
    alert_type: str
    threat_level: str
    message: str
    is_read: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BlockedNumberCreate(BaseModel):
    """Request model for blocking a number"""
    phone_number: str
    caller_name: Optional[str] = None
    block_reason: str
    is_permanent: bool = True

class BlockedNumberResponse(BlockedNumberCreate):
    """Response model for blocked numbers"""
    id: int
    block_date: Optional[datetime] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class SettingsResponse(BaseModel):
    """Response model for settings"""
    id: int
    auto_block_calls: bool
    notifications_enabled: bool
    detection_sensitivity: int
    privacy_mode: bool
    auto_block_threshold: int = 80
    block_unknown_numbers: bool = False
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    """Response model for dashboard stats"""
    total_calls_today: int
    spam_calls_detected: int
    blocked_calls_count: int
    security_score: float
    recent_alerts: List[AlertResponse]

class NumberSearchResult(BaseModel):
    """Response model for number search"""
    phone_number: str
    caller_name: Optional[str] = None
    reputation_score: float
    risk_score: int
    risk_analysis: Optional[str] = None
    total_reports: int
    call_frequency: int = 0
    previous_calls: int = 0
    is_blocked: bool
    is_spam_reported: Optional[bool] = None
    risk_level_id: Optional[int] = None
    id: Optional[int] = None
    carrier: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class NumberSearchAllResult(BaseModel):
    """Response model for search all numbers"""
    id: int
    phone_number: str
    caller_name: Optional[str] = None
    reputation_score: float
    risk_score: int
    risk_analysis: Optional[str] = None
    total_reports: int
    call_frequency: int
    carrier: Optional[str] = None
    location: Optional[str] = None
    is_blocked: bool
    is_spam_reported: bool

    model_config = ConfigDict(from_attributes=True)

class CallAnalyzeResponse(BaseModel):
    """Response model for live call analyze"""
    call_id: int
    caller_number: str
    caller_name: str
    receiver_number: str
    duration: int
    call_type: str
    call_timestamp: str
    app_risk_score: int
    auto_calculated_risk: int
    final_risk_score: int
    status: str
    threat_level: str
    is_blocked: bool
    block_reason: Optional[str] = None
    auto_blocked: bool
    caller_id: int
    is_spam_reported: bool
    total_reports: int
    total_calls: int
    report_id: int
    alert_id: Optional[int] = None
    message: str

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "call_id": 1,
                "caller_number": "+1 (555) 019-2831",
                "caller_name": "Father Leo",
                "receiver_number": "+1 (555) 000-0000",
                "duration": 45,
                "call_type": "INCOMING",
                "call_timestamp": "2024-01-15T10:30:00",
                "app_risk_score": 5,
                "auto_calculated_risk": 2,
                "final_risk_score": 5,
                "status": "Safe",
                "threat_level": "Low",
                "is_blocked": False,
                "block_reason": None,
                "auto_blocked": False,
                "caller_id": 1,
                "is_spam_reported": False,
                "total_reports": 0,
                "total_calls": 1,
                "report_id": 1,
                "alert_id": None,
                "message": "Call analyzed and stored successfully"
            }
        }
    )

# ============================================
# 📦 ANALYTICS RESPONSE MODELS
# ============================================

class DailyStatsResponse(BaseModel):
    """Response model for daily stats"""
    date: str
    total_calls: int
    spam_calls: int
    blocked_calls: int
    safe_calls: int

class BlockedStatsResponse(BaseModel):
    """Response model for blocked stats"""
    total_blocked_calls: int
    total_blocked_numbers: int
    auto_blocked_calls: int
    manual_blocked_calls: int
    auto_block_percentage: float

class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    message: Optional[str] = None

# ============================================
# 📦 SEARCH RESPONSE MODELS
# ============================================

class SearchResponse(BaseModel):
    """Response model for search results"""
    id: Optional[int] = None
    phone_number: str
    caller_name: Optional[str] = None
    reputation_score: float
    risk_score: int
    risk_analysis: Optional[str] = None
    total_reports: int
    call_frequency: int
    previous_calls: int = 0
    is_blocked: bool
    is_spam_reported: Optional[bool] = None
    risk_level_id: Optional[int] = None
    carrier: Optional[str] = None
    location: Optional[str] = None
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# ============================================
# 📦 CALLER ADD RESPONSE
# ============================================

class CallerAddResponse(BaseModel):
    """Response model for adding a caller"""
    id: int
    phone_number: str
    caller_name: str
    is_spam_reported: bool
    risk_level_id: int
    message: str

    model_config = ConfigDict(from_attributes=True)


# ============================================
# 📦 ERROR LOG MODELS
# ============================================

class ErrorLogCreateRequest(BaseModel):
    """Request model for creating an error log"""
    module_name: str = Field(..., description="The service/module where the error occurred")
    severity: str = Field(..., description="Severity level: CRITICAL, ERROR, WARNING")
    error_message: str = Field(..., description="Error message description")
    stack_trace: Optional[str] = Field(None, description="Detailed stack trace")
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    user_id: Optional[str] = None

class ErrorLogResponse(BaseModel):
    """Response model for error logs"""
    id: int = Field(..., alias="error_id")
    timestamp: datetime = Field(..., alias="created_date")
    module_name: str
    severity: str
    error_message: str
    stack_trace: Optional[str] = None
    is_resolved: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
