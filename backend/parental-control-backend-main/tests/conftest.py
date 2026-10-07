# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.schema import ForeignKeyConstraint

from app.main import app
from app.database import Base, get_db
from app.models.db_models import User, Child
from app.services.auth import hash_password
from app.services.jwt import create_access_token

# -------------------------------------------------------------------
# IN-MEMORY TEST DATABASE SETUP WITH SQLITE SCHEMA ADAPTATION
# -------------------------------------------------------------------
for t in Base.metadata.tables.values():
    t.schema = None
    t.foreign_keys.clear()
    t.constraints = {c for c in t.constraints if not isinstance(c, ForeignKeyConstraint)}
    for col in t.columns:
        col.foreign_keys.clear()

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create tables before each test and drop after test execution."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated clean database session per test."""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def override_get_db(db_session: AsyncSession):
    """Overrides the FastAPI get_db dependency to use the isolated test database session."""
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    yield
    app.dependency_overrides.clear()


# -------------------------------------------------------------------
# SEEDED FIXTURES & TEST DATA FACTORIES
# -------------------------------------------------------------------
@pytest_asyncio.fixture
async def test_parent_user(db_session: AsyncSession) -> User:
    """Creates a seeded parent user in the test database."""
    parent = User(
        name="Test Parent",
        email="parent@test.com",
        password_hash=hash_password("Password123!")
    )
    db_session.add(parent)
    await db_session.commit()
    await db_session.refresh(parent)
    return parent


@pytest_asyncio.fixture
async def test_parent_token(test_parent_user: User) -> str:
    """Generates a valid JWT access token for the seeded parent user."""
    return create_access_token(data={"sub": str(test_parent_user.id)})


@pytest_asyncio.fixture
async def auth_headers(test_parent_token: str) -> dict:
    """Returns Authorization header with valid Bearer token."""
    return {"Authorization": f"Bearer {test_parent_token}"}


@pytest_asyncio.fixture
async def test_child_profile(db_session: AsyncSession, test_parent_user: User) -> Child:
    """Creates a seeded child profile belonging to test_parent_user."""
    child = Child(
        parent_id=test_parent_user.id,
        child_name="Alex Test",
        age=10,
        linking_code="123-456"
    )
    db_session.add(child)
    await db_session.commit()
    await db_session.refresh(child)
    return child


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an HTTPX AsyncClient bound to the FastAPI app for async integration testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
