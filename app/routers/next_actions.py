from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Area, Item, Project, Tag
from app.schemas import ItemCreate, ItemResponse, ItemUpdate
from app.sse import notify_change

router = APIRouter(prefix="/next-actions", tags=["Next Actions"])


@router.get("", response_model=list[ItemResponse])
def list_next_actions(
    tag_id: int | None = None,
    project_id: int | None = None,
    area_id: int | None = None,
    energy_level: str | None = None,
    max_time: int | None = Query(default=None, description="Max time estimate in minutes"),
    due_before: datetime | None = None,
    has_deadline: bool | None = None,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all next actions with optional filters."""
    now = datetime.now(timezone.utc)

    if include_completed:
        status_filter = (Item.status == "next_action") | (
            (Item.status == "completed") & (Item.completed_from == "next_action")
        )
    else:
        status_filter = Item.status == "next_action"

    query = db.query(Item).filter(
        Item.api_key_id == api_key.id,
        status_filter,
        # Exclude tickler items that aren't yet due
        (Item.tickler_date.is_(None)) | (Item.tickler_date <= now),
    )

    if tag_id is not None:
        tag = db.query(Tag).filter(Tag.id == tag_id, Tag.api_key_id == api_key.id).first()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        query = query.filter(Item.tags.contains(tag))

    if project_id is not None:
        query = query.filter(Item.project_id == project_id)

    if area_id is not None:
        query = query.filter(Item.area_id == area_id)

    if energy_level is not None:
        query = query.filter(Item.energy_level == energy_level)

    if max_time is not None:
        query = query.filter((Item.time_estimate.is_(None)) | (Item.time_estimate <= max_time))

    if due_before is not None:
        query = query.filter(Item.due_date <= due_before)

    if has_deadline is True:
        query = query.filter(Item.due_date.isnot(None))
    elif has_deadline is False:
        query = query.filter(Item.due_date.is_(None))

    items = query.order_by(Item.priority.desc(), Item.sort_order, Item.created_at).all()
    return items


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_next_action(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a next action directly (bypassing inbox)."""
    # Validate project if provided
    if item_data.project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == item_data.project_id, Project.api_key_id == api_key.id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate area if provided
    if item_data.area_id is not None:
        area = db.query(Area).filter(Area.id == item_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

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
        project_id=item_data.project_id,
        area_id=item_data.area_id,
        tickler_date=item_data.tickler_date,
        due_date=item_data.due_date,
        due_date_is_hard=item_data.due_date_is_hard,
        delegated_to=item_data.delegated_to,
        delegated_at=datetime.now(timezone.utc) if item_data.delegated_to else None,
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


@router.get("/{item_id}", response_model=ItemResponse)
def get_next_action(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a specific next action."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "next_action")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Next action not found")

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_next_action(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update a next action."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "next_action")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Next action not found")

    if item_data.title is not None:
        item.title = item_data.title

    if item_data.notes is not None:
        item.notes = item_data.notes

    if item_data.project_id is not None:
        project = (
            db.query(Project)
            .filter(Project.id == item_data.project_id, Project.api_key_id == api_key.id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        item.project_id = item_data.project_id

    if item_data.area_id is not None:
        area = db.query(Area).filter(Area.id == item_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        item.area_id = item_data.area_id

    if item_data.tickler_date is not None:
        item.tickler_date = item_data.tickler_date

    if item_data.due_date is not None:
        item.due_date = item_data.due_date

    if item_data.due_date_is_hard is not None:
        item.due_date_is_hard = item_data.due_date_is_hard

    if item_data.delegated_to is not None:
        # Normalize empty string to None
        delegated_to = item_data.delegated_to or None
        if delegated_to and not item.delegated_to:
            item.delegated_at = datetime.now(timezone.utc)
        elif not delegated_to:
            item.delegated_at = None
        item.delegated_to = delegated_to

    if item_data.energy_level is not None:
        item.energy_level = item_data.energy_level.value

    if item_data.time_estimate is not None:
        item.time_estimate = item_data.time_estimate

    if item_data.priority is not None:
        item.priority = item_data.priority

    if item_data.sort_order is not None:
        item.sort_order = item_data.sort_order

    if item_data.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")
        item.tags = tags

    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_next_action(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a next action permanently."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "next_action")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Next action not found")

    db.delete(item)
    db.commit()
    notify_change(api_key.id)


@router.post("/{item_id}/complete", response_model=ItemResponse)
def complete_next_action(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Mark a next action as complete."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "next_action")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Next action not found")

    item.completed_from = item.status
    item.status = "completed"
    item.completed_at = datetime.now(timezone.utc)
    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item


@router.post("/{item_id}/defer", response_model=ItemResponse)
def defer_next_action(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Move a next action to Someday/Maybe."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "next_action")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Next action not found")

    item.status = "someday_maybe"
    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item
