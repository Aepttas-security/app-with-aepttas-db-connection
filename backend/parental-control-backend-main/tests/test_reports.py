# tests/test_reports.py
import pytest
from httpx import AsyncClient
from app.models.db_models import Child


@pytest.mark.asyncio
async def test_should_generate_child_activity_report_summary(
    async_client: AsyncClient,
    auth_headers: dict,
    test_child_profile: Child
):
    """AAA Pattern: Aggregated Child Activity Report Metric Generation."""
    # Act
    response = await async_client.get(
        f"/api/reports/{test_child_profile.child_id}/summary",
        headers=auth_headers
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "report_metrics" in data
    metrics = data["report_metrics"]
    assert "total_screentime_minutes" in metrics
    assert "blocked_app_attempts" in metrics
    assert "geofence_boundary_breaches" in metrics
    assert "unresolved_sos_alerts" in metrics
    assert "top_apps_by_duration" in metrics
