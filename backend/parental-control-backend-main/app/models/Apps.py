# app/models/Apps.py
from pydantic import BaseModel, Field
from typing import List, Dict

class AppStatusToggleRequest(BaseModel):
    is_blocked: bool

class AppItemResponse(BaseModel):
    app_id: str
    app_name: str
    category: str
    icon_type: str
    is_blocked: bool

# In-memory database mapping installed apps to each child profile slot
MOCK_APPS_DB: Dict[int, List[dict]] = {
    1: [  # Alex's Installed Apps
        {"app_id": "com.whatsapp", "app_name": "WhatsApp", "category": "Social", "icon_type": "message", "is_blocked": False},
        {"app_id": "com.google.youtube", "app_name": "YouTube", "category": "Entertainment", "icon_type": "video", "is_blocked": True},
        {"app_id": "com.instagram.android", "app_name": "Instagram", "category": "Social", "icon_type": "camera", "is_blocked": False}
    ],
    2: [  # Emma's Installed Apps
        {"app_id": "com.google.youtube", "app_name": "YouTube Kids", "category": "Entertainment", "icon_type": "video", "is_blocked": False},
        {"app_id": "org.unisand.minecraft", "app_name": "Minecraft", "category": "Games", "icon_type": "gamepad", "is_blocked": False}
    ]
}