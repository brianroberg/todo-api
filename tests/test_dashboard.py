"""Tests for the read-only GTD dashboard frontend."""

import pytest
from fastapi.testclient import TestClient


class TestDashboardEndpoint:
    """Tests for GET /dashboard serving the HTML page."""

    def test_dashboard_returns_200(self, client: TestClient):
        """GET /dashboard must return 200 OK."""
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_returns_html_content_type(self, client: TestClient):
        """GET /dashboard must return text/html content type."""
        response = client.get("/dashboard")
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_contains_valid_html_structure(self, client: TestClient):
        """Dashboard must contain proper HTML5 document structure."""
        response = client.get("/dashboard")
        html = response.text
        assert "<!DOCTYPE html>" in html
        assert "<html lang=" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_dashboard_contains_page_title(self, client: TestClient):
        """Dashboard must have a page title."""
        response = client.get("/dashboard")
        assert "<title>GTD Dashboard</title>" in response.text

    def test_dashboard_contains_viewport_meta(self, client: TestClient):
        """Dashboard must include viewport meta tag for responsive design."""
        response = client.get("/dashboard")
        assert 'name="viewport"' in response.text


class TestDashboardNavigation:
    """Tests for navigation elements in the dashboard HTML."""

    def test_dashboard_contains_all_nav_links(self, client: TestClient):
        """Dashboard must include navigation links for all GTD views."""
        response = client.get("/dashboard")
        html = response.text
        assert 'href="#inbox"' in html
        assert 'href="#next-actions"' in html
        assert 'href="#projects"' in html
        assert 'href="#someday"' in html
        assert 'href="#tickler"' in html
        assert 'href="#areas"' in html
        assert 'href="#tags"' in html
        assert 'href="#review"' in html

    def test_dashboard_contains_main_view_container(self, client: TestClient):
        """Dashboard must have a main content container for rendering views."""
        response = client.get("/dashboard")
        assert 'id="view"' in response.text


class TestDashboardAuthentication:
    """Tests for the API key authentication flow in the dashboard."""

    def test_dashboard_does_not_require_auth(self, client_no_auth: TestClient):
        """GET /dashboard must be accessible without an API key."""
        response = client_no_auth.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_contains_api_key_modal(self, client: TestClient):
        """Dashboard must include the API key input modal."""
        response = client.get("/dashboard")
        html = response.text
        assert 'id="api-key-modal"' in html
        assert 'id="key-input"' in html
        assert 'id="key-submit"' in html

    def test_dashboard_contains_api_key_error_display(self, client: TestClient):
        """Dashboard must include an element for showing auth errors."""
        response = client.get("/dashboard")
        assert 'id="key-error"' in response.text

    def test_dashboard_contains_logout_button(self, client: TestClient):
        """Dashboard must include a button to change/clear the API key."""
        response = client.get("/dashboard")
        assert 'id="btn-logout"' in response.text

    def test_dashboard_contains_refresh_button(self, client: TestClient):
        """Dashboard must include a button to refresh cached data."""
        response = client.get("/dashboard")
        assert 'id="btn-refresh"' in response.text


class TestDashboardSecurity:
    """Tests for XSS prevention and security measures in the dashboard."""

    def test_dashboard_contains_xss_escape_function(self, client: TestClient):
        """Dashboard JS must include the HTML escaping function for XSS prevention."""
        response = client.get("/dashboard")
        html = response.text
        assert "function esc(" in html
        assert "textContent" in html

    def test_dashboard_contains_color_validation(self, client: TestClient):
        """Dashboard must validate color values to prevent CSS injection."""
        response = client.get("/dashboard")
        assert "function validColor(" in response.text

    def test_dashboard_uses_safe_localstorage_wrappers(self, client: TestClient):
        """Dashboard must use try-catch wrappers around localStorage access."""
        response = client.get("/dashboard")
        html = response.text
        assert "function lsGet(" in html
        assert "function lsSet(" in html
        assert "function lsDel(" in html
        # Should NOT use raw localStorage directly
        assert "localStorage.getItem" not in html.split("function lsGet")[1].split("function lsSet")[0].replace(
            "localStorage.getItem(k)", ""
        )


class TestDashboardJavaScript:
    """Tests for the JavaScript application code in the dashboard."""

    def test_dashboard_contains_api_client(self, client: TestClient):
        """Dashboard must include API client methods for all GTD endpoints."""
        response = client.get("/dashboard")
        html = response.text
        assert "getInbox()" in html
        assert "getNextActions(" in html
        assert "getProjects(" in html
        assert "getProject(" in html
        assert "getProjectActions(" in html
        assert "getSomeday()" in html
        assert "getTickler()" in html
        assert "getTicklerToday()" in html
        assert "getAreas()" in html
        assert "getArea(" in html
        assert "getAreaProjects(" in html
        assert "getAreaActions(" in html
        assert "getTags()" in html
        assert "getTag(" in html
        assert "getTagItems(" in html

    def test_dashboard_contains_review_api_methods(self, client: TestClient):
        """Dashboard must include API client methods for review endpoints."""
        response = client.get("/dashboard")
        html = response.text
        assert "reviewInbox()" in html
        assert "reviewStale()" in html
        assert "reviewDeadlines(" in html
        assert "reviewWaiting()" in html
        assert "reviewOverdue()" in html

    def test_dashboard_contains_api_key_header(self, client: TestClient):
        """Dashboard API client must send X-API-Key header."""
        response = client.get("/dashboard")
        assert "X-API-Key" in response.text

    def test_dashboard_contains_router(self, client: TestClient):
        """Dashboard must include hash-based routing logic."""
        response = client.get("/dashboard")
        assert "hashchange" in response.text

    def test_dashboard_contains_all_view_functions(self, client: TestClient):
        """Dashboard must define rendering functions for all views."""
        response = client.get("/dashboard")
        html = response.text
        assert "function viewInbox()" in html
        assert "function viewNextActions()" in html
        assert "function viewProjects()" in html
        assert "function viewProjectDetail(" in html
        assert "function viewSomeday()" in html
        assert "function viewTickler()" in html
        assert "function viewAreas()" in html
        assert "function viewAreaDetail(" in html
        assert "function viewTags()" in html
        assert "function viewTagDetail(" in html
        assert "function viewReview()" in html

    def test_dashboard_validates_key_on_connect(self, client: TestClient):
        """Dashboard must validate the API key against /auth/keys/current."""
        response = client.get("/dashboard")
        assert "/auth/keys/current" in response.text


class TestDashboardCSS:
    """Tests for the CSS styles in the dashboard."""

    def test_dashboard_contains_css_custom_properties(self, client: TestClient):
        """Dashboard must define CSS custom properties for theming."""
        response = client.get("/dashboard")
        html = response.text
        assert ":root" in html
        assert "--blue:" in html
        assert "--gray-" in html
        assert "--radius:" in html

    def test_dashboard_contains_responsive_styles(self, client: TestClient):
        """Dashboard must include responsive breakpoints."""
        response = client.get("/dashboard")
        assert "@media" in response.text

    def test_dashboard_contains_loading_spinner(self, client: TestClient):
        """Dashboard must include loading spinner styles."""
        response = client.get("/dashboard")
        html = response.text
        assert ".spinner" in html
        assert "@keyframes spin" in html


class TestDashboardOpenAPI:
    """Tests for dashboard exclusion from API documentation."""

    def test_dashboard_excluded_from_openapi_schema(self, client: TestClient):
        """The /dashboard endpoint must not appear in the OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/dashboard" not in schema.get("paths", {})


class TestDashboardHTMLContent:
    """Tests for the HTML_CONTENT constant."""

    def test_html_content_is_nonempty_string(self):
        """HTML_CONTENT must be a non-empty string."""
        from app.routers.dashboard import HTML_CONTENT
        assert isinstance(HTML_CONTENT, str)
        assert len(HTML_CONTENT) > 1000

    def test_html_content_contains_inline_styles(self):
        """HTML_CONTENT must contain inline CSS (no external stylesheets)."""
        from app.routers.dashboard import HTML_CONTENT
        assert "<style>" in HTML_CONTENT
        assert "</style>" in HTML_CONTENT

    def test_html_content_contains_inline_script(self):
        """HTML_CONTENT must contain inline JavaScript (no external scripts)."""
        from app.routers.dashboard import HTML_CONTENT
        assert "<script>" in HTML_CONTENT
        assert "</script>" in HTML_CONTENT

    def test_html_content_is_self_contained(self):
        """HTML_CONTENT must not reference external CSS or JS files."""
        from app.routers.dashboard import HTML_CONTENT
        assert 'rel="stylesheet"' not in HTML_CONTENT
        assert "<script src=" not in HTML_CONTENT
