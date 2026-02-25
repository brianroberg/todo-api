"""Tests that verify all API endpoints are documented in the README."""

from pathlib import Path

from app.main import app

README = (Path(__file__).parent.parent / "README.md").read_text()

# OpenAPI/Swagger infrastructure routes that don't need README documentation
OPENAPI_ROUTES = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def _documented_path(path: str) -> bool:
    """Check if a route path (or its prefix) appears in the README."""
    # Exact match (e.g. "/health")
    if path in README:
        return True
    # Prefix match: /inbox/{item_id}/complete is covered by "/inbox"
    parts = path.strip("/").split("/")
    prefix = f"/{parts[0]}"
    return prefix in README


def test_all_routes_documented(subtests):
    routes = [
        (r.path, sorted(r.methods))
        for r in app.routes
        if hasattr(r, "methods") and r.path not in OPENAPI_ROUTES
    ]
    for path, methods in sorted(routes):
        with subtests.test(path=path, methods=methods):
            assert _documented_path(path), (
                f"{' '.join(methods)} {path} is not documented in README.md"
            )


def test_readme_endpoints_exist(subtests):
    """Verify endpoint paths mentioned in the README actually exist in the app."""
    import re

    app_paths = {r.path for r in app.routes if hasattr(r, "methods")}

    # Match lines like "POST /auth/keys" or "GET  /auth/keys/current"
    readme_routes = re.findall(
        r"(?:GET|POST|PUT|PATCH|DELETE)\s+(/\S+)", README
    )
    for documented_path in sorted(set(readme_routes)):
        with subtests.test(path=documented_path):
            assert documented_path in app_paths, (
                f"{documented_path} is documented in README but does not exist in the app"
            )
