from datetime import datetime, timezone
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


@pytest.fixture
def unverified_user(db: Session) -> Generator[User, None, None]:
    """Create an unverified user for testing."""
    user = User(
        email="test@example.com", hashed_password="hashed_password", is_verified=False
    )
    db.add(user)
    db.commit()
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def verified_user(db: Session) -> Generator[User, None, None]:
    """Create a verified user for testing."""
    user = User(
        email="verified@example.com",
        hashed_password="hashed_password",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    yield user
    db.delete(user)
    db.commit()


@pytest.mark.asyncio
@patch("app.services.email.get_email_service")
async def test_resend_confirmation_to_unverified_user(
    mock_get_service: AsyncMock, client: TestClient, db: Session, unverified_user: User
) -> None:
    """Test resending confirmation to an unverified user."""
    mock_service = AsyncMock()
    mock_get_service.return_value = mock_service

    response = client.post(
        "/api/v1/auth/resend-confirmation", json={"email": unverified_user.email}
    )

    assert response.status_code == status.HTTP_200_OK
    expected_message = (
        "If your email is registered and not verified, "
        "a new confirmation email has been sent."
    )
    assert response.json() == {"message": expected_message}

    mock_service.send_verification_email.assert_called_once()

    updated_user = db.query(User).filter(User.id == unverified_user.id).first()
    assert updated_user is not None
    assert updated_user.verification_token is not None
    assert updated_user.verification_token_expires_at is not None

    now = datetime.now(timezone.utc)
    expiry = updated_user.verification_token_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert (expiry - now).total_seconds() > 23 * 3600
    assert (expiry - now).total_seconds() < 25 * 3600


@pytest.mark.asyncio
@patch("app.services.email.get_email_service")
async def test_resend_confirmation_to_verified_user(
    mock_get_service: AsyncMock, client: TestClient, verified_user: User
) -> None:
    """Test resending confirmation to an already verified user."""
    mock_service = AsyncMock()
    mock_get_service.return_value = mock_service

    response = client.post(
        "/api/v1/auth/resend-confirmation", json={"email": verified_user.email}
    )

    assert response.status_code == status.HTTP_200_OK
    expected_message = (
        "If your email is registered and not verified, "
        "a new confirmation email has been sent."
    )
    assert response.json() == {"message": expected_message}

    mock_service.send_verification_email.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.email.get_email_service")
async def test_resend_confirmation_to_nonexistent_user(
    mock_get_service: AsyncMock, client: TestClient
) -> None:
    """Test resending confirmation to a non-existent user."""
    mock_service = AsyncMock()
    mock_get_service.return_value = mock_service

    response = client.post(
        "/api/v1/auth/resend-confirmation", json={"email": "nonexistent@example.com"}
    )

    assert response.status_code == status.HTTP_200_OK
    expected_message = (
        "If your email is registered and not verified, "
        "a new confirmation email has been sent."
    )
    assert response.json() == {"message": expected_message}

    mock_service.send_verification_email.assert_not_called()
