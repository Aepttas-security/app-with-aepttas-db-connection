from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime

# --- Module 1: Device Integrity ---

class DeviceIntegrityRequest(BaseModel):
    root_detected: bool
    mock_location_detected: bool
    tamper_detected: bool
    play_integrity_token: str

class DeviceIntegrityResponse(BaseModel):
    trust_status: Literal["trusted", "at_risk", "compromised"]
    root_check: Literal["pass", "fail"]
    play_integrity: Literal["pass", "fail"]
    mock_location: Literal["pass", "fail"]
    tamper_check: Literal["pass", "fail"]
    last_checked: datetime

# --- Module 2: App Permissions ---

class InstalledApp(BaseModel):
    app_name: str
    package_name: str
    category: str
    requested_permissions: List[str]
    current_version: str

class AppPermissionsRequest(BaseModel):
    installed_apps: List[InstalledApp]

class PermissionFlag(BaseModel):
    app_name: str
    risk_label: Literal["safe", "needs_review", "high_risk"]
    reason: str
    flagged_permissions: List[str]

class OutdatedApp(BaseModel):
    app_name: str
    play_store_url: str

class AppPermissionsResponse(BaseModel):
    permission_flags: List[PermissionFlag]
    outdated_apps: List[OutdatedApp]
    ai_summary: Optional[str] = None

# --- Module 3: App Risk Report ---

class CheckResult(BaseModel):
    status: Literal["pass", "fail"]
    detail: str

class AppRiskReportResponse(BaseModel):
    app_name: str
    overall_risk: Literal["low", "moderate", "high"]
    storage_check: CheckResult
    code_protection_check: CheckResult
    ipc_check: CheckResult
    ai_summary: Optional[str] = None

# --- Module 4: Geolocation & GPS Spoofing ---

class GeolocationRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 0.0
    ip_address: Optional[str] = None
    mock_location_detected: Optional[bool] = False

class GeolocationResponse(BaseModel):
    id: int
    device_id: str
    latitude: float
    longitude: float
    accuracy: float
    ip_address: Optional[str]
    ip_latitude: Optional[float]
    ip_longitude: Optional[float]
    distance_km: Optional[float]
    mock_location_detected: bool
    spoof_detected: bool
    reason: Optional[str]
    timestamp: datetime

# --- Module 4b: Current Location ---

class SaveLocationRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: float = 0.0

class SavedLocationResponse(BaseModel):
    id: int
    device_id: str
    latitude: float
    longitude: float
    accuracy: float
    city: Optional[str]
    country: Optional[str]
    address: Optional[str]
    timestamp: datetime

# --- Module 4c: Nearby Places ---

class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 5.0

class NearbyPlaceResponse(BaseModel):
    id: int
    place_name: str
    place_type: str
    latitude: float
    longitude: float
    distance_km: float
    address: Optional[str]

class NearbySearchResponse(BaseModel):
    total: int
    radius_km: float
    places: List[NearbyPlaceResponse]


