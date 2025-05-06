import pytest
import sys
import os
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy.orm import Session
import pytest_asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.models.user import User
from app.core.token import set_verification_token, verify_token


@pytest.fixture
def unverified_user(db: Session):
    """Create an unverified user for testing."""
    user = User(
        email="test@example.com", 
        hashed_password="hashed_password", 
        is_verified=False
    )
    db.add(user)
    db.commit()
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def verified_user(db: Session):
    """Create a verified user for testing."""
    user = User(
        email="verified@example.com", 
        hashed_password="hashed_password", 
        is_verified=True
    )
    db.add(user)
    db.commit()
    yield user
    db.delete(user)
    db.commit()


@pytest.mark.asyncio
@patch("app.api.auth.auth.send_verification_email", new_callable=AsyncMock)
async def test_resend_confirmation_to_unverified_user(
    mock_send_email, client, db: Session, unverified_user
):
    """Test resending confirmation to an unverified user."""
    response = client.post(
        "/auth/resend-confirmation", 
        json={"email": unverified_user.email}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "If your email is registered and not verified, a new confirmation email has been sent."
    }
    
    mock_send_email.assert_called_once()
    
    updated_user = db.query(User).filter(User.id == unverified_user.id).first()
    assert updated_user.verification_token is not None
    assert updated_user.verification_token_expires_at is not None
    
    now = datetime.now(timezone.utc)
    expiry = updated_user.verification_token_expires_at
    assert (expiry - now).total_seconds() > 23 * 3600  # At least 23 hours
    assert (expiry - now).total_seconds() < 25 * 3600  # At most 25 hours


@pytest.mark.asyncio
@patch("app.api.auth.auth.send_verification_email", new_callable=AsyncMock)
async def test_resend_confirmation_to_verified_user(
    mock_send_email, client, verified_user
):
    """Test resending confirmation to an already verified user."""
    response = client.post(
        "/auth/resend-confirmation", 
        json={"email": verified_user.email}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "If your email is registered and not verified, a new confirmation email has been sent."
    }
    
    mock_send_email.assert_not_called()


@pytest.mark.asyncio
@patch("app.api.auth.auth.send_verification_email", new_callable=AsyncMock)
async def test_resend_confirmation_to_nonexistent_user(mock_send_email, client):
    """Test resending confirmation to a non-existent user."""
    response = client.post(
        "/auth/resend-confirmation", 
        json={"email": "nonexistent@example.com"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "message": "If your email is registered and not verified, a new confirmation email has been sent."
    }
    
    mock_send_email.assert_not_called()
