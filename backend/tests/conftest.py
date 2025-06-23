import pytest
import pytest_asyncio
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.base import Base
from app.models.user import User
from fastapi import FastAPI
from app.api.v1.api import api_router
from app.core.config import get_settings
from app.db.session import get_db

settings = get_settings()
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)
app.include_router(api_router, prefix=settings.API_V1_STR)

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    """Database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI test client."""

    def get_test_db():
        return db

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unverified_user(db):
    """Create an unverified user for testing."""
    user = User(
        email="unverified@example.com",
        username="unverified_user",
        hashed_password="fake_hashed_password",
        is_verified=False,
        verification_token="fake_token",
        verification_token_expires_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def verified_user(db):
    """Create a verified user for testing."""
    user = User(
        email="verified@example.com",
        username="verified_user",
        hashed_password="fake_hashed_password",
        is_verified=True,
        verification_token=None,
        verification_token_expires_at=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
