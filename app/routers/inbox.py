from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Item, Project, Tag
from app.schemas import ItemCreate, ItemProcess, ItemResponse, ItemUpdate
from app.schemas.schemas import ProcessDestination

router = APIRouter(prefix="/inbox", tags=["Inbox"])


@router.get("", response_model=list[ItemResponse])
def list_inbox(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all items in the inbox (unprocessed items)."""
    items = (
        db.query(Item)
        .filter(Item.api_key_id == api_key.id, Item.status == "inbox")
        .order_by(Item.created_at.desc())
        .all()
    )
    return items


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_inbox_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Capture a new item into the inbox."""
    # Validate tags if provided
    tags = []
    if item_data.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")

    item = Item(
        api_key_id=api_key.id,
        title=item_data.title,
        notes=item_data.notes,
        status="inbox",
    )
    item.tags = tags

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_inbox_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a specific inbox item."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "inbox")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbox item not found")

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_inbox_item(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update an inbox item before processing."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "inbox")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbox item not found")

    if item_data.title is not None:
        item.title = item_data.title

    if item_data.notes is not None:
        item.notes = item_data.notes

    if item_data.tag_ids is not None:
        tags = db.query(Tag).filter(Tag.id.in_(item_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(item_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")
        item.tags = tags

    db.commit()
    db.refresh(item)

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inbox_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete an inbox item permanently."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "inbox")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbox item not found")

    db.delete(item)
    db.commit()


@router.post("/{item_id}/process", response_model=ItemResponse)
def process_inbox_item(
    item_id: int,
    process_data: ItemProcess,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Process an inbox item by moving it to its destination."""
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.api_key_id == api_key.id, Item.status == "inbox")
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inbox item not found")

    # Handle tags
    if process_data.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(process_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(process_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")
        item.tags = tags

    # Link to project if specified
    if process_data.project_id:
        project = (
            db.query(Project)
            .filter(Project.id == process_data.project_id, Project.api_key_id == api_key.id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        item.project_id = process_data.project_id
        # Inherit area from project if item doesn't have one
        if not item.area_id and project.area_id:
            item.area_id = project.area_id

    # Process based on destination
    if process_data.destination == ProcessDestination.NEXT_ACTION:
        item.status = "next_action"

    elif process_data.destination == ProcessDestination.SOMEDAY_MAYBE:
        item.status = "someday_maybe"

    elif process_data.destination == ProcessDestination.TICKLER:
        if not process_data.tickler_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tickler_date is required for tickler destination",
            )
        item.tickler_date = process_data.tickler_date
        item.status = "next_action"  # Will be hidden until tickler_date

    elif process_data.destination == ProcessDestination.DELETE:
        item.status = "deleted"
        item.deleted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(item)

    return item
