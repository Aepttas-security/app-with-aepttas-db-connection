# test_endpoints.py
import urllib.request
import json

endpoints = [
    ("Root", "http://127.0.0.1:5000/"),
    ("Health", "http://127.0.0.1:5000/api/health"),
    ("Caller Lookup", "http://127.0.0.1:5000/api/callers/lookup/+919876543210"),
    ("Dashboard", "http://127.0.0.1:5000/api/dashboard"),
    ("Geo Current", "http://127.0.0.1:5000/api/geo/current"),
    ("Child Management", "http://127.0.0.1:5000/api/child"),
    ("Admin Logs", "http://127.0.0.1:5000/api/admin/logs"),
]

print("=" * 60)
print("TESTING UNIFIED BACKEND ON PORT 5000")
print("=" * 60)

for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TestClient"})
        with urllib.request.urlopen(req, timeout=5) as response:
            status_code = response.status
            data = json.loads(response.read().decode())
            print(f"[PASS] {name:<18} [{status_code}]: {str(data)[:60]}...")
    except Exception as e:
        print(f"[FAIL] {name:<18} FAILED: {e}")

print("=" * 60)
