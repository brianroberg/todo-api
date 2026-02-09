from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Item, Tag
from app.schemas import ItemResponse, TagCreate, TagUpdate
from app.schemas.schemas import TagWithCount
from app.sse import notify_change

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagWithCount])
def list_tags(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all tags."""
    tags = db.query(Tag).filter(Tag.api_key_id == api_key.id).order_by(Tag.name).all()

    result = []
    for tag in tags:
        item_count = len([item for item in tag.items if item.status not in ("completed", "deleted")])
        result.append(
            TagWithCount(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                created_at=tag.created_at,
                updated_at=tag.updated_at,
                item_count=item_count,
            )
        )
    return result


@router.post("", response_model=TagWithCount, status_code=status.HTTP_201_CREATED)
def create_tag(
    tag_data: TagCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new tag."""
    # Check for duplicate name
    existing = db.query(Tag).filter(Tag.api_key_id == api_key.id, Tag.name == tag_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists",
        )

    tag = Tag(
        api_key_id=api_key.id,
        name=tag_data.name,
        color=tag_data.color,
    )
    db.add(tag)
    db.commit()
    notify_change(api_key.id)
    db.refresh(tag)

    return TagWithCount(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        item_count=0,
    )


@router.get("/{tag_id}", response_model=TagWithCount)
def get_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve a tag and its usage count."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.api_key_id == api_key.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    item_count = len([item for item in tag.items if item.status not in ("completed", "deleted")])
    return TagWithCount(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        item_count=item_count,
    )


@router.patch("/{tag_id}", response_model=TagWithCount)
def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update a tag's name or color."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.api_key_id == api_key.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if tag_data.name is not None:
        # Check for duplicate name
        existing = (
            db.query(Tag)
            .filter(Tag.api_key_id == api_key.id, Tag.name == tag_data.name, Tag.id != tag_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists",
            )
        tag.name = tag_data.name

    if tag_data.color is not None:
        tag.color = tag_data.color

    db.commit()
    notify_change(api_key.id)
    db.refresh(tag)

    item_count = len([item for item in tag.items if item.status not in ("completed", "deleted")])
    return TagWithCount(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        item_count=item_count,
    )


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete a tag. Removes it from all items that had it."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.api_key_id == api_key.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    db.delete(tag)
    db.commit()
    notify_change(api_key.id)


@router.get("/{tag_id}/items", response_model=list[ItemResponse])
def get_tag_items(
    tag_id: int,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all items with this tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.api_key_id == api_key.id).first()
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    query = db.query(Item).filter(Item.api_key_id == api_key.id, Item.tags.contains(tag))

    if not include_completed:
        query = query.filter(Item.status.notin_(["completed", "deleted"]))

    items = query.order_by(Item.priority.desc(), Item.created_at).all()
    return items
