# tests/test_screentime.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_fetch_screentime_dashboard_metrics(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Fetch Real-Time Screentime Dashboard Metrics."""
    # Act
    response = await async_client.get(
        f"/api/screentime/{test_child_profile.child_id}/dashboard",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["child_id"] == str(test_child_profile.child_id)
    assert "daily_limit_minutes" in data
    assert "current_usage_minutes" in data
    assert "is_locked_remotely" in data


@pytest.mark.asyncio
async def test_should_toggle_remote_device_lock(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Toggles Instant Remote Hardware Lock."""
    # Arrange
    payload = {"is_locked": True}

    # Act
    response = await async_client.post(
        f"/api/screentime/{test_child_profile.child_id}/remote-lock",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["is_locked_remotely"] is True


@pytest.mark.asyncio
async def test_should_update_screentime_daily_limit(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Updates Daily Screentime Limit."""
    # Arrange
    payload = {"daily_limit_minutes": 180}

    # Act
    response = await async_client.put(
        f"/api/screentime/{test_child_profile.child_id}/daily-limit",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["daily_limit_minutes"] == 180
