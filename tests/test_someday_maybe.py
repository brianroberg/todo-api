"""Tests for someday/maybe completion and include_completed filtering."""

from fastapi.testclient import TestClient


class TestSomedayMaybeCompletion:
    """Tests for completing someday/maybe items."""

    def test_complete_someday_maybe_sets_completed_status(self, client: TestClient):
        """POST /someday-maybe/{id}/complete must set status to completed."""
        create_response = client.post("/someday-maybe", json={"title": "Learn guitar"})
        item_id = create_response.json()["id"]

        response = client.post(f"/someday-maybe/{item_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
        assert data["completed_from"] == "someday_maybe"

    def test_complete_nonexistent_returns_404(self, client: TestClient):
        """POST /someday-maybe/{id}/complete for nonexistent item must return 404."""
        response = client.post("/someday-maybe/99999/complete")
        assert response.status_code == 404

    def test_completed_items_excluded_from_list_by_default(self, client: TestClient):
        """GET /someday-maybe must not return completed items by default."""
        create_response = client.post("/someday-maybe", json={"title": "To complete"})
        item_id = create_response.json()["id"]

        client.post(f"/someday-maybe/{item_id}/complete")

        response = client.get("/someday-maybe")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_include_completed_shows_completed_items(self, client: TestClient):
        """GET /someday-maybe?include_completed=true must return completed items."""
        client.post("/someday-maybe", json={"title": "Active item"})
        complete_response = client.post("/someday-maybe", json={"title": "Completed item"})
        item_id = complete_response.json()["id"]
        client.post(f"/someday-maybe/{item_id}/complete")

        response = client.get("/someday-maybe?include_completed=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        titles = {item["title"] for item in items}
        assert "Active item" in titles
        assert "Completed item" in titles

    def test_include_completed_does_not_show_other_completed_items(self, client: TestClient):
        """GET /someday-maybe?include_completed=true must not return items completed from other statuses."""
        # Create and complete a next action
        na_response = client.post("/next-actions", json={"title": "Completed next action"})
        na_id = na_response.json()["id"]
        client.post(f"/next-actions/{na_id}/complete")

        # Create a someday/maybe item
        client.post("/someday-maybe", json={"title": "Someday item"})

        response = client.get("/someday-maybe?include_completed=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Someday item"
