from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Area, Item, Project, Tag
from app.schemas import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter(prefix="/someday-maybe", tags=["Someday/Maybe"])


class ActivateRequest(BaseModel):
    """Request body for activating a someday/maybe item."""

    project_id: int | None = None
    tag_ids: list[int] = []
    due_date: datetime | None = None
    due_date_is_hard: bool = False


@router.get("", response_model=list[ItemResponse])
def list_someday_maybe(
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all someday/maybe items."""
    if include_completed:
        status_filter = (Item.status == "someday_maybe") | (
            (Item.status == "completed") & (Item.completed_from == "someday_maybe")
        )
    else:
        status_filter = Item.status == "someday_maybe"

    items = (
        db.query(Item)
        .filter(Item.api_key_id == api_key.id, status_filter)
        .order_by(Item.priority.desc(), Item.created_at.desc())
        .all()
    )
    return items


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_someday_maybe(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a someday/maybe item directly."""
    # Validate tags
    tags = []
    if item_data.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")

    # Validate area if provided
    if item_data.area_id is not None:
        area = db.query(Area).filter(Area.id == item_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    item = Item(
        api_key_id=api_key.id,
        title=item_data.title,
        notes=item_data.notes,
        status="someday_maybe",
        area_id=item_data.area_id,
        priority=item_data.priority,
    )
    item.tags = tags

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_someday_maybe(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a specific someday/maybe item."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "someday_maybe")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Someday/maybe item not found")

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_someday_maybe(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update a someday/maybe item."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "someday_maybe")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Someday/maybe item not found")

    if item_data.title is not None:
        item.title = item_data.title

    if item_data.notes is not None:
        item.notes = item_data.notes

    if item_data.area_id is not None:
        area = db.query(Area).filter(Area.id == item_data.area_id, Area.api_key_id == api_key.id).first()
        if not area:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
        item.area_id = item_data.area_id

    if item_data.priority is not None:
        item.priority = item_data.priority

    if item_data.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")
        item.tags = tags

    db.commit()
    db.refresh(item)

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_someday_maybe(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a someday/maybe item."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "someday_maybe")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Someday/maybe item not found")

    db.delete(item)
    db.commit()


@router.post("/{item_id}/complete", response_model=ItemResponse)
def complete_someday_maybe(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Mark a someday/maybe item as complete."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "someday_maybe")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Someday/maybe item not found")

    item.completed_from = item.status
    item.status = "completed"
    item.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)

    return item


@router.post("/{item_id}/activate", response_model=ItemResponse)
def activate_someday_maybe(
    item_id: int,
    activate_data: ActivateRequest | None = None,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Move item to Next Actions."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "someday_maybe")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Someday/maybe item not found")

    if activate_data:
        # Link to project if specified
        if activate_data.project_id:
            project = (
                db.query(Project)
                .filter(Project.id == activate_data.project_id, Project.api_key_id == api_key.id)
                .first()
            )
            if not project:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            item.project_id = activate_data.project_id

        # Add tags if specified
        if activate_data.tag_ids:
            tags = db.query(Tag).filter(Tag.id.in_(activate_data.tag_ids), Tag.api_key_id == api_key.id).all()
            if len(tags) != len(activate_data.tag_ids):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")
            item.tags = tags

        # Set deadline if specified
        if activate_data.due_date:
            item.due_date = activate_data.due_date
            item.due_date_is_hard = activate_data.due_date_is_hard

    item.status = "next_action"
    db.commit()
    db.refresh(item)

    return item
