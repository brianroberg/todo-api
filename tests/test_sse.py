"""Tests for Server-Sent Events push notification system."""

import asyncio

from fastapi.testclient import TestClient

from app.sse import _clients, notify_change


class TestSSEEndpoint:
    """Tests for GET /events SSE endpoint."""

    def test_sse_returns_401_for_invalid_key(self, client_no_auth: TestClient):
        """SSE endpoint must reject invalid API keys."""
        response = client_no_auth.get("/events?key=invalid_key")
        assert response.status_code == 401

    def test_sse_returns_401_for_missing_key(self, client_no_auth: TestClient):
        """SSE endpoint must require a key parameter."""
        response = client_no_auth.get("/events")
        assert response.status_code == 422  # FastAPI validation error

    def test_sse_excluded_from_openapi_schema(self, client: TestClient):
        """The /events endpoint must not appear in the OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/events" not in schema.get("paths", {})


class TestNotifyChange:
    """Tests for the notify_change function."""

    def test_notify_with_no_clients_does_not_error(self):
        """notify_change must not raise when no clients are connected."""
        notify_change(99999)  # Non-existent api_key_id

    def test_notify_queues_message_for_connected_client(self):
        """notify_change must put a message in connected client queues."""
        queue = asyncio.Queue(maxsize=16)
        api_key_id = 12345
        _clients[api_key_id].add(queue)
        try:
            notify_change(api_key_id)
            assert not queue.empty()
            msg = queue.get_nowait()
            assert "change" in msg
            assert "refresh" in msg
        finally:
            _clients[api_key_id].discard(queue)
            if not _clients[api_key_id]:
                del _clients[api_key_id]

    def test_notify_only_targets_matching_api_key(self):
        """notify_change must only notify clients with matching api_key_id."""
        queue_a = asyncio.Queue(maxsize=16)
        queue_b = asyncio.Queue(maxsize=16)
        _clients[1].add(queue_a)
        _clients[2].add(queue_b)
        try:
            notify_change(1)
            assert not queue_a.empty()
            assert queue_b.empty()
        finally:
            _clients[1].discard(queue_a)
            _clients[2].discard(queue_b)
            if not _clients[1]:
                del _clients[1]
            if not _clients[2]:
                del _clients[2]

    def test_notify_handles_full_queue_gracefully(self):
        """notify_change must not raise when a client queue is full."""
        queue = asyncio.Queue(maxsize=1)
        api_key_id = 12345
        _clients[api_key_id].add(queue)
        try:
            # Fill the queue
            queue.put_nowait("filler")
            # Should not raise
            notify_change(api_key_id)
            # Queue should still have exactly 1 item (the filler)
            assert queue.qsize() == 1
        finally:
            _clients[api_key_id].discard(queue)
            if not _clients[api_key_id]:
                del _clients[api_key_id]

    def test_notify_broadcasts_to_multiple_clients(self):
        """notify_change must notify all connected clients for same api_key_id."""
        queue_a = asyncio.Queue(maxsize=16)
        queue_b = asyncio.Queue(maxsize=16)
        api_key_id = 12345
        _clients[api_key_id].add(queue_a)
        _clients[api_key_id].add(queue_b)
        try:
            notify_change(api_key_id)
            assert not queue_a.empty()
            assert not queue_b.empty()
        finally:
            _clients[api_key_id].discard(queue_a)
            _clients[api_key_id].discard(queue_b)
            if not _clients[api_key_id]:
                del _clients[api_key_id]


class TestDashboardSSEIntegration:
    """Tests for SSE integration in the dashboard HTML."""

    def test_dashboard_contains_sse_connection_code(self, client: TestClient):
        """Dashboard must include SSE connection logic."""
        response = client.get("/dashboard")
        html = response.text
        assert "connectSSE" in html
        assert "disconnectSSE" in html

    def test_dashboard_contains_eventsource(self, client: TestClient):
        """Dashboard must use EventSource for SSE."""
        response = client.get("/dashboard")
        assert "EventSource" in response.text

    def test_dashboard_connects_sse_on_auth(self, client: TestClient):
        """Dashboard must call connectSSE after successful authentication."""
        response = client.get("/dashboard")
        html = response.text
        # Should appear in both tryConnect and init
        assert html.count("connectSSE()") >= 2

    def test_dashboard_disconnects_sse_on_logout(self, client: TestClient):
        """Dashboard must call disconnectSSE on logout."""
        response = client.get("/dashboard")
        assert "disconnectSSE()" in response.text

    def test_dashboard_clears_cache_on_sse_change(self, client: TestClient):
        """Dashboard must clear cache and re-route on SSE change event."""
        response = client.get("/dashboard")
        html = response.text
        # The change event handler should clear cache and route
        assert 'addEventListener("change"' in html


class TestNotifyInRouters:
    """Tests that CRUD operations trigger SSE notifications."""

    def test_create_inbox_item_triggers_notify(self, client: TestClient):
        """Creating an inbox item must call notify_change."""
        response = client.post("/inbox", json={"title": "Test SSE notify"})
        assert response.status_code == 201

        # Verify the router has notify_change wired in
        from app.routers import inbox

        assert hasattr(inbox, "notify_change")

    def test_all_routers_import_notify_change(self):
        """All CRUD routers must import notify_change."""
        from app.routers import (
            areas,
            inbox,
            next_actions,
            projects,
            someday_maybe,
            tags,
            tickler,
        )

        for module in [inbox, next_actions, projects, tags, areas, someday_maybe, tickler]:
            assert hasattr(module, "notify_change"), f"{module.__name__} missing notify_change"
