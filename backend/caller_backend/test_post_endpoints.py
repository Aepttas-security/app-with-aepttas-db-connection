# test_post_endpoints.py
import urllib.request
import json

tests = [
    (
        "Malware Batch Scan",
        "http://127.0.0.1:5000/api/scan/batch",
        {"apps": [{"package_name": "com.example.app", "app_name": "Sample App", "requested_permissions": ["android.permission.INTERNET"]}]}
    ),
    (
        "Vuln Permission Scan",
        "http://127.0.0.1:5000/api/app-permissions/analyze",
        {"package_name": "com.sallysoft.srpol.edge.directcall", "app_name": "Direct Call", "category": "tools", "requested_permissions": ["android.permission.READ_CONTACTS"]}
    ),
    (
        "Parental Child Pairing",
        "http://127.0.0.1:5000/api/pairing/generate-parent-code",
        {"parent_id": 1}
    ),
    (
        "Live Call Analyze",
        "http://127.0.0.1:5000/api/live-call/analyze",
        {"caller_number": "+1 (555) 019-2831", "caller_name": "Father Leo", "duration": 30, "call_type": "INCOMING"}
    )
]

print("=" * 60)
print("TESTING POST ENDPOINTS ON PORT 5000")
print("=" * 60)

for name, url, payload in tests:
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "TestClient"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"[PASS] {name:<24} [{resp.status}]: {str(data)[:55]}...")
    except Exception as e:
        print(f"[FAIL] {name:<24} FAILED: {e}")

print("=" * 60)
