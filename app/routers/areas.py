from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_api_key
from app.database import get_db
from app.models import ApiKey, Area, Item, Project
from app.schemas import AreaCreate, AreaUpdate, ItemResponse, ProjectResponse
from app.schemas.schemas import AreaWithStats

router = APIRouter(prefix="/areas", tags=["Areas of Responsibility"])


@router.get("", response_model=list[AreaWithStats])
def list_areas(
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all areas of responsibility."""
    areas = db.query(Area).filter(Area.api_key_id == api_key.id).order_by(Area.sort_order, Area.name).all()

    result = []
    for area in areas:
        project_count = (
            db.query(Project)
            .filter(Project.area_id == area.id, Project.status == "active")
            .count()
        )
        action_count = (
            db.query(Item)
            .filter(Item.area_id == area.id, Item.status == "next_action")
            .count()
        )
        result.append(
            AreaWithStats(
                id=area.id,
                name=area.name,
                description=area.description,
                sort_order=area.sort_order,
                created_at=area.created_at,
                updated_at=area.updated_at,
                project_count=project_count,
                action_count=action_count,
            )
        )
    return result


@router.post("", response_model=AreaWithStats, status_code=status.HTTP_201_CREATED)
def create_area(
    area_data: AreaCreate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Create a new area of responsibility."""
    # Check for duplicate name
    existing = db.query(Area).filter(Area.api_key_id == api_key.id, Area.name == area_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Area with this name already exists",
        )

    area = Area(
        api_key_id=api_key.id,
        name=area_data.name,
        description=area_data.description,
        sort_order=area_data.sort_order,
    )
    db.add(area)
    db.commit()
    db.refresh(area)

    return AreaWithStats(
        id=area.id,
        name=area.name,
        description=area.description,
        sort_order=area.sort_order,
        created_at=area.created_at,
        updated_at=area.updated_at,
        project_count=0,
        action_count=0,
    )


@router.get("/{area_id}", response_model=AreaWithStats)
def get_area(
    area_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Retrieve an area with summary stats."""
    area = db.query(Area).filter(Area.id == area_id, Area.api_key_id == api_key.id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    project_count = (
        db.query(Project)
        .filter(Project.area_id == area.id, Project.status == "active")
        .count()
    )
    action_count = (
        db.query(Item)
        .filter(Item.area_id == area.id, Item.status == "next_action")
        .count()
    )

    return AreaWithStats(
        id=area.id,
        name=area.name,
        description=area.description,
        sort_order=area.sort_order,
        created_at=area.created_at,
        updated_at=area.updated_at,
        project_count=project_count,
        action_count=action_count,
    )


@router.patch("/{area_id}", response_model=AreaWithStats)
def update_area(
    area_id: int,
    area_data: AreaUpdate,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Update an area's name or description."""
    area = db.query(Area).filter(Area.id == area_id, Area.api_key_id == api_key.id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    if area_data.name is not None:
        # Check for duplicate name
        existing = (
            db.query(Area)
            .filter(Area.api_key_id == api_key.id, Area.name == area_data.name, Area.id != area_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Area with this name already exists",
            )
        area.name = area_data.name

    if area_data.description is not None:
        area.description = area_data.description

    if area_data.sort_order is not None:
        area.sort_order = area_data.sort_order

    db.commit()
    db.refresh(area)

    project_count = (
        db.query(Project)
        .filter(Project.area_id == area.id, Project.status == "active")
        .count()
    )
    action_count = (
        db.query(Item)
        .filter(Item.area_id == area.id, Item.status == "next_action")
        .count()
    )

    return AreaWithStats(
        id=area.id,
        name=area.name,
        description=area.description,
        sort_order=area.sort_order,
        created_at=area.created_at,
        updated_at=area.updated_at,
        project_count=project_count,
        action_count=action_count,
    )


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_area(
    area_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Delete an area. Projects and actions become unlinked."""
    area = db.query(Area).filter(Area.id == area_id, Area.api_key_id == api_key.id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    db.delete(area)
    db.commit()


@router.get("/{area_id}/projects", response_model=list[ProjectResponse])
def get_area_projects(
    area_id: int,
    include_completed: bool = False,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all projects under this area of responsibility."""
    area = db.query(Area).filter(Area.id == area_id, Area.api_key_id == api_key.id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    query = db.query(Project).filter(Project.area_id == area_id)

    if not include_completed:
        query = query.filter(Project.status != "completed")

    projects = query.order_by(Project.created_at.desc()).all()
    return projects


@router.get("/{area_id}/actions", response_model=list[ItemResponse])
def get_area_actions(
    area_id: int,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List all next actions linked to this area."""
    area = db.query(Area).filter(Area.id == area_id, Area.api_key_id == api_key.id).first()
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")

    # Get direct items and items from projects in this area
    direct_items = (
        db.query(Item)
        .filter(Item.area_id == area_id, Item.status == "next_action")
        .all()
    )

    # Get project IDs in this area
    project_ids = [p.id for p in db.query(Project).filter(Project.area_id == area_id).all()]

    project_items = []
    if project_ids:
        project_items = (
            db.query(Item)
            .filter(Item.project_id.in_(project_ids), Item.status == "next_action")
            .all()
        )

    # Combine and deduplicate
    all_items = {item.id: item for item in direct_items + project_items}
    return list(all_items.values())
