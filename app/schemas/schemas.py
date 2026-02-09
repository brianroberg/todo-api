from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ItemStatus(str, Enum):
    INBOX = "inbox"
    NEXT_ACTION = "next_action"
    SOMEDAY_MAYBE = "someday_maybe"
    COMPLETED = "completed"
    DELETED = "deleted"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class EnergyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProcessDestination(str, Enum):
    NEXT_ACTION = "next_action"
    SOMEDAY_MAYBE = "someday_maybe"
    TICKLER = "tickler"
    DELETE = "delete"


# ============================================================================
# Tag Schemas
# ============================================================================


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TagResponse(BaseModel):
    id: int
    name: str
    color: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TagWithCount(TagResponse):
    item_count: int = 0


# ============================================================================
# Area Schemas
# ============================================================================


class AreaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0


class AreaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class AreaResponse(BaseModel):
    id: int
    name: str
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AreaWithStats(AreaResponse):
    project_count: int = 0
    action_count: int = 0


# ============================================================================
# Project Schemas
# ============================================================================


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    outcome: str | None = None
    area_id: int | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    due_date: datetime | None = None
    due_date_is_hard: bool = False


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    outcome: str | None = None
    area_id: int | None = None
    status: ProjectStatus | None = None
    due_date: datetime | None = None
    due_date_is_hard: bool | None = None


class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str | None
    outcome: str | None
    area_id: int | None
    status: str
    due_date: datetime | None
    due_date_is_hard: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectWithStats(ProjectResponse):
    action_count: int = 0
    completed_action_count: int = 0
    has_next_action: bool = False


# ============================================================================
# Item Schemas
# ============================================================================


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    notes: str | None = None
    project_id: int | None = None
    area_id: int | None = None
    tickler_date: datetime | None = None
    due_date: datetime | None = None
    due_date_is_hard: bool = False
    delegated_to: str | None = None
    energy_level: EnergyLevel | None = None
    time_estimate: int | None = Field(default=None, ge=1)
    priority: int = 0
    tag_ids: list[int] = []


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = None
    project_id: int | None = None
    area_id: int | None = None
    tickler_date: datetime | None = None
    due_date: datetime | None = None
    due_date_is_hard: bool | None = None
    delegated_to: str | None = None
    energy_level: EnergyLevel | None = None
    time_estimate: int | None = Field(default=None, ge=1)
    priority: int | None = None
    sort_order: int | None = None
    tag_ids: list[int] | None = None


class ItemResponse(BaseModel):
    id: int
    title: str
    notes: str | None
    status: str
    project_id: int | None
    area_id: int | None
    tickler_date: datetime | None
    due_date: datetime | None
    due_date_is_hard: bool
    delegated_to: str | None
    delegated_at: datetime | None
    energy_level: str | None
    time_estimate: int | None
    priority: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    completed_from: str | None = None
    tags: list[TagResponse] = []

    model_config = {"from_attributes": True}


class ItemProcess(BaseModel):
    destination: ProcessDestination
    tickler_date: datetime | None = None  # Required if destination is tickler
    project_id: int | None = None  # Optional: link to project
    tag_ids: list[int] = []  # Optional: add tags during processing


# ============================================================================
# Review Schemas
# ============================================================================


class InboxCountResponse(BaseModel):
    count: int


class StaleProjectResponse(BaseModel):
    projects: list[ProjectResponse]


class UpcomingDeadline(BaseModel):
    type: str  # "item" or "project"
    id: int
    title: str
    due_date: datetime
    due_date_is_hard: bool
    days_until_due: int


class UpcomingDeadlinesResponse(BaseModel):
    deadlines: list[UpcomingDeadline]


class WaitingForResponse(BaseModel):
    items: list[ItemResponse]
