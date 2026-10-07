# app/models/child.py
from pydantic import BaseModel, Field
from typing import Optional, Dict

# Advanced Feature #1: Strict validation enforcement constraints
class ChildProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, example="Alex")
    age: int = Field(..., ge=2, le=18, example=12)
    linking_code: str = Field(..., min_length=6, max_length=7, example="123-456")

class ChildProfileResponse(BaseModel):
    id: int
    parent_id: int
    name: str
    age: int
    device: str
    battery: str
    is_active_online: bool
    linking_code: Optional[str] = None

class DevicePairRequest(BaseModel):
    linking_code: str = Field(..., min_length=6, max_length=7, description="Handles formats like 942-817")
    device_name: str = Field(..., example="Samsung S23 Ultra")
    os_type: str = Field(..., description="Android or iOS")

class ConsentPayload(BaseModel):
    linking_code: str = Field(..., min_length=6, max_length=7, example="942-817")
    consent_approved: bool = Field(..., example=True)

class CodeGenerateResponse(BaseModel):
    child_id: str
    linking_code: str
    status: str = "PENDING"
    database_sync: str = "Neon PostgreSQL Verified"

class PairingStatusResponse(BaseModel):
    status: str
    child_id: str
    linking_code: Optional[str] = None
    parent_id: Optional[int] = None
    child_consent_given: bool = False
    device_model: Optional[str] = None
    is_online: bool = False

class PermissionStatusPayload(BaseModel):
    location_allowed: bool = Field(..., example=True)
    usage_stats_allowed: bool = Field(..., example=True)
    vpn_filter_allowed: bool = Field(..., example=True)


# In-Memory dynamic store matching your exact UI configurations
MOCK_CHILDREN_DB: Dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Alex",
        "age": 12,
        "device": "Samsung S23 Ultra",
        "battery": "84%",
        "is_active_online": True,
        "linking_code": None
    },
    2: {
        "id": 2,
        "name": "Emma",
        "age": 8,
        "device": "iPad Mini 6",
        "battery": "92%",
        "is_active_online": True,
        "linking_code": None
    }
}
CHILD_ID_COUNTER = 3