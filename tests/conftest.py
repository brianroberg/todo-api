"""Shared test fixtures for FastAPI GTD API."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.auth.dependencies import get_current_api_key
from app.auth.service import AuthService
from app.main import app
from app.models import ApiKey


# Create test engine with in-memory SQLite using StaticPool for connection sharing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Ensures same connection is reused
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh tables before each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def test_db():
    """Create a test database session."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


def override_get_db():
    """Dependency override for get_db."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_api_key(test_db: Session) -> tuple[ApiKey, str]:
    """Create a test API key and return (ApiKey object, raw key string)."""
    api_key_obj, raw_key = AuthService.create_api_key(test_db, name="Test Key")
    return api_key_obj, raw_key


@pytest.fixture
def client(test_db: Session, test_api_key: tuple[ApiKey, str]) -> TestClient:
    """Create a FastAPI TestClient with dependency overrides."""
    api_key_obj, raw_key = test_api_key

    def override_get_current_api_key():
        return api_key_obj

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_api_key] = override_get_current_api_key

    test_client = TestClient(app)
    # Store raw key on client for tests that need to make authenticated requests
    test_client.headers["X-API-Key"] = raw_key

    yield test_client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_auth(test_db: Session) -> TestClient:
    """Create a TestClient without authentication for testing auth endpoints."""
    app.dependency_overrides[get_db] = override_get_db

    test_client = TestClient(app)
    yield test_client

    app.dependency_overrides.clear()
