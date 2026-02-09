"""Tests for tickler completion and include_completed filtering."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


class TestTicklerCompletion:
    """Tests for completing tickler items."""

    def test_complete_tickler_item_sets_completed_status(self, client: TestClient):
        """POST /tickler/{id}/complete must set status to completed."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        create_response = client.post("/tickler", json={
            "title": "Follow up",
            "tickler_date": future_date,
        })
        item_id = create_response.json()["id"]

        response = client.post(f"/tickler/{item_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["completed_from"] == "next_action"

    def test_complete_nonexistent_returns_404(self, client: TestClient):
        """POST /tickler/{id}/complete for nonexistent item must return 404."""
        response = client.post("/tickler/99999/complete")
        assert response.status_code == 404

    def test_completed_items_excluded_from_list_by_default(self, client: TestClient):
        """GET /tickler must not return completed items by default."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        create_response = client.post("/tickler", json={
            "title": "To complete",
            "tickler_date": future_date,
        })
        item_id = create_response.json()["id"]

        client.post(f"/tickler/{item_id}/complete")

        response = client.get("/tickler")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_include_completed_shows_completed_items(self, client: TestClient):
        """GET /tickler?include_completed=true must return completed tickler items."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        client.post("/tickler", json={"title": "Active tickler", "tickler_date": future_date})
        complete_response = client.post("/tickler", json={
            "title": "Completed tickler",
            "tickler_date": future_date,
        })
        item_id = complete_response.json()["id"]
        client.post(f"/tickler/{item_id}/complete")

        response = client.get("/tickler?include_completed=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        titles = {item["title"] for item in items}
        assert "Active tickler" in titles
        assert "Completed tickler" in titles
