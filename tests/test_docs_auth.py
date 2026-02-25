"""Tests for authenticated OpenAPI documentation endpoints."""

import pytest


class TestDocsWithoutAuth:
    """Docs endpoints should return 401 without a valid API key."""

    def test_docs_requires_auth(self, client_no_auth):
        response = client_no_auth.get("/docs")
        assert response.status_code == 401

    def test_redoc_requires_auth(self, client_no_auth):
        response = client_no_auth.get("/redoc")
        assert response.status_code == 401

    def test_openapi_json_requires_auth(self, client_no_auth):
        response = client_no_auth.get("/openapi.json")
        assert response.status_code == 401


class TestDocsWithAuth:
    """Docs endpoints should work with a valid API key."""

    def test_docs_returns_swagger_ui(self, client):
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger-ui" in response.text

    def test_redoc_returns_redoc_html(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()

    def test_openapi_json_returns_valid_schema(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data
