# tests/test_scanner.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_should_scan_safe_apk_file(async_client: AsyncClient):
    """AAA Pattern: Malware Scanner - Safe APK Upload."""
    # Arrange
    files = {"file": ("calculator_app.apk", b"dummy_apk_bytes_content", "application/vnd.android.package-archive")}

    # Act
    response = await async_client.post("/api/scan", files=files)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["threat_level"] == "SAFE"
    assert data["risk_score"] == 15


@pytest.mark.asyncio
async def test_should_detect_high_risk_malware_file(async_client: AsyncClient):
    """AAA Pattern: Malware Scanner - High Risk Spyware Detection."""
    # Arrange
    files = {"file": ("spyware_tracker.apk", b"malicious_payload_bytes", "application/vnd.android.package-archive")}

    # Act
    response = await async_client.post("/api/scan", files=files)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["threat_level"] == "HIGH_RISK"
    assert data["risk_score"] == 88


@pytest.mark.asyncio
async def test_should_fetch_quarantine_list(async_client: AsyncClient):
    """AAA Pattern: Malware Scanner - Fetch Quarantined Files List."""
    # Act
    response = await async_client.get("/api/quarantine")

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_should_fetch_scanner_dashboard_metrics(async_client: AsyncClient):
    """AAA Pattern: Security Score Dashboard Metrics."""
    # Act
    response = await async_client.get("/api/dashboard")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "total_scanned" in data
    assert "threats_detected" in data
    assert "device_security_score" in data
