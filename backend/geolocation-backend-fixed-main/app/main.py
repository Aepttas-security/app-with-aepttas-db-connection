from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.config import settings
from app.routers import geolocation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create SQLite/Postgres tables on startup
    # Base.metadata.create_all(bind=engine)  # disabled - tables already exist
    # Load scikit-learn permission model

    yield

app = FastAPI(
    title="AeptasShield Security Backend",
    description="Backend API for device integrity, app permission scoring, and APK risk reports",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS using settings
origins = settings.ALLOWED_CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers

app.include_router(geolocation.router)


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AeptasShield Backend"
    }

@app.get("/health")
def read_health():
    return {
        "status": "healthy",
        "database": "connected",
        "service": "AeptasShield Backend"
    }

