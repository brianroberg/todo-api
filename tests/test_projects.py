"""Tests for projects endpoint - managing multi-step outcomes."""

import pytest
from fastapi.testclient import TestClient


class TestProjectsCRUD:
    """Tests for project create, read, update, delete operations."""

    def test_create_project_returns_201(self, client: TestClient):
        """POST /projects must return 201 and create a project."""
        response = client.post("/projects", json={"title": "Launch website"})
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Launch website"
        assert data["status"] == "active"

    def test_create_project_with_all_fields(self, client: TestClient):
        """POST /projects with all optional fields must store them."""
        response = client.post("/projects", json={
            "title": "Product Launch",
            "description": "Launch new product line",
            "outcome": "Product is available for purchase",
            "due_date": "2030-06-01T00:00:00",
            "due_date_is_hard": True
        })
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Launch new product line"
        assert data["outcome"] == "Product is available for purchase"
        assert data["due_date_is_hard"] is True

    def test_list_projects_returns_all_projects(self, client: TestClient):
        """GET /projects must return all projects."""
        client.post("/projects", json={"title": "Project A"})
        client.post("/projects", json={"title": "Project B"})

        response = client.get("/projects")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 2

    def test_get_project_returns_project_with_stats(self, client: TestClient):
        """GET /projects/{id} must return the project with stats."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Project"
        assert "action_count" in data
        assert "has_next_action" in data

    def test_update_project_title(self, client: TestClient):
        """PATCH /projects/{id} must update the project."""
        create_response = client.post("/projects", json={"title": "Original"})
        project_id = create_response.json()["id"]

        response = client.patch(f"/projects/{project_id}", json={"title": "Updated"})
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_delete_project_returns_204(self, client: TestClient):
        """DELETE /projects/{id} must return 204."""
        create_response = client.post("/projects", json={"title": "To delete"})
        project_id = create_response.json()["id"]

        response = client.delete(f"/projects/{project_id}")
        assert response.status_code == 204


class TestProjectsFiltering:
    """Tests for project filtering."""

    def test_filter_by_status_active(self, client: TestClient):
        """GET /projects?status_filter=active must return only active projects."""
        client.post("/projects", json={"title": "Active Project"})
        # Create and complete another project
        create_response = client.post("/projects", json={"title": "Completed Project"})
        client.post(f"/projects/{create_response.json()['id']}/complete")

        response = client.get("/projects?status_filter=active")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["title"] == "Active Project"

    def test_filter_by_status_completed(self, client: TestClient):
        """GET /projects?status_filter=completed must return only completed projects."""
        client.post("/projects", json={"title": "Active Project"})
        create_response = client.post("/projects", json={"title": "Completed Project"})
        client.post(f"/projects/{create_response.json()['id']}/complete")

        response = client.get("/projects?status_filter=completed")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["title"] == "Completed Project"

    def test_filter_by_has_next_action_true(self, client: TestClient):
        """GET /projects?has_next_action=true must return projects with next actions."""
        # Create project without actions
        client.post("/projects", json={"title": "Empty Project"})

        # Create project with actions
        project_response = client.post("/projects", json={"title": "Project With Actions"})
        project_id = project_response.json()["id"]
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})

        response = client.get("/projects?has_next_action=true")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["title"] == "Project With Actions"

    def test_filter_by_has_next_action_false(self, client: TestClient):
        """GET /projects?has_next_action=false must return projects without next actions."""
        # Create project without actions
        client.post("/projects", json={"title": "Empty Project"})

        # Create project with actions
        project_response = client.post("/projects", json={"title": "Project With Actions"})
        project_id = project_response.json()["id"]
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})

        response = client.get("/projects?has_next_action=false")
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) == 1
        assert projects[0]["title"] == "Empty Project"


class TestProjectsStatusLifecycle:
    """Tests for project status transitions."""

    def test_complete_project_sets_completed_status_and_timestamp(self, client: TestClient):
        """POST /projects/{id}/complete must set status and completed_at."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.post(f"/projects/{project_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_hold_project_sets_on_hold_status(self, client: TestClient):
        """POST /projects/{id}/hold must set status to on_hold."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.post(f"/projects/{project_id}/hold")
        assert response.status_code == 200
        assert response.json()["status"] == "on_hold"

    def test_activate_project_sets_active_status_and_clears_completed_at(self, client: TestClient):
        """POST /projects/{id}/activate must set status to active and clear completed_at."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        # Complete first
        client.post(f"/projects/{project_id}/complete")

        # Then activate
        response = client.post(f"/projects/{project_id}/activate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["completed_at"] is None

    def test_update_status_to_completed_sets_completed_at(self, client: TestClient):
        """PATCH /projects/{id} with status=completed must set completed_at."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.patch(f"/projects/{project_id}", json={"status": "completed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    def test_update_status_from_completed_clears_completed_at(self, client: TestClient):
        """PATCH /projects/{id} changing from completed must clear completed_at."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        # Complete first
        client.patch(f"/projects/{project_id}", json={"status": "completed"})

        # Change to active
        response = client.patch(f"/projects/{project_id}", json={"status": "active"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["completed_at"] is None


class TestProjectsStats:
    """Tests for project statistics calculation."""

    def test_action_count_reflects_project_items(self, client: TestClient):
        """Project action_count must reflect number of non-deleted items."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        # Add 2 actions
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 2"})

        response = client.get(f"/projects/{project_id}")
        assert response.json()["action_count"] == 2

    def test_completed_action_count_reflects_completed_items(self, client: TestClient):
        """Project completed_action_count must reflect completed items."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        # Add 2 actions
        action1 = client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 2"})

        # Complete one
        action_id = action1.json()["id"]
        client.post(f"/next-actions/{action_id}/complete")

        response = client.get(f"/projects/{project_id}")
        data = response.json()
        assert data["action_count"] == 2
        assert data["completed_action_count"] == 1

    def test_has_next_action_true_when_next_action_exists(self, client: TestClient):
        """has_next_action must be True when project has next_action items."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        # Add an action
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})

        response = client.get(f"/projects/{project_id}")
        assert response.json()["has_next_action"] is True

    def test_has_next_action_false_when_no_next_actions(self, client: TestClient):
        """has_next_action must be False when project has no next_action items."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.get(f"/projects/{project_id}")
        assert response.json()["has_next_action"] is False


class TestProjectsActions:
    """Tests for project action management."""

    def test_create_project_action_returns_201(self, client: TestClient):
        """POST /projects/{id}/actions must create an action under the project."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        response = client.post(f"/projects/{project_id}/actions", json={
            "title": "New task"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New task"
        assert data["project_id"] == project_id
        assert data["status"] == "next_action"

    def test_create_project_action_inherits_area_from_project(self, client: TestClient):
        """Creating action under project without area_id must inherit project's area."""
        # Create area
        area_response = client.post("/areas", json={"name": "Work"})
        area_id = area_response.json()["id"]

        # Create project with area
        project_response = client.post("/projects", json={
            "title": "Work Project",
            "area_id": area_id
        })
        project_id = project_response.json()["id"]

        # Create action without specifying area
        response = client.post(f"/projects/{project_id}/actions", json={
            "title": "Work task"
        })
        assert response.status_code == 201
        assert response.json()["area_id"] == area_id

    def test_create_project_action_explicit_area_not_overridden(self, client: TestClient):
        """Creating action with explicit area_id must not be overridden by project's area."""
        # Create two areas
        area1 = client.post("/areas", json={"name": "Work"}).json()["id"]
        area2 = client.post("/areas", json={"name": "Personal"}).json()["id"]

        # Create project with area1
        project = client.post("/projects", json={
            "title": "Work Project",
            "area_id": area1
        }).json()["id"]

        # Create action with explicit area2
        response = client.post(f"/projects/{project}/actions", json={
            "title": "Personal task in work project",
            "area_id": area2
        })
        assert response.status_code == 201
        assert response.json()["area_id"] == area2

    def test_list_project_actions_returns_actions(self, client: TestClient):
        """GET /projects/{id}/actions must return project actions."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 2"})

        response = client.get(f"/projects/{project_id}/actions")
        assert response.status_code == 200
        actions = response.json()
        assert len(actions) == 2

    def test_list_project_actions_excludes_completed_by_default(self, client: TestClient):
        """GET /projects/{id}/actions must exclude completed actions by default."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        action1 = client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 2"})

        # Complete one
        client.post(f"/next-actions/{action1.json()['id']}/complete")

        response = client.get(f"/projects/{project_id}/actions")
        assert response.status_code == 200
        actions = response.json()
        assert len(actions) == 1
        assert actions[0]["title"] == "Task 2"

    def test_list_project_actions_include_completed(self, client: TestClient):
        """GET /projects/{id}/actions?include_completed=true must include completed."""
        create_response = client.post("/projects", json={"title": "Test Project"})
        project_id = create_response.json()["id"]

        action1 = client.post(f"/projects/{project_id}/actions", json={"title": "Task 1"})
        client.post(f"/projects/{project_id}/actions", json={"title": "Task 2"})

        # Complete one
        client.post(f"/next-actions/{action1.json()['id']}/complete")

        response = client.get(f"/projects/{project_id}/actions?include_completed=true")
        assert response.status_code == 200
        actions = response.json()
        assert len(actions) == 2
