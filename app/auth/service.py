import hashlib
import secrets

from sqlalchemy.orm import Session

from app.models import ApiKey


class AuthService:
    """Service for API key authentication operations."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key."""
        return f"gtd_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def create_api_key(db: Session, name: str | None = None) -> tuple[ApiKey, str]:
        """Create a new API key. Returns the ApiKey object and the raw key (only shown once)."""
        raw_key = AuthService.generate_api_key()
        key_hash = AuthService.hash_key(raw_key)

        api_key = ApiKey(
            key_hash=key_hash,
            name=name,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        return api_key, raw_key

    @staticmethod
    def verify_api_key(db: Session, raw_key: str) -> ApiKey | None:
        """Verify an API key and return the ApiKey object if valid."""
        key_hash = AuthService.hash_key(raw_key)

        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.is_active)
            .first()
        )

        return api_key

    @staticmethod
    def revoke_api_key(db: Session, api_key_id: int) -> bool:
        """Revoke an API key by setting is_active to False."""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if api_key:
            api_key.is_active = False
            db.commit()
            return True
        return False

    @staticmethod
    def delete_api_key(db: Session, api_key_id: int) -> bool:
        """Delete an API key and all associated data."""
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if api_key:
            db.delete(api_key)
            db.commit()
            return True
        return False
