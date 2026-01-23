from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


# Junction table for Item <-> Tag many-to-many relationship
item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class ApiKey(Base):
    """API key for authentication. Each key represents a separate user/tenant."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))  # Optional friendly name for the key
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    areas = relationship("Area", back_populates="api_key", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="api_key", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="api_key", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="api_key", cascade="all, delete-orphan")


class Area(Base):
    """Area of Responsibility - ongoing roles/accountabilities."""

    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_key = relationship("ApiKey", back_populates="areas")
    projects = relationship("Project", back_populates="area")
    items = relationship("Item", back_populates="area")

    __table_args__ = (
        UniqueConstraint("api_key_id", "name", name="uq_area_apikey_name"),
        Index("ix_areas_api_key_id", "api_key_id"),
    )


class Project(Base):
    """Multi-step outcome requiring more than one action."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id", ondelete="SET NULL"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    outcome = Column(Text)  # What "done" looks like
    status = Column(String(50), default="active", nullable=False)  # active, on_hold, completed
    due_date = Column(DateTime)
    due_date_is_hard = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_key = relationship("ApiKey", back_populates="projects")
    area = relationship("Area", back_populates="projects")
    items = relationship("Item", back_populates="project")

    __table_args__ = (
        Index("ix_projects_api_key_id", "api_key_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_area_id", "area_id"),
    )


class Tag(Base):
    """Freeform tag for categorization (including @context-style tags)."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(String(7))  # Hex color like "#ff5733"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_key = relationship("ApiKey", back_populates="tags")
    items = relationship("Item", secondary=item_tags, back_populates="tags")

    __table_args__ = (
        UniqueConstraint("api_key_id", "name", name="uq_tag_apikey_name"),
        Index("ix_tags_api_key_id", "api_key_id"),
    )


class Item(Base):
    """Core task entity - inbox items, next actions, someday/maybe, completed."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)

    # Core content
    title = Column(String(500), nullable=False)
    notes = Column(Text)

    # GTD classification
    status = Column(
        String(50), default="inbox", nullable=False
    )  # inbox, next_action, someday_maybe, completed, deleted

    # Relationships
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"))
    area_id = Column(Integer, ForeignKey("areas.id", ondelete="SET NULL"))

    # Scheduling & deadlines
    tickler_date = Column(DateTime)  # Hidden until this date
    due_date = Column(DateTime)
    due_date_is_hard = Column(Boolean, default=False, nullable=False)

    # Delegation (for @waiting_for)
    delegated_to = Column(String(255))
    delegated_at = Column(DateTime)

    # Energy, time & priority
    energy_level = Column(String(20))  # low, medium, high
    time_estimate = Column(Integer)  # Minutes
    priority = Column(Integer, default=0, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    deleted_at = Column(DateTime)

    # Relationships
    api_key = relationship("ApiKey", back_populates="items")
    project = relationship("Project", back_populates="items")
    area = relationship("Area", back_populates="items")
    tags = relationship("Tag", secondary=item_tags, back_populates="items")

    __table_args__ = (
        Index("ix_items_api_key_id", "api_key_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_project_id", "project_id"),
        Index("ix_items_area_id", "area_id"),
        Index("ix_items_tickler_date", "tickler_date"),
        Index("ix_items_due_date", "due_date"),
    )
