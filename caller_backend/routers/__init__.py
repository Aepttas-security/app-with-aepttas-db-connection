# caller_backend/routers/__init__.py
from .callers import router as callers_router
from .calls import router as calls_router
from .blocked import router as blocked_router
from .reports import router as reports_router
from .settings import router as settings_router
from .malware import router as malware_router
from .geolocation import router as geolocation_router
from .vulnerability import router as vulnerability_router
from .parental import router as parental_router

__all__ = [
    "callers_router",
    "calls_router",
    "blocked_router",
    "reports_router",
    "settings_router",
    "malware_router",
    "geolocation_router",
    "vulnerability_router",
    "parental_router",
]
