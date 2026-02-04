"""Tests for inbox endpoint - capturing and processing items."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Item, Project, Tag


class TestInboxCRUD:
    """Tests for inbox create, read, update, delete operations."""

    def test_create_inbox_item_returns_201(self, client: TestClient):
        """POST /inbox must return 201 and create an item with inbox status."""
        response = client.post("/inbox", json={"title": "Buy groceries"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["status"] == "inbox"

    def test_create_inbox_item_with_notes(self, client: TestClient):
        """POST /inbox with notes must store the notes."""
        response = client.post("/inbox", json={
            "title": "Call mom",
            "notes": "Remember to ask about the recipe"
        })
        assert response.status_code == 201
        assert response.json()["notes"] == "Remember to ask about the recipe"

    def test_list_inbox_returns_only_inbox_status_items(self, client: TestClient):
        """GET /inbox must only return items with inbox status."""
        # Create inbox item via API
        client.post("/inbox", json={"title": "Inbox item"})

        # Create a next_action item via API (will have same api_key)
        client.post("/next-actions", json={"title": "Next action item"})

        response = client.get("/inbox")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Inbox item"

    def test_get_inbox_item_returns_item(self, client: TestClient):
        """GET /inbox/{id} must return the specific inbox item."""
        create_response = client.post("/inbox", json={"title": "Test item"})
        item_id = create_response.json()["id"]

        response = client.get(f"/inbox/{item_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test item"

    def test_get_nonexistent_inbox_item_returns_404(self, client: TestClient):
        """GET /inbox/{id} for nonexistent item must return 404."""
        response = client.get("/inbox/99999")
        assert response.status_code == 404

    def test_update_inbox_item_title(self, client: TestClient):
        """PATCH /inbox/{id} must update the item title."""
        create_response = client.post("/inbox", json={"title": "Original title"})
        item_id = create_response.json()["id"]

        response = client.patch(f"/inbox/{item_id}", json={"title": "Updated title"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated title"

    def test_delete_inbox_item_returns_204(self, client: TestClient):
        """DELETE /inbox/{id} must return 204 and remove the item."""
        create_response = client.post("/inbox", json={"title": "To delete"})
        item_id = create_response.json()["id"]

        response = client.delete(f"/inbox/{item_id}")
        assert response.status_code == 204

        # Verify item is gone
        get_response = client.get(f"/inbox/{item_id}")
        assert get_response.status_code == 404


class TestInboxProcessing:
    """Tests for processing inbox items to different destinations."""

    def test_process_to_next_action(self, client: TestClient):
        """Processing to next_action must change status to next_action."""
        create_response = client.post("/inbox", json={"title": "Actionable item"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "next_action"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "next_action"

    def test_process_to_someday_maybe(self, client: TestClient):
        """Processing to someday_maybe must change status to someday_maybe."""
        create_response = client.post("/inbox", json={"title": "Someday item"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "someday_maybe"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "someday_maybe"

    def test_process_to_tickler_requires_date(self, client: TestClient):
        """Processing to tickler without tickler_date must return 400."""
        create_response = client.post("/inbox", json={"title": "Tickler item"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "tickler"
        })
        assert response.status_code == 400
        assert "tickler_date" in response.json()["detail"].lower()

    def test_process_to_tickler_with_date(self, client: TestClient):
        """Processing to tickler with tickler_date must set the date and status."""
        create_response = client.post("/inbox", json={"title": "Tickler item"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "tickler",
            "tickler_date": "2030-01-01T00:00:00"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "next_action"
        assert data["tickler_date"] is not None

    def test_process_to_delete_sets_deleted_status(self, client: TestClient):
        """Processing to delete must set status to deleted and set deleted_at."""
        create_response = client.post("/inbox", json={"title": "Delete me"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "delete"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"

    def test_process_with_project_links_item_to_project(self, client: TestClient):
        """Processing with project_id must link the item to the project."""
        # Create a project first
        project_response = client.post("/projects", json={"title": "Test Project"})
        project_id = project_response.json()["id"]

        # Create and process inbox item
        create_response = client.post("/inbox", json={"title": "Project task"})
        item_id = create_response.json()["id"]

        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "next_action",
            "project_id": project_id
        })
        assert response.status_code == 200
        assert response.json()["project_id"] == project_id

    def test_process_inherits_area_from_project(self, client: TestClient):
        """When processing to a project, item should inherit project's area if item has no area."""
        # Create area
        area_response = client.post("/areas", json={"name": "Work"})
        area_id = area_response.json()["id"]

        # Create project with area
        project_response = client.post("/projects", json={
            "title": "Work Project",
            "area_id": area_id
        })
        project_id = project_response.json()["id"]

        # Create inbox item without area
        create_response = client.post("/inbox", json={"title": "Work task"})
        item_id = create_response.json()["id"]

        # Process to project - should inherit area
        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "next_action",
            "project_id": project_id
        })
        assert response.status_code == 200
        assert response.json()["area_id"] == area_id

    def test_process_nonexistent_item_returns_404(self, client: TestClient):
        """Processing a nonexistent item must return 404."""
        response = client.post("/inbox/99999/process", json={
            "destination": "next_action"
        })
        assert response.status_code == 404


class TestInboxTagHandling:
    """Tests for tag handling in inbox operations."""

    def test_create_inbox_item_with_tags(self, client: TestClient):
        """POST /inbox with tag_ids must associate tags with the item."""
        # Create a tag first
        tag_response = client.post("/tags", json={"name": "urgent"})
        tag_id = tag_response.json()["id"]

        response = client.post("/inbox", json={
            "title": "Tagged item",
            "tag_ids": [tag_id]
        })
        assert response.status_code == 201
        tags = response.json()["tags"]
        assert len(tags) == 1
        assert tags[0]["name"] == "urgent"

    def test_create_inbox_item_with_invalid_tag_returns_400(self, client: TestClient):
        """POST /inbox with nonexistent tag_id must return 400."""
        response = client.post("/inbox", json={
            "title": "Bad tags item",
            "tag_ids": [99999]
        })
        assert response.status_code == 400
        assert "tag" in response.json()["detail"].lower()

    def test_process_with_tags_adds_tags_to_item(self, client: TestClient):
        """Processing with tag_ids must add tags to the item."""
        # Create a tag
        tag_response = client.post("/tags", json={"name": "context"})
        tag_id = tag_response.json()["id"]

        # Create inbox item without tags
        create_response = client.post("/inbox", json={"title": "Process with tags"})
        item_id = create_response.json()["id"]

        # Process with tags
        response = client.post(f"/inbox/{item_id}/process", json={
            "destination": "next_action",
            "tag_ids": [tag_id]
        })
        assert response.status_code == 200
        tags = response.json()["tags"]
        assert len(tags) == 1
        assert tags[0]["name"] == "context"
