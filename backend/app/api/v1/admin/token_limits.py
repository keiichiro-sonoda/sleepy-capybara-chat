from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from app.core.security import get_current_admin_user
from app.db.session import get_db
from app.models.user import User
from app.models.token_limit import TokenLimit as TokenLimitModel
from app.schemas.token_limit import TokenLimit, TokenLimitCreate, TokenLimitUpdate
from app.schemas.user import UserWithTokenLimits

router = APIRouter()


@router.get("/users/token-limits-summary", response_model=list[UserWithTokenLimits])
async def get_users_with_token_limits_summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[User]:
    """Get all users with their token limits summary."""
    users = db.query(User).options(selectinload(User.token_limits)).all()
    return users


@router.get("/users/{user_id}/token-limits", response_model=list[TokenLimit])
async def get_user_token_limits(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[TokenLimitModel]:
    """Get all token limits for a specific user."""
    return db.query(TokenLimitModel).filter(TokenLimitModel.user_id == user_id).all()


@router.get("/models/{model_name}/token-limits", response_model=list[TokenLimit])
async def get_model_token_limits(
    model_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[TokenLimitModel]:
    """Get all token limits for a specific model."""
    return (
        db.query(TokenLimitModel).filter(TokenLimitModel.model_name == model_name).all()
    )


@router.post(
    "/token-limits", response_model=TokenLimit, status_code=status.HTTP_201_CREATED
)
async def create_token_limit(
    token_limit: TokenLimitCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> TokenLimitModel:
    """Create a new token limit."""
    try:
        db_token_limit = TokenLimitModel(**token_limit.model_dump())
        db.add(db_token_limit)
        db.commit()
        db.refresh(db_token_limit)
        return db_token_limit
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A token limit with these parameters already exists",
        )


@router.put("/token-limits/{token_limit_id}", response_model=TokenLimit)
async def update_token_limit(
    token_limit_id: int,
    token_limit: TokenLimitUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> TokenLimitModel:
    """Update an existing token limit."""
    db_token_limit = (
        db.query(TokenLimitModel).filter(TokenLimitModel.id == token_limit_id).first()
    )
    if not db_token_limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token limit not found",
        )

    # 更新対象のフィールドのみを更新
    update_data = token_limit.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_token_limit, field, value)

    try:
        db.commit()
        db.refresh(db_token_limit)
        return db_token_limit
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A token limit with these parameters already exists",
        )


@router.delete("/token-limits/{token_limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_token_limit(
    token_limit_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> None:
    """Delete a token limit."""
    db_token_limit = (
        db.query(TokenLimitModel).filter(TokenLimitModel.id == token_limit_id).first()
    )
    if not db_token_limit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token limit not found",
        )

    db.delete(db_token_limit)
    db.commit()
    return None


@router.get("/token-limits", response_model=list[TokenLimit])
async def get_all_token_limits(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user),
) -> list[TokenLimitModel]:
    """Get all token limits."""
    return db.query(TokenLimitModel).all()
