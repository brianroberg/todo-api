from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.database import get_db
from app.models import ApiKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_api_key(
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> ApiKey:
    """Dependency that validates the API key and returns the ApiKey object."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include X-API-Key header.",
        )

    api_key_obj = AuthService.verify_api_key(db, api_key)
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key",
        )

    return api_key_obj
