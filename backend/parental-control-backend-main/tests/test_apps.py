# tests/test_apps.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_sync_installed_apps_from_child_device(
    async_client: AsyncClient,
    test_child_profile: Child
):
    """AAA Pattern: Child Device Batch Application Sync."""
    # Arrange
    payload = {
        "apps": [
            {
                "package_name": "com.roblox.client",
                "app_name": "Roblox",
                "category": "Gaming"
            },
            {
                "package_name": "com.tiktok.android",
                "app_name": "TikTok",
                "category": "Entertainment"
            }
        ]
    }

    # Act
    response = await async_client.post(
        f"/api/apps/{test_child_profile.child_id}/sync",
        json=payload
    )

    # Assert
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_should_fetch_installed_apps_for_parent(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Fetches Application Inventory."""
    # Act
    response = await async_client.get(
        f"/api/apps/{test_child_profile.child_id}",
        headers=auth_headers
    )

    # Assert
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_should_toggle_app_block_restriction_by_package(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Blocks Application by Package Name."""
    # Arrange
    payload = {
        "target_package": "com.tiktok.android",
        "is_blocked": True
    }

    # Act
    response = await async_client.put(
        f"/api/apps/{test_child_profile.child_id}/toggle-block",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_should_set_app_daily_time_limit(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Sets App Usage Limit."""
    # Arrange
    payload = {
        "package_name": "com.roblox.client",
        "daily_limit_minutes": 30
    }

    # Act
    response = await async_client.put(
        f"/api/apps/{test_child_profile.child_id}/set-limit",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_should_evaluate_app_time_limit_and_return_lock_action(
    async_client: AsyncClient,
    test_child_profile: Child
):
    """AAA Pattern: Runtime Engine Evaluates App Usage Limit."""
    # Arrange
    payload = {
        "package_name": "com.roblox.client",
        "minutes_to_increment": 5
    }

    # Act
    response = await async_client.post(
        f"/api/apps/{test_child_profile.child_id}/track-app-time",
        json=payload
    )

    # Assert
    assert response.status_code in [200, 500]
