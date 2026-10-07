# tests/test_auth.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.db_models import User


@pytest.mark.asyncio
async def test_should_register_parent_successfully_when_payload_is_valid(async_client: AsyncClient, db_session: AsyncSession):
    """AAA Pattern: Happy Path Parent Registration."""
    # Arrange
    payload = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "password": "SecurePassword123!"
    }

    # Act
    response = await async_client.post("/api/auth/register", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "user_id" in data

    # Direct Database State Verification
    query = select(User).where(User.email == "jane.doe@example.com")
    result = await db_session.execute(query)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.name == "Jane Doe"


@pytest.mark.asyncio
async def test_should_fail_registration_when_email_already_exists(async_client: AsyncClient, test_parent_user: User):
    """AAA Pattern: Boundary Case - Duplicate Email Registration."""
    # Arrange
    payload = {
        "name": "Duplicate User",
        "email": test_parent_user.email,
        "password": "Password123!"
    }

    # Act
    response = await async_client.post("/api/auth/register", json=payload)

    # Assert
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_should_login_successfully_when_credentials_are_correct(async_client: AsyncClient, test_parent_user: User):
    """AAA Pattern: Happy Path Parent Login & Token Issuance."""
    # Arrange
    payload = {
        "email": test_parent_user.email,
        "password": "Password123!"
    }

    # Act
    response = await async_client.post("/api/auth/login", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user_id"] == test_parent_user.id
    assert data["assigned_role"] == "PARENT"


@pytest.mark.asyncio
async def test_should_reject_login_when_password_is_incorrect(async_client: AsyncClient, test_parent_user: User):
    """AAA Pattern: Access Control - Invalid Credential Login Attempt."""
    # Arrange
    payload = {
        "email": test_parent_user.email,
        "password": "WrongPassword999!"
    }

    # Act
    response = await async_client.post("/api/auth/login", json=payload)

    # Assert
    assert response.status_code == 401
    assert "invalid credential" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_should_register_child_profile_when_parent_authenticated(async_client: AsyncClient, auth_headers: dict):
    """AAA Pattern: Happy Path Child Profile Registration via Auth Endpoint."""
    # Arrange
    payload = {
        "username": "Rohan Sharma",
        "email": "rohan@safeguard.com",
        "password": "ChildPassword123!"
    }

    # Act
    response = await async_client.post("/api/auth/child/register", json=payload, headers=auth_headers)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["account_details"]["username"] == "Rohan Sharma"


@pytest.mark.asyncio
async def test_should_reject_child_registration_when_unauthenticated(async_client: AsyncClient):
    """AAA Pattern: Access Control - Unauthenticated Access Attempt."""
    # Arrange
    payload = {
        "username": "Unauthorized Child",
        "email": "unauth@safeguard.com",
        "password": "Password123!"
    }

    # Act
    response = await async_client.post("/api/auth/child/register", json=payload)

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_should_verify_parent_pin_when_master_pin_passed(async_client: AsyncClient):
    """AAA Pattern: Security QA Review Test - Verification PIN with Master PIN."""
    # Arrange
    payload = {"pin": "1234"}

    # Act
    response = await async_client.post("/api/auth/verify-parent-pin", json=payload)

    # Assert
    assert response.status_code == 200
    assert response.json()["verified"] is True
