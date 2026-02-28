"""Donor task integration endpoints.

Reads donor tasks from the Donor Management DB and exposes them alongside
native GTD items. Status updates are pushed back to the donor DB.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import get_current_api_key
from app.models import ApiKey
from app.services.donor_client import donor_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/donor-tasks", tags=["Donor Tasks"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DonorTaskResponse(BaseModel):
    donor_task_id: int
    title: str
    status: str
    donor_status: str | None
    task_date: str | None
    notes: str | None
    is_thank: bool
    source: str


class DonorStatusUpdate(BaseModel):
    status: str


class ConsistencyReport(BaseModel):
    cache_populated: bool
    checked_count: int
    inconsistencies: list[dict] = []
    cache_age_seconds: float | None = None
    message: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[DonorTaskResponse])
async def list_donor_tasks(
    status: str | None = Query(default=None, description="Filter by donor status"),
    api_key: ApiKey = Depends(get_current_api_key),
):
    """List donor tasks, optionally filtered by donor status."""
    return await donor_client.fetch_tasks(status=status)


@router.get("/consistency", response_model=ConsistencyReport)
async def check_consistency(
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Compare cached donor tasks against a live fetch from the donor DB."""
    report = await donor_client.check_consistency()
    logger.info(
        "consistency_check: %d checked, %d inconsistencies",
        report.get("checked_count", 0),
        len(report.get("inconsistencies", [])),
    )
    return report


@router.get("/{donor_task_id}", response_model=DonorTaskResponse)
async def get_donor_task(
    donor_task_id: int,
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Fetch a single donor task by its donor DB ID."""
    task = await donor_client.get_task(donor_task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Donor task {donor_task_id} not found",
        )
    return task


@router.patch("/{donor_task_id}/status", response_model=DonorTaskResponse)
async def update_donor_task_status(
    donor_task_id: int,
    body: DonorStatusUpdate,
    api_key: ApiKey = Depends(get_current_api_key),
):
    """Push a status change back to the donor DB.

    Accepted values: 'completed', 'deleted' (maps to 'cancelled' in donor DB).
    """
    if body.status not in ("completed", "deleted"):
        raise HTTPException(
            status_code=422,
            detail="status must be 'completed' or 'deleted'",
        )

    success = await donor_client.update_status(donor_task_id, body.status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update status in donor DB",
        )

    # Try to re-fetch the updated task; fall back to a constructed response
    # if the donor DB is momentarily unavailable after the update.
    task = await donor_client.get_task(donor_task_id)
    if task is None:
        from app.services.donor_client import GTD_TO_DONOR_STATUS

        task = {
            "donor_task_id": donor_task_id,
            "title": "",
            "status": body.status,
            "donor_status": GTD_TO_DONOR_STATUS.get(body.status, body.status),
            "task_date": None,
            "notes": None,
            "is_thank": False,
            "source": "donor_db",
        }
    return task
