from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Area, Item, Project, Tag
from app.schemas import ItemCreate, ItemResponse, ProjectCreate, ProjectUpdate
from app.schemas.schemas import ProjectStatus, ProjectWithStats
from app.sse import notify_change

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_with_stats(db: Session, project: Project) -> ProjectWithStats:
    """Helper to build ProjectWithStats from a Project."""
    action_count = db.query(Item).filter(Item.project_id == project.id, Item.status != "deleted").count()
    completed_action_count = (
        db.query(Item).filter(Item.project_id == project.id, Item.status == "completed").count()
    )
    has_next_action = (
        db.query(Item).filter(Item.project_id == project.id, Item.status == "next_action").first() is not None
    )

    return ProjectWithStats(
        id=project.id,
        title=project.title,
        description=project.description,
        outcome=project.outcome,
        area_id=project.area_id,
        status=project.status,
        due_date=project.due_date,
        due_date_is_hard=project.due_date_is_hard,
        completed_at=project.completed_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
        action_count=action_count,
        completed_action_count=completed_action_count,
        has_next_action=has_next_action,
    )


@router.get("", response_model=list[ProjectWithStats])
def list_projects(
    status_filter: ProjectStatus | None = None,
    area_id: int | None = None,
    has_next_action: bool | None = None,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List projects with optional filters."""
    query = db.query(Project).filter(Project.api_key_id == api_key.id)

    if status_filter:
        query = query.filter(Project.status == status_filter.value)

    if area_id is not None:
        query = query.filter(Project.area_id == area_id)

    projects = query.order_by(Project.created_at.desc()).all()

    result = []
    for project in projects:
        project_stats = get_project_with_stats(db, project)

        # Filter by has_next_action if specified
        if has_next_action is not None:
            if has_next_action and not project_stats.has_next_action:
                continue
            if not has_next_action and project_stats.has_next_action:
                continue

        result.append(project_stats)

    return result


@router.post("", response_model=ProjectWithStats, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new project."""
    # Validate area if provided
    if project_data.area_id is not None:
        area = db.query(Area).filter(Area.id == project_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    project = Project(
        api_key_id=api_key.id,
        title=project_data.title,
        description=project_data.description,
        outcome=project_data.outcome,
        area_id=project_data.area_id,
        status=project_data.status.value,
        due_date=project_data.due_date,
        due_date_is_hard=project_data.due_date_is_hard,
    )
    db.add(project)
    db.commit()
    notify_change(api_key.id)
    db.refresh(project)

    return get_project_with_stats(db, project)


@router.get("/{project_id}", response_model=ProjectWithStats)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a project with stats."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return get_project_with_stats(db, project)


@router.patch("/{project_id}", response_model=ProjectWithStats)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update a project."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if project_data.title is not None:
        project.title = project_data.title

    if project_data.description is not None:
        project.description = project_data.description

    if project_data.outcome is not None:
        project.outcome = project_data.outcome

    if project_data.area_id is not None:
        area = db.query(Area).filter(Area.id == project_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        project.area_id = project_data.area_id

    if project_data.status is not None:
        project.status = project_data.status.value
        if project_data.status == ProjectStatus.COMPLETED:
            project.completed_at = datetime.now(timezone.utc)
        else:
            project.completed_at = None

    if project_data.due_date is not None:
        project.due_date = project_data.due_date

    if project_data.due_date_is_hard is not None:
        project.due_date_is_hard = project_data.due_date_is_hard

    db.commit()
    notify_change(api_key.id)
    db.refresh(project)

    return get_project_with_stats(db, project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a project. Actions become unlinked."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    db.delete(project)
    db.commit()
    notify_change(api_key.id)


@router.get("/{project_id}/actions", response_model=list[ItemResponse])
def get_project_actions(
    project_id: int,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all actions belonging to this project."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    query = db.query(Item).filter(Item.project_id == project_id)

    if not include_completed:
        query = query.filter(Item.status.notin_(["completed", "deleted"]))

    items = query.order_by(Item.priority.desc(), Item.sort_order, Item.created_at).all()
    return items


@router.post("/{project_id}/actions", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_project_action(
    project_id: int,
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new action directly under this project."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate tags
    tags = []
    if item_data.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")

    item = Item(
        api_key_id=api_key.id,
        title=item_data.title,
        notes=item_data.notes,
        status="next_action",
        project_id=project_id,
        area_id=item_data.area_id or project.area_id,  # Inherit area from project if not specified
        due_date=item_data.due_date,
        due_date_is_hard=item_data.due_date_is_hard,
        delegated_to=item_data.delegated_to,
        energy_level=item_data.energy_level.value if item_data.energy_level else None,
        time_estimate=item_data.time_estimate,
        priority=item_data.priority,
    )
    item.tags = tags

    db.add(item)
    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item


@router.post("/{project_id}/complete", response_model=ProjectWithStats)
def complete_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Mark project as complete."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.status = "completed"
    project.completed_at = datetime.now(timezone.utc)
    db.commit()
    notify_change(api_key.id)
    db.refresh(project)

    return get_project_with_stats(db, project)


@router.post("/{project_id}/hold", response_model=ProjectWithStats)
def hold_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Put project on hold."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.status = "on_hold"
    db.commit()
    notify_change(api_key.id)
    db.refresh(project)

    return get_project_with_stats(db, project)


@router.post("/{project_id}/activate", response_model=ProjectWithStats)
def activate_project(
    project_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Reactivate a project that was on hold or completed."""
    project = db.query(Project).filter(Project.id == project_id, Project.api_key_id == api_key.id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    project.status = "active"
    project.completed_at = None
    db.commit()
    notify_change(api_key.id)
    db.refresh(project)

    return get_project_with_stats(db, project)
