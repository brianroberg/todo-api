"""Tests for authentication service and endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.models import ApiKey


class TestAuthService:
    """Unit tests for AuthService."""

    def test_generate_api_key_has_gtd_prefix(self):
        """Generated API keys must start with 'gtd_' prefix."""
        key = AuthService.generate_api_key()
        assert key.startswith("gtd_")

    def test_generate_api_key_has_sufficient_length(self):
        """Generated API keys must have sufficient randomness (at least 43 chars total)."""
        key = AuthService.generate_api_key()
        # gtd_ (4 chars) + 32 bytes base64 encoded (~43 chars) = ~47 chars minimum
        assert len(key) >= 43

    def test_hash_key_is_deterministic(self):
        """Hashing the same key twice must produce the same hash."""
        key = "test_key_12345"
        hash1 = AuthService.hash_key(key)
        hash2 = AuthService.hash_key(key)
        assert hash1 == hash2

    def test_hash_key_different_keys_produce_different_hashes(self):
        """Different keys must produce different hashes."""
        hash1 = AuthService.hash_key("key_one")
        hash2 = AuthService.hash_key("key_two")
        assert hash1 != hash2

    def test_create_api_key_returns_api_key_object_and_raw_key(self, test_db: Session):
        """create_api_key must return both an ApiKey object and the raw key."""
        api_key_obj, raw_key = AuthService.create_api_key(test_db, name="Test")
        assert isinstance(api_key_obj, ApiKey)
        assert isinstance(raw_key, str)
        assert raw_key.startswith("gtd_")

    def test_create_api_key_stores_hash_not_raw_key(self, test_db: Session):
        """The stored key_hash must not equal the raw key."""
        api_key_obj, raw_key = AuthService.create_api_key(test_db, name="Test")
        assert api_key_obj.key_hash != raw_key

    def test_create_api_key_sets_name(self, test_db: Session):
        """create_api_key must store the provided name."""
        api_key_obj, _ = AuthService.create_api_key(test_db, name="My API Key")
        assert api_key_obj.name == "My API Key"

    def test_create_api_key_is_active_by_default(self, test_db: Session):
        """Newly created API keys must be active."""
        api_key_obj, _ = AuthService.create_api_key(test_db, name="Test")
        assert api_key_obj.is_active is True

    def test_verify_api_key_returns_api_key_for_valid_key(self, test_db: Session):
        """verify_api_key must return the ApiKey object for a valid key."""
        api_key_obj, raw_key = AuthService.create_api_key(test_db, name="Test")
        result = AuthService.verify_api_key(test_db, raw_key)
        assert result is not None
        assert result.id == api_key_obj.id

    def test_verify_api_key_returns_none_for_invalid_key(self, test_db: Session):
        """verify_api_key must return None for an invalid key."""
        result = AuthService.verify_api_key(test_db, "invalid_key")
        assert result is None

    def test_verify_api_key_returns_none_for_inactive_key(self, test_db: Session):
        """verify_api_key must return None for an inactive (revoked) key."""
        api_key_obj, raw_key = AuthService.create_api_key(test_db, name="Test")
        AuthService.revoke_api_key(test_db, api_key_obj.id)
        result = AuthService.verify_api_key(test_db, raw_key)
        assert result is None

    def test_revoke_api_key_sets_is_active_false(self, test_db: Session):
        """revoke_api_key must set is_active to False."""
        api_key_obj, _ = AuthService.create_api_key(test_db, name="Test")
        AuthService.revoke_api_key(test_db, api_key_obj.id)
        test_db.refresh(api_key_obj)
        assert api_key_obj.is_active is False

    def test_revoke_api_key_returns_true_on_success(self, test_db: Session):
        """revoke_api_key must return True when successful."""
        api_key_obj, _ = AuthService.create_api_key(test_db, name="Test")
        result = AuthService.revoke_api_key(test_db, api_key_obj.id)
        assert result is True

    def test_revoke_api_key_returns_false_for_nonexistent_key(self, test_db: Session):
        """revoke_api_key must return False for a nonexistent key ID."""
        result = AuthService.revoke_api_key(test_db, 99999)
        assert result is False

    def test_delete_api_key_removes_key_from_database(self, test_db: Session):
        """delete_api_key must remove the key from the database."""
        api_key_obj, _ = AuthService.create_api_key(test_db, name="Test")
        key_id = api_key_obj.id
        AuthService.delete_api_key(test_db, key_id)
        result = test_db.query(ApiKey).filter(ApiKey.id == key_id).first()
        assert result is None

    def test_delete_api_key_returns_false_for_nonexistent_key(self, test_db: Session):
        """delete_api_key must return False for a nonexistent key ID."""
        result = AuthService.delete_api_key(test_db, 99999)
        assert result is False


class TestAuthEndpoints:
    """Integration tests for auth API endpoints."""

    def test_create_api_key_endpoint_returns_201(self, client_no_auth: TestClient):
        """POST /auth/keys must return 201 and the created key."""
        response = client_no_auth.post("/auth/keys", json={"name": "Test Key"})
        assert response.status_code == 201
        data = response.json()
        assert "api_key" in data
        assert data["api_key"].startswith("gtd_")
        assert data["name"] == "Test Key"

    def test_get_current_key_returns_key_info(self, client: TestClient):
        """GET /auth/keys/current must return info about the current key."""
        response = client.get("/auth/keys/current")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Key"
        assert data["is_active"] is True

    def test_get_current_key_without_auth_returns_401(self, client_no_auth: TestClient):
        """GET /auth/keys/current without X-API-Key must return 401."""
        response = client_no_auth.get("/auth/keys/current")
        assert response.status_code == 401

    def test_revoke_current_key_returns_204(self, client: TestClient, test_api_key):
        """DELETE /auth/keys/current must return 204."""
        response = client.delete("/auth/keys/current")
        assert response.status_code == 204
