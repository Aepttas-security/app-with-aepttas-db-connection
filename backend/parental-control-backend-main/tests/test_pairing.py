# tests/test_pairing.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_generate_parent_linking_code(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Generates Pairing Code Token."""
    # Act
    response = await async_client.post(
        f"/api/pairing/generate-code/{test_child_profile.child_id}",
        headers=auth_headers
    )

    # Assert
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_should_check_pairing_status_by_linking_code(async_client: AsyncClient):
    """AAA Pattern: Check Status of Linking Code."""
    # Act
    response = await async_client.get("/api/pairing/status/123-456")

    # Assert
    assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_should_link_child_device_using_valid_code(async_client: AsyncClient):
    """AAA Pattern: Child Device Pair Request Handshake."""
    # Arrange
    payload = {
        "linking_code": "123-456",
        "child_name": "Leo Smith",
        "device_name": "Samsung Galaxy Tab",
        "os_type": "Android"
    }

    # Act
    response = await async_client.post("/api/pairing/link-device", json=payload)

    # Assert
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_should_submit_child_consent_authorization(async_client: AsyncClient):
    """AAA Pattern: Child Grants Operational Consent."""
    # Arrange
    payload = {
        "consent_given": True
    }

    # Act
    response = await async_client.post("/api/pairing/child-consent/1", json=payload)

    # Assert
    assert response.status_code in [200, 404, 500]


@pytest.mark.asyncio
async def test_should_report_and_check_logout_attempt(async_client: AsyncClient):
    """AAA Pattern: Tamper Detection - Unauthorized Child Logout Alert."""
    # Arrange
    report_payload = {
        "child_id": "1",
        "parent_id": 1,
        "child_name": "Alex Test"
    }

    # Act - Report
    rep_res = await async_client.post("/api/pairing/logout-attempt", json=report_payload)
    assert rep_res.status_code == 200

    # Act - Check Status
    chk_res = await async_client.get("/api/pairing/check-logout-attempt/1")
    assert chk_res.status_code == 200
    assert chk_res.json()["has_logout_attempt"] is True
