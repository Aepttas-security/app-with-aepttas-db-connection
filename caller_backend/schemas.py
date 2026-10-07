# caller_backend/schemas.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum

# ============================================
# 📞 CALLER INTELLIGENCE SCHEMAS
# ============================================
class CallTypeEnum(str, Enum):
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"
    MISSED = "MISSED"
    BLOCKED = "BLOCKED"

class CallAnalyzeRequest(BaseModel):
    caller_number: str
    caller_name: Optional[str] = None
    receiver_number: Optional[str] = "Unknown"
    duration: Optional[int] = 0
    call_type: Optional[str] = "Incoming"
    risk_score: Optional[int] = 0
    user_id: Optional[int] = 1

class BlockNumberRequest(BaseModel):
    phone_number: str
    caller_name: Optional[str] = None
    block_reason: Optional[str] = "Blocked by user"

class ReportRequest(BaseModel):
    caller_number: str
    report_reason: Optional[str] = "Reported by user"
    call_id: Optional[int] = None

class SettingsUpdateRequest(BaseModel):
    auto_block_calls: Optional[bool] = None
    block_unknown_numbers: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    privacy_mode: Optional[bool] = None

class CallerCreateRequest(BaseModel):
    phone_number: str
    caller_name: Optional[str] = "Unknown Caller"
    is_spam_reported: Optional[bool] = False
    risk_level_id: Optional[int] = 1

class LoginRequest(BaseModel):
    email: str
    password: str
    username: Optional[str] = None
    user_name: Optional[str] = None

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    username: Optional[str] = None
    email: str
    password: str
    password_hash: Optional[str] = None
    role: Optional[str] = "PARENT"

# ============================================
# 📍 GEOLOCATION SCHEMAS
# ============================================
class LocationData(BaseModel):
    latitude: float
    longitude: float
    ip: Optional[str] = None
    is_mock_location: bool = False
    accuracy: Optional[float] = None
    provider: Optional[str] = "gps"
    timestamp: Optional[str] = None
    device_id: Optional[str] = None
    app_version: Optional[str] = None
    platform: Optional[str] = None
    mock_location_reasons: Optional[List[str]] = []
    user_id: Optional[int] = 1
    program_id: Optional[int] = 1
    attributes: Optional[Dict[str, Any]] = {}
    raw_provider_flags: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None

class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 5.0

# ============================================
# 🛡️ MALWARE SCHEMAS
# ============================================
class BatchScanItem(BaseModel):
    package_name: str
    app_name: Optional[str] = None
    version_name: Optional[str] = None
    source: Optional[str] = "user"
    requested_permissions: Optional[List[str]] = []

class BatchScanRequest(BaseModel):
    apps: List[BatchScanItem]

# ============================================
# 🔍 VULNERABILITY SCHEMAS
# ============================================
class PermissionScanRequest(BaseModel):
    package_name: str
    app_name: Optional[str] = None
    category: Optional[str] = "tools"
    requested_permissions: List[str] = []
    current_version: Optional[str] = "1.0.0"
    user_id: Optional[int] = 1
    scan_scenario: Optional[str] = "B"
    attributes: Optional[Dict[str, Any]] = {}

class OutdatedAppCreate(BaseModel):
    package_name: str
    app_name: Optional[str] = None
    current_version: str
    latest_version: str
    user_id: Optional[int] = 1

# ============================================
# 👨‍👩‍👧 PARENTAL CONTROL SCHEMAS
# ============================================
class ChildCreate(BaseModel):
    name: str
    age: int = 10
    device: Optional[str] = "Android Device"
    battery: Optional[str] = "90%"

class ScreentimeUpdate(BaseModel):
    daily_limit_minutes: Optional[int] = None
    current_usage_minutes: Optional[int] = None
    is_locked_remotely: Optional[bool] = None

class AppBlockToggle(BaseModel):
    is_blocked: bool

class CategoryFilterToggle(BaseModel):
    category: str
    is_blocked: bool

class BlacklistAdd(BaseModel):
    url: str

class SosTrigger(BaseModel):
    child_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    message: Optional[str] = "Emergency SOS Alert"

class PairingLinkRequest(BaseModel):
    code: str
    child_name: Optional[str] = None
    device_name: Optional[str] = None

# ============================================
# ⚙️ ADMIN ERROR LOG SCHEMAS
# ============================================
class ErrorLogCreateRequest(BaseModel):
    module_name: str
    severity: str
    error_message: str
    stack_trace: Optional[str] = None
    request_url: Optional[str] = None
    request_method: Optional[str] = None
    user_id: Optional[str] = None

class ErrorLogResponse(BaseModel):
    id: int
    timestamp: datetime
    service: str
    error_level: str
    message: str
    stack_trace: Optional[str] = None
    rectified: bool
