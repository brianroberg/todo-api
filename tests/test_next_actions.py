"""Tests for next actions endpoint - managing actionable tasks."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


class TestNextActionsCRUD:
    """Tests for next action create, read, update, delete operations."""

    def test_create_next_action_returns_201(self, client: TestClient):
        """POST /next-actions must return 201 and create an item with next_action status."""
        response = client.post("/next-actions", json={"title": "Call client"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Call client"
        assert data["status"] == "next_action"

    def test_create_next_action_with_all_fields(self, client: TestClient):
        """POST /next-actions with all optional fields must store them correctly."""
        response = client.post("/next-actions", json={
            "title": "Prepare presentation",
            "notes": "For quarterly review",
            "energy_level": "high",
            "time_estimate": 60,
            "priority": 5,
            "due_date": "2030-01-15T10:00:00",
            "due_date_is_hard": True
        })
        assert response.status_code == 201
        data = response.json()
        assert data["notes"] == "For quarterly review"
        assert data["energy_level"] == "high"
        assert data["time_estimate"] == 60
        assert data["priority"] == 5
        assert data["due_date_is_hard"] is True

    def test_list_next_actions_returns_only_next_action_status(self, client: TestClient):
        """GET /next-actions must return only items with next_action status."""
        # Create a next action
        client.post("/next-actions", json={"title": "Active task"})

        # Create an inbox item
        client.post("/inbox", json={"title": "Inbox task"})

        response = client.get("/next-actions")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Active task"

    def test_get_next_action_returns_item(self, client: TestClient):
        """GET /next-actions/{id} must return the specific next action."""
        create_response = client.post("/next-actions", json={"title": "Specific task"})
        item_id = create_response.json()["id"]

        response = client.get(f"/next-actions/{item_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Specific task"

    def test_update_next_action_title(self, client: TestClient):
        """PATCH /next-actions/{id} must update the item."""
        create_response = client.post("/next-actions", json={"title": "Original"})
        item_id = create_response.json()["id"]

        response = client.patch(f"/next-actions/{item_id}", json={"title": "Updated"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_delete_next_action_returns_204(self, client: TestClient):
        """DELETE /next-actions/{id} must return 204 and remove the item."""
        create_response = client.post("/next-actions", json={"title": "To delete"})
        item_id = create_response.json()["id"]

        response = client.delete(f"/next-actions/{item_id}")
        assert response.status_code == 204


class TestNextActionsFiltering:
    """Tests for filtering next actions."""

    def test_filter_by_energy_level(self, client: TestClient):
        """GET /next-actions?energy_level=high must return only high energy items."""
        client.post("/next-actions", json={"title": "High energy", "energy_level": "high"})
        client.post("/next-actions", json={"title": "Low energy", "energy_level": "low"})

        response = client.get("/next-actions?energy_level=high")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "High energy"

    def test_filter_by_max_time(self, client: TestClient):
        """GET /next-actions?max_time=30 must return items with time_estimate <= 30."""
        client.post("/next-actions", json={"title": "Quick task", "time_estimate": 15})
        client.post("/next-actions", json={"title": "Long task", "time_estimate": 120})

        response = client.get("/next-actions?max_time=30")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Quick task"

    def test_filter_by_max_time_includes_null_time_estimate(self, client: TestClient):
        """max_time filter must include items with null time_estimate."""
        client.post("/next-actions", json={"title": "No estimate"})  # time_estimate is null
        client.post("/next-actions", json={"title": "Long task", "time_estimate": 120})

        response = client.get("/next-actions?max_time=30")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "No estimate"

    def test_filter_has_deadline_true(self, client: TestClient):
        """GET /next-actions?has_deadline=true must return only items with due_date."""
        client.post("/next-actions", json={
            "title": "With deadline",
            "due_date": "2030-01-01T00:00:00"
        })
        client.post("/next-actions", json={"title": "No deadline"})

        response = client.get("/next-actions?has_deadline=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "With deadline"

    def test_filter_has_deadline_false(self, client: TestClient):
        """GET /next-actions?has_deadline=false must return only items without due_date."""
        client.post("/next-actions", json={
            "title": "With deadline",
            "due_date": "2030-01-01T00:00:00"
        })
        client.post("/next-actions", json={"title": "No deadline"})

        response = client.get("/next-actions?has_deadline=false")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "No deadline"

    def test_filter_excludes_future_tickler_items(self, client: TestClient):
        """GET /next-actions must exclude items with future tickler_date."""
        # Create item with future tickler date
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        client.post("/next-actions", json={
            "title": "Future tickler",
            "tickler_date": future_date
        })
        # Create normal next action
        client.post("/next-actions", json={"title": "Normal action"})

        response = client.get("/next-actions")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Normal action"

    def test_filter_includes_past_tickler_items(self, client: TestClient):
        """GET /next-actions must include items with past tickler_date."""
        # Create item with past tickler date
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        client.post("/next-actions", json={
            "title": "Past tickler",
            "tickler_date": past_date
        })

        response = client.get("/next-actions")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Past tickler"


class TestNextActionsLifecycle:
    """Tests for next action lifecycle operations."""

    def test_complete_next_action_sets_completed_status(self, client: TestClient):
        """POST /next-actions/{id}/complete must set status to completed."""
        create_response = client.post("/next-actions", json={"title": "Task to complete"})
        item_id = create_response.json()["id"]

        response = client.post(f"/next-actions/{item_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_defer_next_action_sets_someday_maybe_status(self, client: TestClient):
        """POST /next-actions/{id}/defer must set status to someday_maybe."""
        create_response = client.post("/next-actions", json={"title": "Task to defer"})
        item_id = create_response.json()["id"]

        response = client.post(f"/next-actions/{item_id}/defer")
        assert response.status_code == 200
        assert response.json()["status"] == "someday_maybe"

    def test_complete_nonexistent_item_returns_404(self, client: TestClient):
        """POST /next-actions/{id}/complete for nonexistent item must return 404."""
        response = client.post("/next-actions/99999/complete")
        assert response.status_code == 404


class TestNextActionsDelegation:
    """Tests for delegation tracking."""

    def test_create_with_delegated_to_sets_delegated_at(self, client: TestClient):
        """Creating a next action with delegated_to must set delegated_at."""
        response = client.post("/next-actions", json={
            "title": "Delegated task",
            "delegated_to": "John"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["delegated_to"] == "John"
        assert data["delegated_at"] is not None

    def test_update_delegated_to_from_null_sets_delegated_at(self, client: TestClient):
        """Setting delegated_to from null must set delegated_at timestamp."""
        create_response = client.post("/next-actions", json={"title": "Task"})
        item_id = create_response.json()["id"]
        assert create_response.json()["delegated_at"] is None

        response = client.patch(f"/next-actions/{item_id}", json={"delegated_to": "Sarah"})
        assert response.status_code == 200
        data = response.json()
        assert data["delegated_to"] == "Sarah"
        assert data["delegated_at"] is not None

    def test_clear_delegated_to_clears_delegated_at(self, client: TestClient):
        """Clearing delegated_to must also clear delegated_at."""
        create_response = client.post("/next-actions", json={
            "title": "Task",
            "delegated_to": "John"
        })
        item_id = create_response.json()["id"]

        response = client.patch(f"/next-actions/{item_id}", json={"delegated_to": ""})
        assert response.status_code == 200
        data = response.json()
        assert data["delegated_to"] is None
        assert data["delegated_at"] is None


class TestNextActionsProjectIntegration:
    """Tests for project-related functionality."""

    def test_create_with_project_links_to_project(self, client: TestClient):
        """Creating next action with project_id must link to that project."""
        project_response = client.post("/projects", json={"title": "Test Project"})
        project_id = project_response.json()["id"]

        response = client.post("/next-actions", json={
            "title": "Project task",
            "project_id": project_id
        })
        assert response.status_code == 201
        assert response.json()["project_id"] == project_id

    def test_create_with_invalid_project_returns_404(self, client: TestClient):
        """Creating next action with nonexistent project_id must return 404."""
        response = client.post("/next-actions", json={
            "title": "Task",
            "project_id": 99999
        })
        assert response.status_code == 404

    def test_create_with_invalid_area_returns_404(self, client: TestClient):
        """Creating next action with nonexistent area_id must return 404."""
        response = client.post("/next-actions", json={
            "title": "Task",
            "area_id": 99999
        })
        assert response.status_code == 404

    def test_update_with_invalid_area_returns_404(self, client: TestClient):
        """Updating next action with nonexistent area_id must return 404."""
        create_response = client.post("/next-actions", json={"title": "Task"})
        item_id = create_response.json()["id"]

        response = client.patch(f"/next-actions/{item_id}", json={"area_id": 99999})
        assert response.status_code == 404

    def test_filter_by_project_id(self, client: TestClient):
        """GET /next-actions?project_id={id} must return only project items."""
        project_response = client.post("/projects", json={"title": "My Project"})
        project_id = project_response.json()["id"]

        client.post("/next-actions", json={"title": "Project task", "project_id": project_id})
        client.post("/next-actions", json={"title": "Standalone task"})

        response = client.get(f"/next-actions?project_id={project_id}")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Project task"


class TestNextActionsCompletion:
    """Tests for next action completion and include_completed filtering."""

    def test_complete_sets_completed_from(self, client: TestClient):
        """POST /next-actions/{id}/complete must set completed_from to next_action."""
        create_response = client.post("/next-actions", json={"title": "Task"})
        item_id = create_response.json()["id"]

        response = client.post(f"/next-actions/{item_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["completed_from"] == "next_action"

    def test_completed_items_excluded_from_list_by_default(self, client: TestClient):
        """GET /next-actions must not return completed items by default."""
        create_response = client.post("/next-actions", json={"title": "To complete"})
        item_id = create_response.json()["id"]

        client.post(f"/next-actions/{item_id}/complete")

        response = client.get("/next-actions")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_include_completed_shows_completed_next_actions(self, client: TestClient):
        """GET /next-actions?include_completed=true must return completed next actions."""
        create_response = client.post("/next-actions", json={"title": "Active task"})
        complete_response = client.post("/next-actions", json={"title": "Completed task"})
        item_id = complete_response.json()["id"]
        client.post(f"/next-actions/{item_id}/complete")

        response = client.get("/next-actions?include_completed=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 2
        titles = {item["title"] for item in items}
        assert "Active task" in titles
        assert "Completed task" in titles

    def test_include_completed_does_not_show_other_completed_items(self, client: TestClient):
        """GET /next-actions?include_completed=true must not return items completed from other statuses."""
        # Create and complete a someday/maybe item
        sm_response = client.post("/someday-maybe", json={"title": "Completed someday"})
        sm_id = sm_response.json()["id"]
        client.post(f"/someday-maybe/{sm_id}/complete")

        # Create a next action
        client.post("/next-actions", json={"title": "Active task"})

        response = client.get("/next-actions?include_completed=true")
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 1
        assert items[0]["title"] == "Active task"
