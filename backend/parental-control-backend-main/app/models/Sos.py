# app/models/Sos.py
from pydantic import BaseModel, Field
from typing import List, Dict

class SosAlertTriggerRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    current_address: str = Field(..., example="Near Metro Pillar 142")

class SosAlertResponse(BaseModel):
    alert_id: int
    child_id: int
    child_name: str
    latitude: float
    longitude: float
    current_address: str
    timestamp: str
    is_resolved: bool

# Shared system memory queue to hold emergency alerts for the parent's feed
MOCK_SOS_ALERTS_FEED: List[dict] = [
    {
        "alert_id": 501,
        "child_id": 2,
        "child_name": "Emma",
        "latitude": 12.9279,
        "longitude": 77.6271,
        "current_address": "Outside Greenwood High School Gate",
        "timestamp": "2 hours ago",
        "is_resolved": True
    }
]
SOS_ID_COUNTER = 502