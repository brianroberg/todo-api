from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Item, Project, Tag
from app.schemas.schemas import (
    InboxCountResponse,
    ItemResponse,
    StaleProjectResponse,
    UpcomingDeadline,
    UpcomingDeadlinesResponse,
    WaitingForResponse,
)

router = APIRouter(prefix="/review", tags=["Weekly Review"])


@router.get("/inbox-count", response_model=InboxCountResponse)
def get_inbox_count(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Quick count of inbox items. Non-zero means stuff to process."""
    count = db.query(Item).filter(Item.api_key_id == api_key.id, Item.status == "inbox").count()
    return InboxCountResponse(count=count)


@router.get("/stale-projects", response_model=StaleProjectResponse)
def get_stale_projects(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Projects with no next action defined."""
    # Get all active projects
    active_projects = (
        db.query(Project).filter(Project.api_key_id == api_key.id, Project.status == "active").all()
    )

    stale = []
    for project in active_projects:
        # Check if project has at least one next action
        has_next_action = (
            db.query(Item)
            .filter(Item.project_id == project.id, Item.status == "next_action")
            .first()
            is not None
        )
        if not has_next_action:
            stale.append(project)

    return StaleProjectResponse(projects=stale)


@router.get("/upcoming-deadlines", response_model=UpcomingDeadlinesResponse)
def get_upcoming_deadlines(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Actions and projects with deadlines in the next N days."""
    now = datetime.utcnow()
    cutoff = now + timedelta(days=days)

    deadlines = []

    # Get items with upcoming deadlines
    items = (
        db.query(Item)
        .filter(
            Item.api_key_id == api_key.id,
            Item.due_date.isnot(None),
            Item.due_date <= cutoff,
            Item.status.notin_(["completed", "deleted"]),
        )
        .all()
    )

    for item in items:
        days_until = (item.due_date - now).days
        deadlines.append(
            UpcomingDeadline(
                type="item",
                id=item.id,
                title=item.title,
                due_date=item.due_date,
                due_date_is_hard=item.due_date_is_hard,
                days_until_due=days_until,
            )
        )

    # Get projects with upcoming deadlines
    projects = (
        db.query(Project)
        .filter(
            Project.api_key_id == api_key.id,
            Project.due_date.isnot(None),
            Project.due_date <= cutoff,
            Project.status != "completed",
        )
        .all()
    )

    for project in projects:
        days_until = (project.due_date - now).days
        deadlines.append(
            UpcomingDeadline(
                type="project",
                id=project.id,
                title=project.title,
                due_date=project.due_date,
                due_date_is_hard=project.due_date_is_hard,
                days_until_due=days_until,
            )
        )

    # Sort by days until due
    deadlines.sort(key=lambda x: x.days_until_due)

    return UpcomingDeadlinesResponse(deadlines=deadlines)


@router.get("/waiting-for", response_model=WaitingForResponse)
def get_waiting_for(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """All items with @waiting_for tag or delegated_to set."""
    # Find items with delegated_to set
    delegated_items = (
        db.query(Item)
        .filter(
            Item.api_key_id == api_key.id,
            Item.delegated_to.isnot(None),
            Item.delegated_to != "",
            Item.status.notin_(["completed", "deleted"]),
        )
        .all()
    )

    # Also find items with a tag containing "waiting" (case-insensitive)
    waiting_tag = (
        db.query(Tag)
        .filter(Tag.api_key_id == api_key.id, Tag.name.ilike("%waiting%"))
        .first()
    )

    tagged_items = []
    if waiting_tag:
        tagged_items = (
            db.query(Item)
            .filter(
                Item.api_key_id == api_key.id,
                Item.tags.contains(waiting_tag),
                Item.status.notin_(["completed", "deleted"]),
            )
            .all()
        )

    # Combine and deduplicate
    all_items = {item.id: item for item in delegated_items + tagged_items}

    return WaitingForResponse(items=list(all_items.values()))


@router.get("/overdue", response_model=list[ItemResponse])
def get_overdue_items(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Get all items that are past their due date."""
    now = datetime.utcnow()

    items = (
        db.query(Item)
        .filter(
            Item.api_key_id == api_key.id,
            Item.due_date.isnot(None),
            Item.due_date < now,
            Item.status.notin_(["completed", "deleted"]),
        )
        .order_by(Item.due_date)
        .all()
    )

    return items
