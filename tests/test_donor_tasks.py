"""Tests for donor task integration — service layer and router endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.donor_client import DonorClient, _build_title, _map_task, _cache


class TestBuildTitle:
    """Unit tests for title assembly from donor task fields."""

    def test_no_contacts_returns_description_only(self):
        assert _build_title("Call donor", []) == "Call donor"

    def test_one_contact_appends_name(self):
        contacts = [{"id": 1, "file_as": "Smith, John"}]
        assert _build_title("Call donor", contacts) == "Call donor - Smith, John"

    def test_two_contacts_joins_with_ampersand(self):
        contacts = [
            {"id": 1, "file_as": "Smith, John"},
            {"id": 2, "file_as": "Doe, Jane"},
        ]
        assert _build_title("Lunch", contacts) == "Lunch - Smith, John & Doe, Jane"

    def test_falls_back_to_id_when_file_as_is_none(self):
        contacts = [{"id": 9, "file_as": None}]
        assert _build_title("Meeting", contacts) == "Meeting - 9"

    def test_falls_back_to_id_when_file_as_missing(self):
        contacts = [{"id": 5}]
        assert _build_title("Email", contacts) == "Email - 5"


def _raw_task(*, status="pending", contacts=None, **overrides):
    """Helper to build a raw donor task dict."""
    base = {
        "id": 1,
        "description": "Call donor",
        "status": status,
        "task_date": "2024-06-01",
        "task_time": None,
        "notes": None,
        "is_thank": False,
        "contacts": contacts or [],
    }
    base.update(overrides)
    return base


class TestMapTask:
    """Unit tests for mapping donor DB tasks to GTD-shaped dicts."""

    def test_pending_maps_to_next_action(self):
        result = _map_task(_raw_task(status="pending"))
        assert result["status"] == "next_action"
        assert result["donor_status"] == "pending"

    def test_completed_maps_to_completed(self):
        result = _map_task(_raw_task(status="completed"))
        assert result["status"] == "completed"

    def test_cancelled_maps_to_deleted(self):
        result = _map_task(_raw_task(status="cancelled"))
        assert result["status"] == "deleted"

    def test_unknown_status_defaults_to_next_action(self):
        result = _map_task(_raw_task(status="some_future_status"))
        assert result["status"] == "next_action"

    def test_preserves_donor_task_id(self):
        result = _map_task(_raw_task(id=42))
        assert result["donor_task_id"] == 42

    def test_builds_title_with_contacts(self):
        contacts = [{"id": 1, "file_as": "Smith, John"}]
        result = _map_task(_raw_task(contacts=contacts))
        assert result["title"] == "Call donor - Smith, John"

    def test_source_is_donor_db(self):
        result = _map_task(_raw_task())
        assert result["source"] == "donor_db"

    def test_preserves_task_date_and_notes(self):
        result = _map_task(_raw_task(task_date="2024-12-25", notes="Important"))
        assert result["task_date"] == "2024-12-25"
        assert result["notes"] == "Important"


# ---------------------------------------------------------------------------
# Mapped task fixture for reuse
# ---------------------------------------------------------------------------

MAPPED_TASK = _map_task(_raw_task(id=42, contacts=[{"id": 1, "file_as": "Smith, John"}]))


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the module-level cache before each test."""
    _cache.tasks = []
    _cache.fetched_at = 0.0
    _cache.stale = True
    yield
    _cache.tasks = []
    _cache.fetched_at = 0.0
    _cache.stale = True


# ---------------------------------------------------------------------------
# DonorClient tests — use httpx mock transport, no real HTTP
# ---------------------------------------------------------------------------


def _mock_client(handler):
    """Create a DonorClient with a mocked httpx.AsyncClient using a custom transport."""
    import httpx

    transport = httpx.MockTransport(handler)
    client = DonorClient()
    client._client = httpx.AsyncClient(transport=transport, base_url="http://test")
    return client


class TestDonorClientFetchTasks:
    """Tests for DonorClient.fetch_tasks()."""

    @pytest.mark.asyncio
    async def test_fetches_and_maps_tasks(self):
        """Successful fetch returns mapped tasks and populates cache."""
        raw_list = [_raw_task(id=1), _raw_task(id=2)]
        detail_1 = {**_raw_task(id=1), "contacts": [{"id": 10, "file_as": "Smith"}]}
        detail_2 = {**_raw_task(id=2), "contacts": []}

        def handler(request):
            import httpx
            if request.url.path == "/api/v1/tasks":
                return httpx.Response(200, json=raw_list)
            if request.url.path == "/api/v1/tasks/1":
                return httpx.Response(200, json=detail_1)
            if request.url.path == "/api/v1/tasks/2":
                return httpx.Response(200, json=detail_2)
            return httpx.Response(404)

        client = _mock_client(handler)
        tasks = await client.fetch_tasks()

        assert len(tasks) == 2
        assert tasks[0]["donor_task_id"] == 1
        assert tasks[0]["title"] == "Call donor - Smith"
        assert tasks[1]["title"] == "Call donor"
        # Cache should be populated
        assert len(_cache.tasks) == 2
        assert _cache.stale is False

    @pytest.mark.asyncio
    async def test_returns_cache_on_http_error(self):
        """When donor DB is unreachable, returns cached tasks."""
        _cache.tasks = [MAPPED_TASK]
        _cache.stale = True  # Force fetch attempt

        def handler(request):
            raise Exception("Connection refused")

        client = _mock_client(handler)
        tasks = await client.fetch_tasks()

        assert len(tasks) == 1
        assert tasks[0]["donor_task_id"] == 42

    @pytest.mark.asyncio
    async def test_returns_fresh_cache_without_http_call(self):
        """When cache is fresh (not stale, within TTL), no HTTP call is made."""
        import time

        _cache.tasks = [MAPPED_TASK]
        _cache.stale = False
        _cache.fetched_at = time.monotonic()  # Just now

        call_count = 0

        def handler(request):
            nonlocal call_count
            call_count += 1
            import httpx
            return httpx.Response(200, json=[])

        client = _mock_client(handler)
        tasks = await client.fetch_tasks()

        assert len(tasks) == 1
        assert call_count == 0  # No HTTP call made

    @pytest.mark.asyncio
    async def test_filters_by_status_locally(self):
        """Status filter is applied locally after fetching all tasks."""
        raw_list = [
            _raw_task(id=1, status="pending"),
            _raw_task(id=2, status="completed"),
        ]
        detail_1 = {**_raw_task(id=1, status="pending"), "contacts": []}
        detail_2 = {**_raw_task(id=2, status="completed"), "contacts": []}

        def handler(request):
            import httpx
            if request.url.path == "/api/v1/tasks":
                # Should NOT have a status param — always fetches all
                assert "status" not in request.url.params
                return httpx.Response(200, json=raw_list)
            if request.url.path == "/api/v1/tasks/1":
                return httpx.Response(200, json=detail_1)
            if request.url.path == "/api/v1/tasks/2":
                return httpx.Response(200, json=detail_2)
            return httpx.Response(404)

        client = _mock_client(handler)
        tasks = await client.fetch_tasks(status="pending")
        assert len(tasks) == 1
        assert tasks[0]["donor_status"] == "pending"
        # Cache should contain ALL tasks, not just the filtered subset
        assert len(_cache.tasks) == 2


class TestDonorClientGetTask:
    """Tests for DonorClient.get_task()."""

    @pytest.mark.asyncio
    async def test_returns_mapped_task(self):
        detail = {**_raw_task(id=5), "contacts": [{"id": 1, "file_as": "Doe"}]}

        def handler(request):
            import httpx
            return httpx.Response(200, json=detail)

        client = _mock_client(handler)
        task = await client.get_task(5)
        assert task is not None
        assert task["donor_task_id"] == 5
        assert task["title"] == "Call donor - Doe"

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        def handler(request):
            import httpx
            return httpx.Response(404)

        client = _mock_client(handler)
        assert await client.get_task(999) is None

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        def handler(request):
            raise Exception("timeout")

        client = _mock_client(handler)
        assert await client.get_task(1) is None


class TestDonorClientUpdateStatus:
    """Tests for DonorClient.update_status()."""

    @pytest.mark.asyncio
    async def test_completed_posts_to_complete_endpoint(self):
        called_path = None

        def handler(request):
            nonlocal called_path
            called_path = request.url.path
            import httpx
            return httpx.Response(200, json=_raw_task(id=5, status="completed"))

        client = _mock_client(handler)
        result = await client.update_status(5, "completed")
        assert result is True
        assert called_path == "/api/v1/tasks/5/complete"

    @pytest.mark.asyncio
    async def test_deleted_puts_cancelled_status(self):
        sent_json = None

        def handler(request):
            nonlocal sent_json
            import json as json_mod
            import httpx
            sent_json = json_mod.loads(request.content)
            return httpx.Response(200, json=_raw_task(id=5, status="cancelled"))

        client = _mock_client(handler)
        result = await client.update_status(5, "deleted")
        assert result is True
        assert sent_json == {"status": "cancelled"}

    @pytest.mark.asyncio
    async def test_invalidates_cache_on_success(self):
        _cache.stale = False

        def handler(request):
            import httpx
            return httpx.Response(200, json=_raw_task(id=5, status="completed"))

        client = _mock_client(handler)
        await client.update_status(5, "completed")
        assert _cache.stale is True

    @pytest.mark.asyncio
    async def test_unsupported_status_returns_false(self):
        client = DonorClient()
        result = await client.update_status(5, "inbox")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self):
        def handler(request):
            raise Exception("connection refused")

        client = _mock_client(handler)
        result = await client.update_status(5, "completed")
        assert result is False


class TestDonorClientConsistency:
    """Tests for DonorClient.check_consistency()."""

    @pytest.mark.asyncio
    async def test_returns_not_populated_when_cache_empty(self):
        client = DonorClient()
        report = await client.check_consistency()
        assert report["cache_populated"] is False

    @pytest.mark.asyncio
    async def test_detects_status_drift(self):
        # Cache says task 1 is next_action (pending)
        _cache.tasks = [_map_task(_raw_task(id=1, status="pending"))]
        _cache.stale = False
        _cache.fetched_at = __import__("time").monotonic()

        # Live says task 1 is now completed
        live_list = [_raw_task(id=1, status="completed")]

        def handler(request):
            import httpx
            return httpx.Response(200, json=live_list)

        client = _mock_client(handler)
        report = await client.check_consistency()
        assert report["cache_populated"] is True
        assert len(report["inconsistencies"]) == 1
        assert report["inconsistencies"][0]["donor_task_id"] == 1
        assert report["inconsistencies"][0]["cached_status"] == "next_action"
        assert report["inconsistencies"][0]["live_status"] == "completed"

    @pytest.mark.asyncio
    async def test_no_inconsistencies_when_in_sync(self):
        _cache.tasks = [_map_task(_raw_task(id=1, status="pending"))]
        _cache.stale = False
        _cache.fetched_at = __import__("time").monotonic()

        live_list = [_raw_task(id=1, status="pending")]

        def handler(request):
            import httpx
            return httpx.Response(200, json=live_list)

        client = _mock_client(handler)
        report = await client.check_consistency()
        assert report["inconsistencies"] == []

    @pytest.mark.asyncio
    async def test_detects_tasks_missing_from_live(self):
        _cache.tasks = [_map_task(_raw_task(id=99, status="pending"))]
        _cache.stale = False
        _cache.fetched_at = __import__("time").monotonic()

        def handler(request):
            import httpx
            return httpx.Response(200, json=[])  # Empty live

        client = _mock_client(handler)
        report = await client.check_consistency()
        assert len(report["inconsistencies"]) == 1
        assert report["inconsistencies"][0]["live_status"] == "missing_from_live"


# ===========================================================================
# Router endpoint tests — use existing client/client_no_auth from conftest
# ===========================================================================

_PATCH_BASE = "app.routers.donor_tasks.donor_client"


class TestListDonorTasksEndpoint:
    """GET /donor-tasks"""

    def test_returns_empty_list(self, client):
        with patch(f"{_PATCH_BASE}.fetch_tasks", new=AsyncMock(return_value=[])):
            resp = client.get("/donor-tasks")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_mapped_tasks(self, client):
        with patch(f"{_PATCH_BASE}.fetch_tasks", new=AsyncMock(return_value=[MAPPED_TASK])):
            resp = client.get("/donor-tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["donor_task_id"] == 42
        assert data[0]["status"] == "next_action"
        assert data[0]["source"] == "donor_db"

    def test_passes_status_filter(self, client):
        mock_fetch = AsyncMock(return_value=[MAPPED_TASK])
        with patch(f"{_PATCH_BASE}.fetch_tasks", new=mock_fetch):
            resp = client.get("/donor-tasks?status=pending")
        assert resp.status_code == 200
        mock_fetch.assert_awaited_once_with(status="pending")

    def test_requires_auth(self, client_no_auth):
        resp = client_no_auth.get("/donor-tasks")
        assert resp.status_code == 401


class TestGetDonorTaskEndpoint:
    """GET /donor-tasks/{id}"""

    def test_returns_task(self, client):
        with patch(f"{_PATCH_BASE}.get_task", new=AsyncMock(return_value=MAPPED_TASK)):
            resp = client.get("/donor-tasks/42")
        assert resp.status_code == 200
        assert resp.json()["donor_task_id"] == 42

    def test_returns_404_when_not_found(self, client):
        with patch(f"{_PATCH_BASE}.get_task", new=AsyncMock(return_value=None)):
            resp = client.get("/donor-tasks/999")
        assert resp.status_code == 404

    def test_requires_auth(self, client_no_auth):
        resp = client_no_auth.get("/donor-tasks/1")
        assert resp.status_code == 401


class TestUpdateDonorTaskStatusEndpoint:
    """PATCH /donor-tasks/{id}/status"""

    def test_complete_returns_updated_task(self, client):
        completed = {**MAPPED_TASK, "status": "completed", "donor_status": "completed"}
        with (
            patch(f"{_PATCH_BASE}.update_status", new=AsyncMock(return_value=True)),
            patch(f"{_PATCH_BASE}.get_task", new=AsyncMock(return_value=completed)),
        ):
            resp = client.patch("/donor-tasks/42/status", json={"status": "completed"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_delete_maps_to_cancelled(self, client):
        cancelled = {**MAPPED_TASK, "status": "deleted", "donor_status": "cancelled"}
        mock_update = AsyncMock(return_value=True)
        with (
            patch(f"{_PATCH_BASE}.update_status", new=mock_update),
            patch(f"{_PATCH_BASE}.get_task", new=AsyncMock(return_value=cancelled)),
        ):
            resp = client.patch("/donor-tasks/42/status", json={"status": "deleted"})
        assert resp.status_code == 200
        mock_update.assert_awaited_once_with(42, "deleted")

    def test_invalid_status_returns_422(self, client):
        resp = client.patch("/donor-tasks/42/status", json={"status": "inbox"})
        assert resp.status_code == 422

    def test_returns_502_when_donor_db_fails(self, client):
        with patch(f"{_PATCH_BASE}.update_status", new=AsyncMock(return_value=False)):
            resp = client.patch("/donor-tasks/42/status", json={"status": "completed"})
        assert resp.status_code == 502

    def test_returns_fallback_when_refetch_fails(self, client):
        """When update succeeds but re-fetch returns None, return a fallback response."""
        with (
            patch(f"{_PATCH_BASE}.update_status", new=AsyncMock(return_value=True)),
            patch(f"{_PATCH_BASE}.get_task", new=AsyncMock(return_value=None)),
        ):
            resp = client.patch("/donor-tasks/42/status", json={"status": "completed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["donor_task_id"] == 42
        assert data["status"] == "completed"
        assert data["donor_status"] == "completed"

    def test_requires_auth(self, client_no_auth):
        resp = client_no_auth.patch("/donor-tasks/1/status", json={"status": "completed"})
        assert resp.status_code == 401


class TestConsistencyEndpoint:
    """GET /donor-tasks/consistency"""

    def test_returns_report(self, client):
        report = {
            "cache_populated": True,
            "cache_age_seconds": 12.3,
            "checked_count": 5,
            "inconsistencies": [],
        }
        with patch(f"{_PATCH_BASE}.check_consistency", new=AsyncMock(return_value=report)):
            resp = client.get("/donor-tasks/consistency")
        assert resp.status_code == 200
        assert resp.json()["checked_count"] == 5
        assert resp.json()["inconsistencies"] == []

    def test_reports_drift(self, client):
        report = {
            "cache_populated": True,
            "cache_age_seconds": 60.0,
            "checked_count": 3,
            "inconsistencies": [
                {"donor_task_id": 7, "cached_status": "next_action", "live_status": "completed"}
            ],
        }
        with patch(f"{_PATCH_BASE}.check_consistency", new=AsyncMock(return_value=report)):
            resp = client.get("/donor-tasks/consistency")
        assert resp.status_code == 200
        assert len(resp.json()["inconsistencies"]) == 1

    def test_requires_auth(self, client_no_auth):
        resp = client_no_auth.get("/donor-tasks/consistency")
        assert resp.status_code == 401
