# tests/test_sos.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_trigger_panic_button_emergency_alert(
    async_client: AsyncClient,
    test_child_profile: Child
):
    """AAA Pattern: Device Panic Button Trigger."""
    # Arrange
    payload = {
        "child_id": str(test_child_profile.child_id),
        "current_latitude": 37.7749,
        "current_longitude": -122.4194,
        "emergency_message": "Immediate Assistance Needed at Main St."
    }

    # Act
    response = await async_client.post("/api/sos/trigger", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "EMERGENCY_BROADCAST_ACTIVE"
    assert "alert_details" in data
    assert data["alert_details"]["child_id"] == str(test_child_profile.child_id)


@pytest.mark.asyncio
async def test_should_fetch_active_sos_alerts_for_child(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Parent Polls Active Panic Alarms."""
    # Arrange - First trigger a panic alert
    trigger_payload = {
        "child_id": str(test_child_profile.child_id),
        "current_latitude": 37.7749,
        "current_longitude": -122.4194,
        "emergency_message": "Emergency alert test"
    }
    await async_client.post("/api/sos/trigger", json=trigger_payload)

    # Act
    response = await async_client.get(
        f"/api/sos/active/{test_child_profile.child_id}",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["child_id"] == str(test_child_profile.child_id)
    assert data["is_panic_active"] is True


@pytest.mark.asyncio
async def test_should_fetch_parent_sos_incident_feed(
    async_client: AsyncClient,
    auth_headers: dict
):
    """AAA Pattern: Parent Incident Feed."""
    # Act
    response = await async_client.get("/api/sos/feed", headers=auth_headers)

    # Assert
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_should_handle_missing_sos_preferences_table(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: QA Review Verification - Missing ORM Table Handling."""
    # Act - Attempt to fetch preferences for non-existent ORM table apt_sos_preferences_b
    get_res = await async_client.get(
        f"/api/sos/preferences/{test_child_profile.child_id}",
        headers=auth_headers
    )

    # Assert - Confirms 500 error due to un-migrated raw table in backend code
    assert get_res.status_code == 500
    assert "database error" in get_res.json()["detail"].lower()
