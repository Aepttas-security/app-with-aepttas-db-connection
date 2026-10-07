# app/models/Reports.py
from pydantic import BaseModel
from typing import List, Dict

class CategoryBreakdownItem(BaseModel):
    category: str
    minutes_used: int
    percentage: float

class DailyUsageHistoryItem(BaseModel):
    day_of_week: str  # e.g., "Mon", "Tue"
    minutes_used: int

class ActivityReportResponse(BaseModel):
    child_id: int
    time_frame: str  # "7_days" or "30_days"
    total_screen_time_hours: float
    most_used_category: str
    category_breakdown: List[CategoryBreakdownItem]
    weekly_history: List[DailyUsageHistoryItem]

# In-memory mock analytical metrics for the summary charts
MOCK_REPORTS_DB: Dict[int, dict] = {
    1: {  # Alex's 7-Day Analytics
        "time_frame": "7_days",
        "total_screen_time_hours": 18.5,
        "most_used_category": "Social Media",
        "category_breakdown": [
            {"category": "Social Media", "minutes_used": 600, "percentage": 54.0},
            {"category": "Entertainment", "minutes_used": 300, "percentage": 27.0},
            {"category": "Education", "minutes_used": 210, "percentage": 19.0}
        ],
        "weekly_history": [
            {"day_of_week": "Mon", "minutes_used": 180},
            {"day_of_week": "Tue", "minutes_used": 240},
            {"day_of_week": "Wed", "minutes_used": 135},
            {"day_of_week": "Thu", "minutes_used": 190},
            {"day_of_week": "Fri", "minutes_used": 220},
            {"day_of_week": "Sat", "minutes_used": 310},
            {"day_of_week": "Sun", "minutes_used": 260}
        ]
    },
    2: {  # Emma's 7-Day Analytics
        "time_frame": "7_days",
        "total_screen_time_hours": 6.2,
        "most_used_category": "Games",
        "category_breakdown": [
            {"category": "Games", "minutes_used": 240, "percentage": 64.5},
            {"category": "Entertainment", "minutes_used": 132, "percentage": 35.5}
        ],
        "weekly_history": [
            {"day_of_week": "Mon", "minutes_used": 45},
            {"day_of_week": "Tue", "minutes_used": 60},
            {"day_of_week": "Wed", "minutes_used": 45},
            {"day_of_week": "Thu", "minutes_used": 50},
            {"day_of_week": "Fri", "minutes_used": 80},
            {"day_of_week": "Sat", "minutes_used": 120},
            {"day_of_week": "Sun", "minutes_used": 92}
        ]
    }
}