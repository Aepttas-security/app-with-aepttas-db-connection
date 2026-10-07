# AeptasShield Vulnerability Backend

A complete backend for the mobile security app **AeptasShield**, built using Python, FastAPI, SQLAlchemy, SQLite, scikit-learn, and the Anthropic Claude API.

## Project Structure

```
vulnerability_backend/
├── app/
│   ├── main.py                  # FastAPI app, mounts all routers
│   ├── config.py                # Settings (env-driven)
│   ├── database.py               # SQLAlchemy engine/session setup
│   ├── models/
│   │   └── __init__.py           # SQLAlchemy ORM models (scan history tables, including Geolocation)
│   ├── schemas/
│   │   └── __init__.py           # Pydantic request/response models
│   ├── routers/
│   │   └── __init__.py
│   │   ├── device_integrity.py  # Module 1 endpoints
│   │   ├── app_permissions.py   # Module 2 endpoints
│   │   ├── app_risk_report.py   # Module 3 endpoints
│   │   └── geolocation.py       # Module 4 endpoints (GPS Spoofing Detection)
│   ├── services/
│   │   ├── permission_risk_model.py   # ML risk prediction
│   │   ├── explanation_service.py     # LLM and Template explanations
│   │   ├── play_integrity.py          # Google Play Integrity service
│   │   ├── play_store_lookup.py       # Google Play version scraper
│   │   ├── apk_static_analysis.py     # Static APK analysis (androguard)
│   │   └── geolocation.py             # GPS Spoofing Detection logic
│   ├── ml/
│   │   ├── train_permission_model.py  # Synthetic data generation and training script
│   │   └── permission_risk_model.joblib  # Trained RandomForest model artifact
│   └── utils/
│   │   ├── __init__.py
│   │   └── feature_engineering.py     # Shared category/permission multi-hot mapping
├── tests/
│   ├── conftest.py
│   ├── test_device_integrity.py
│   ├── test_app_permissions.py
│   ├── test_app_risk_report.py
│   ├── test_ml_model.py
│   ├── test_explanation.py
│   └── test_geolocation.py       # Geolocation unit tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Architectural Choices: The ML / LLM Split

This backend separates ML-based risk decisions from natural language explanations to ensure reliability and verification:
- **ML Model for Permissions (Module 2)**: Permission risk is predicted by a `RandomForestClassifier` trained using synthetic datasets. It predicts the `risk_label` (`safe | needs_review | high_risk`) dynamically from the app's category and sensitive permission requests.
- **Deterministic Verification**: Module 1 (Device Integrity) and Module 3 (APK static checks for hardcoded credentials, cleartext permissions, and manifest vulnerabilities) are rule-based and deterministic on purpose. Security decisions on these levels must be reproducible and verifiable.
- **LLM for Explanations Only**: The LLM (Anthropic Claude API) is only used as an **explanation layer** to translate findings into user-friendly plain English. It **never** decides the security verdict or risk score directly.

---

## Local Setup & Run

### 1. Prerequisites
- Python 3.11+
- Virtual Environment tool

### 2. Installation
Clone the repository, enter the directory, set up your virtual environment, and install dependencies:
```bash
python -m venv .venv
.venv\Scripts\activate  # On Windows PowerShell
pip install -r requirements.txt
```

### 3. Setup Configuration
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
By default, the application runs out of the box in `mock` Play Integrity mode and `template` Explanation mode without requiring any external keys.

### 4. Train the ML Model
Run the standalone model training script once to generate the RandomForest classifier artifact:
```bash
python -m app.ml.train_permission_model
```
This generates the model artifact at `app/ml/permission_risk_model.joblib`. If the model is not trained yet, the backend will load in "untrained fallback mode" and predict using deterministic rules, so the app never crashes.

### 5. Launch the Server
Start the FastAPI development server:
```bash
uvicorn app.main:app --reload
```
Once running, you can explore the OpenAPI docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 6. Running Tests
Execute the pytest suite:
```bash
pytest
```

---

## Configuration Options (`.env`)

- **`PLAY_INTEGRITY_MODE`**: Set to `"mock"` (default) or `"real"`. 
  - In `"real"` mode, provide service account JSON credentials in `GOOGLE_APPLICATION_CREDENTIALS` and the client package name in `PLAY_INTEGRITY_PACKAGE_NAME` to call the Google Play Integrity API.
- **`EXPLANATION_MODE`**: Set to `"template"` (default) or `"llm"`.
  - In `"llm"` mode, provide your Anthropic key in `LLM_API_KEY` to enable Claude 3-based explanation text generation and AI summary creation. Failed/timed-out LLM requests (>3s) automatically fallback to templates.

---

## Example `curl` Requests

### Endpoint 1 — Device Integrity Scan (`POST /api/device-integrity/scan`)
```bash
curl -X POST http://127.0.0.1:8000/api/device-integrity/scan \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: device-abc-123" \
  -d '{
    "root_detected": false,
    "mock_location_detected": false,
    "tamper_detected": false,
    "play_integrity_token": "pass-token-demo"
  }'
```

### Endpoint 2 — App Permissions Analyze (`POST /api/app-permissions/analyze`)
```bash
curl -X POST http://127.0.0.1:8000/api/app-permissions/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "installed_apps": [
      {
        "app_name": "Flashlight Pro",
        "package_name": "com.example.flashlight",
        "category": "tools",
        "requested_permissions": ["CAMERA", "SMS", "CONTACTS"],
        "current_version": "1.2.0"
      }
    ]
  }'
```

### Endpoint 3 — App Risk Report Analyze (`POST /api/app-risk-report/analyze`)
```bash
curl -X POST http://127.0.0.1:8000/api/app-risk-report/analyze \
  -H "Accept: application/json" \
  -F "apk_file=@path/to/local/app.apk"
```

### Endpoint 4 — Geolocation GPS Spoofing Verification (`POST /api/geolocation/verify`)
```bash
curl -X POST http://127.0.0.1:8000/api/geolocation/verify \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: device-abc-123" \
  -d '{
    "latitude": 12.9716,
    "longitude": 77.5946,
    "accuracy": 10.0,
    "ip_address": "103.86.176.1",
    "mock_location_detected": false
  }'
```

