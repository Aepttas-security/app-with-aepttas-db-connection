# app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from app.database import engine, DATABASE_URL

logger = logging.getLogger(__name__)

# ==========================================
# 1. LIFESPAN STARTUP/SHUTDOWN ENGINE
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    db_target = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"[DATABASE] Initializing PostgreSQL connection: {db_target}")
    
    # Non-blocking async background verification to ensure instantaneous server startup
    async def _async_db_ping():
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1;"))
            print("[SUCCESS] Connected to PostgreSQL database successfully.")
        except Exception as e:
            print(f"[INFO] Database initial connection status: {e}")
            
    asyncio.create_task(_async_db_ping())
    yield
    # Any code written after 'yield' runs when the server is shutting down

# ==========================================
# 2. FASTAPI INSTANCE CONFIGURATION & SWAGGER UI METADATA
# ==========================================
tags_metadata = [
    {
        "name": "Authentication System",
        "description": "Endpoints for parent & child registration, authentication, and token issuance.",
    },
    {
        "name": "Child Management",
        "description": "Create child profiles, generate pairing codes, and link parent-child devices.",
    },
    {
        "name": "App Control",
        "description": "Retrieve installed apps on child devices and toggle block/allow restrictions.",
    },
    {
        "name": "Screen Time Control",
        "description": "Screen time usage monitoring, daily limits, and remote instant locking.",
    },
    {
        "name": "Web Filtering",
        "description": "Content category filters, blacklists, and URL restrictions.",
    },
    {
        "name": "Location Tracking",
        "description": "Real-time GPS coordinate telemetry, live tracking, and geofence safe zones.",
    },
    {
        "name": "Activity Reports",
        "description": "Comprehensive analytics summaries and activity logging.",
    },
    {
        "name": "SOS Emergency Alerts",
        "description": "Panic button alerts, active panic state tracking, and emergency feeds.",
    },
    {
        "name": "Device Pairing",
        "description": "Pairing codes, device handshakes, and status verification.",
    },
]

app = FastAPI(
    title="Parent Control API - Swagger UI Portal",
    description="""
    ## 🛡️ Parent Control API Documentation
    Welcome to the interactive **Swagger UI** for the Parent Control system.
    
    ### Key Features:
    * 🔑 **Authentication**: Parent & Child registration and login.
    * 📱 **Device & App Management**: Control app permissions and limits.
    * ⌛ **Screen Time**: Dashboard monitoring and remote lock switches.
    * 🌐 **Web Filtering**: Blacklist and category content filtering.
    * 📍 **GPS Location**: Live location monitoring & Geofencing.
    * 🚨 **SOS Emergency**: Instant emergency notification triggers.
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True
    },
    lifespan=lifespan
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. ROUTER REGISTRATIONS
# ==========================================
from app.routers import auth, child, screentime, apps, location, reports, sos, pairing, scanner
import app.routers.filter as filter_router

app.include_router(auth.router)
app.include_router(child.router)
app.include_router(screentime.router)
app.include_router(apps.router)
app.include_router(filter_router.router)
app.include_router(location.router)
app.include_router(reports.router)
app.include_router(sos.router)
app.include_router(pairing.router)
app.include_router(scanner.router)

# ==========================================
# 4. GLOBAL EXCEPTION HANDLER
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a proper HTTP 500 JSON response."""
    logger.error(f"Unhandled exception on route {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error occurred.",
            "detail": "An unexpected server-side error occurred."
        }
    )

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")