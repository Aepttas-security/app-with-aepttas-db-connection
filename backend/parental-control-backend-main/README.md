# Parental Control Backend API

FastAPI backend service for Parental Control application providing authentication, child profile management, device pairing, location tracking (OSM geofencing), screen time management, web filtering, app control, reports, and SOS alerts.

## 🚀 Features

- **Authentication & Authorization**: JWT token based auth with password hashing.
- **Child & Device Management**: Child profiles, device pairing/unlinking.
- **Location & Geofencing**: Live GPS tracking, geofence zone monitoring, and OpenStreetMap (OSM) integration.
- **Screen Time Control**: Schedules, daily usage limits, and remote device locking.
- **Web Filtering & App Rules**: Category blocking, URL blacklisting, and app usage control.
- **Reports & Analytics**: Usage statistics and security summaries.
- **SOS Emergency Alerts**: Instant trigger and status tracking for child emergencies.

## 🛠 Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: PostgreSQL (SQLAlchemy Async engine + asyncpg) / SQLite fallback
- **Validation**: Pydantic v2
- **Testing**: Pytest & Async HTTPX client

## 🔧 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Aepttas-security/parental-control-backend.git
cd parental-control-backend
```

### 2. Create and activate a Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
Copy `.env.example` to `.env` and fill in configuration details:
```bash
cp .env.example .env
```

### 5. Run the Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation available at `http://localhost:8000/docs`.
