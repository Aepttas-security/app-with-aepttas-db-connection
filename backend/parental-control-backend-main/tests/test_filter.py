# tests/test_filter.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_toggle_content_category_filter(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Toggles Content Category Filter."""
    # Arrange
    payload = {
        "category_name": "Adult Content",
        "is_blocked": True
    }

    # Act
    response = await async_client.post(
        f"/api/filters/{test_child_profile.child_id}/category",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["updated_policy"]["category_key"] == "Adult Content"
    assert data["updated_policy"]["is_enabled"] is True


@pytest.mark.asyncio
async def test_should_append_url_to_blacklist(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Appends Blacklisted URL."""
    # Arrange
    payload = {"url": "https://malicious-site.com"}

    # Act
    response = await async_client.post(
        f"/api/filters/{test_child_profile.child_id}/blacklist",
        json=payload,
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["blacklisted_url"] == "https://malicious-site.com"


@pytest.mark.asyncio
async def test_should_delete_url_from_blacklist(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Unblocks Blacklisted URL."""
    # Act
    response = await async_client.delete(
        f"/api/filters/{test_child_profile.child_id}/blacklist?url=https://malicious-site.com",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_should_fetch_active_filter_rules_for_child(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Fetch Web Content Firewall Rules."""
    # Act
    response = await async_client.get(
        f"/api/filters/{test_child_profile.child_id}/rules",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "blocked_categories" in data
    assert "blacklisted_urls" in data
    assert data["safesearch_forced"] is True
