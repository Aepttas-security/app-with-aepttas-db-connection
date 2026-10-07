# caller_backend/main.py
"""
AEPTTAS Shield - Unified Enterprise Backend Server
Consolidates Caller Intelligence, Malware Scanner, Geolocation,
Vulnerability Scanner, and Parental Control into ONE FastAPI Server on Port 5000.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from routers import (
    callers_router,
    calls_router,
    blocked_router,
    reports_router,
    settings_router,
    malware_router,
    geolocation_router,
    vulnerability_router,
    parental_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("unified_backend")

app = FastAPI(
    title="AEPTTAS Shield Unified Backend API",
    description="Unified API server hosting Callers, Malware, Geolocation, Vulnerability, and Parental Control services.",
    version="1.0.0"
)

# Enable CORS for React Native mobile apps, Android emulators, and web interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register All Subsystem Routers
app.include_router(callers_router)
app.include_router(calls_router)
app.include_router(blocked_router)
app.include_router(reports_router)
app.include_router(settings_router)
app.include_router(malware_router)
app.include_router(geolocation_router)
app.include_router(vulnerability_router)
app.include_router(parental_router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "AEPTTAS Shield Unified Backend",
        "port": 5000,
        "endpoints": {
            "caller_intelligence": "/api/callers/*",
            "calls": "/api/calls/*",
            "blocked": "/api/blocked/*",
            "reports": "/api/reports/*",
            "malware": "/api/malware/*",
            "geolocation": "/api/geo/*",
            "vulnerability": "/api/vuln/*",
            "parental_control": "/api/parental/*",
            "settings_and_admin": "/api/settings, /api/admin/logs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AEPTTAS Shield Unified Backend on http://0.0.0.0:5000 ...")
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
