from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Item, Tag
from app.schemas import ItemResponse, ItemUpdate
from app.sse import notify_change

router = APIRouter(prefix="/tickler", tags=["Tickler"])


class TicklerCreate(BaseModel):
    """Request body for creating a tickler item."""

    title: str
    notes: str | None = None
    tickler_date: datetime
    tag_ids: list[int] = []


class SurfaceRequest(BaseModel):
    """Request body for surfacing a tickler item."""

    destination: str = "inbox"  # inbox or next_action


@router.get("", response_model=list[ItemResponse])
def list_tickler(
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all tickler items (items with future tickler dates)."""
    now = datetime.now(timezone.utc)

    query = db.query(Item).filter(
        Item.api_key_id == api_key.id,
        Item.tickler_date.isnot(None),
    )

    if include_completed:
        query = query.filter(Item.status.notin_(["deleted"]))
    else:
        query = query.filter(
            Item.tickler_date > now,
            Item.status.notin_(["completed", "deleted"]),
        )

    if from_date:
        query = query.filter(Item.tickler_date >= from_date)

    if to_date:
        query = query.filter(Item.tickler_date <= to_date)

    items = query.order_by(Item.tickler_date).all()
    return items


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_tickler(
    tickler_data: TicklerCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a tickler item."""
    if tickler_data.tickler_date <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickler date must be in the future",
        )

    # Validate tags
    tags = []
    if tickler_data.tag_ids:
        tags = db.query(Tag).filter(Tag.id.in_(tickler_data.tag_ids), Tag.api_key_id == api_key.id).all()
        if len(tags) != len(tickler_data.tag_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more tags not found")

    item = Item(
        api_key_id=api_key.id,
        title=tickler_data.title,
        notes=tickler_data.notes,
        status="next_action",  # Will be hidden until tickler_date
        tickler_date=tickler_data.tickler_date,
    )
    item.tags = tags

    db.add(item)
    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item


@router.get("/today", response_model=list[ItemResponse])
def get_tickler_today(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Get items whose tickler date is today (items that should be processed now)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    items = (
        db.query(Item)
        .filter(
            Item.api_key_id == api_key.id,
            Item.tickler_date >= today_start,
            Item.tickler_date <= today_end,
            Item.status.notin_(["completed", "deleted"]),
        )
        .order_by(Item.tickler_date)
        .all()
    )
    return items


@router.get("/{item_id}", response_model=ItemResponse)
def get_tickler_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a specific tickler item."""
    item = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.api_key_id == api_key.id,
            Item.tickler_date.isnot(None),
            Item.status.notin_(["completed", "deleted"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tickler item not found")

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_tickler_item(
    item_id: int,
    item_data: ItemUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update a tickler item."""
    item = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.api_key_id == api_key.id,
            Item.tickler_date.isnot(None),
            Item.status.notin_(["completed", "deleted"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tickler item not found")

    if item_data.title is not None:
        item.title = item_data.title

    if item_data.notes is not None:
        item.notes = item_data.notes

    if item_data.tickler_date is not None:
        if item_data.tickler_date <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tickler date must be in the future",
            )
        item.tickler_date = item_data.tickler_date

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
def delete_tickler_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a tickler item."""
    item = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.api_key_id == api_key.id,
            Item.tickler_date.isnot(None),
            Item.status.notin_(["completed", "deleted"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tickler item not found")

    db.delete(item)
    db.commit()
    notify_change(api_key.id)


@router.post("/{item_id}/complete", response_model=ItemResponse)
def complete_tickler_item(
    item_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Mark a tickler item as complete."""
    item = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.api_key_id == api_key.id,
            Item.tickler_date.isnot(None),
            Item.status.notin_(["completed", "deleted"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tickler item not found")

    item.completed_from = item.status
    item.status = "completed"
    item.completed_at = datetime.now(timezone.utc)
    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item


@router.post("/{item_id}/surface", response_model=ItemResponse)
def surface_tickler_item(
    item_id: int,
    surface_data: SurfaceRequest | None = None,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Manually surface a tickler item now (before its date)."""
    item = (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.api_key_id == api_key.id,
            Item.tickler_date.isnot(None),
            Item.status.notin_(["completed", "deleted"]),
        )
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tickler item not found")

    # Clear the tickler date
    item.tickler_date = None

    # Set destination
    destination = surface_data.destination if surface_data else "inbox"
    if destination == "inbox":
        item.status = "inbox"
    elif destination == "next_action":
        item.status = "next_action"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid destination. Use 'inbox' or 'next_action'",
        )

    db.commit()
    notify_change(api_key.id)
    db.refresh(item)

    return item
