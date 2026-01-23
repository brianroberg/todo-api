from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_api_key
from app.auth.service import AuthService
from app.config import get_settings
from app.database import get_db
from app.models import ApiKey

router = APIRouter(prefix="/auth", tags=["Authentication"])

settings = get_settings()


class ApiKeyCreate(BaseModel):
    name: str | None = None
    admin_key: str | None = None  # Optional: require admin key to create new keys


class ApiKeyResponse(BaseModel):
    id: int
    name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    id: int
    name: str | None
    api_key: str  # The raw key - only shown once!
    message: str = "Save this API key - it will not be shown again"


@router.post("/keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    key_data: ApiKeyCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new API key.

    If ADMIN_KEY is set in environment, you must provide it to create new keys.
    The returned api_key is only shown once - save it securely!
    """
    # Check if admin key is required
    admin_key_env = getattr(settings, "admin_key", None)
    if admin_key_env and key_data.admin_key != admin_key_env:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin key required to create API keys",
        )

    api_key_obj, raw_key = AuthService.create_api_key(db, key_data.name)

    return ApiKeyCreatedResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        api_key=raw_key,
    )


@router.get("/keys/current", response_model=ApiKeyResponse)
def get_current_key_info(
    current_api_key: ApiKey = Depends(get_current_api_key),
):
    """Get information about the current API key."""
    return current_api_key


@router.delete("/keys/current", status_code=status.HTTP_204_NO_CONTENT)
def revoke_current_key(
    db: Session = Depends(get_db),
    current_api_key: ApiKey = Depends(get_current_api_key),
):
    """Revoke the current API key (soft delete - sets is_active to False)."""
    AuthService.revoke_api_key(db, current_api_key.id)
