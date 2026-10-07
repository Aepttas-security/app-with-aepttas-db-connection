# app/models/Filter.py
from pydantic import BaseModel, Field
from typing import List, Dict

class CategoryToggleRequest(BaseModel):
    category_key: str = Field(..., example="gambling")
    is_enabled: bool

class UrlRuleRequest(BaseModel):
    url: str = Field(..., example="facebook.com")

class FilterDashboardResponse(BaseModel):
    child_id: int
    blocked_categories: Dict[str, bool]
    blacklisted_urls: List[str]
    whitelisted_urls: List[str]

# Initial mockup dataset mapping filtering rules to each child profile
MOCK_FILTER_DB: Dict[int, dict] = {
    1: {  # Alex
        "blocked_categories": {
            "adult_content": True,
            "gambling": True,
            "violence": False,
            "gaming_sites": False
        },
        "blacklisted_urls": ["reddit.com", "twitter.com"],
        "whitelisted_urls": ["wikipedia.org", "khanacademy.org"]
    },
    2: {  # Emma
        "blocked_categories": {
            "adult_content": True,
            "gambling": True,
            "violence": True,
            "gaming_sites": True
        },
        "blacklisted_urls": ["youtube.com"],
        "whitelisted_urls": ["pbskids.org"]
    }
}