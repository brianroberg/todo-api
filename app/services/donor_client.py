"""HTTP client for reading donor tasks from the Donor Management DB."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------

DONOR_TO_GTD_STATUS: dict[str, str] = {
    "pending": "next_action",
    "completed": "completed",
    "cancelled": "deleted",
}

GTD_TO_DONOR_STATUS: dict[str, str] = {
    "completed": "completed",
    "deleted": "cancelled",
}

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

CACHE_TTL_SECONDS = 300


@dataclass
class _Cache:
    tasks: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: float = 0.0
    stale: bool = True


_cache = _Cache()


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _build_title(description: str, contacts: list[dict[str, Any]]) -> str:
    """Assemble GTD display title from donor task fields."""
    if not contacts:
        return description
    names = [c.get("file_as") or str(c["id"]) for c in contacts]
    return f"{description} - {' & '.join(names)}"


def _map_task(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a donor TaskResponse dict to a GTD-shaped representation."""
    return {
        "donor_task_id": raw["id"],
        "title": _build_title(raw.get("description", ""), raw.get("contacts", [])),
        "status": DONOR_TO_GTD_STATUS.get(raw.get("status", ""), "next_action"),
        "donor_status": raw.get("status"),
        "task_date": raw.get("task_date"),
        "notes": raw.get("notes"),
        "is_thank": raw.get("is_thank", False),
        "source": "donor_db",
    }


# ---------------------------------------------------------------------------
# DonorClient
# ---------------------------------------------------------------------------


class DonorClient:
    """Async HTTP client for the Donor Management DB tasks API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url: str = settings.donor_db_url.rstrip("/") if settings.donor_db_url else ""
        self._headers: dict[str, str] = (
            {"X-API-Key": settings.donor_db_api_key} if settings.donor_db_api_key else {}
        )
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._headers,
                timeout=10.0,
            )
        return self._client

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Fetch tasks
    # ------------------------------------------------------------------

    async def fetch_tasks(self, *, status: str | None = None) -> list[dict[str, Any]]:
        """Fetch donor tasks. Returns cached data on failure."""
        now = time.monotonic()

        # Return fresh cache without HTTP call
        if not _cache.stale and (now - _cache.fetched_at) < CACHE_TTL_SECONDS:
            tasks = _cache.tasks
            if status:
                tasks = [t for t in tasks if t["donor_status"] == status]
            return tasks

        try:
            client = self._get_client()
            # Always fetch all tasks to avoid poisoning cache with filtered subsets
            resp = await client.get("/api/v1/tasks", params={"limit": 500})
            resp.raise_for_status()
            raw_list: list[dict[str, Any]] = resp.json()

            enriched = await self._enrich_contacts(client, raw_list)
            mapped = [_map_task(r) for r in enriched]

            _cache.tasks = mapped
            _cache.fetched_at = time.monotonic()
            _cache.stale = False
            logger.info("donor_client: fetched %d tasks", len(mapped))

            if status:
                mapped = [t for t in mapped if t["donor_status"] == status]
            return mapped

        except Exception as exc:
            logger.warning("donor_client: fetch failed (%s), serving cached tasks", exc)
            tasks = _cache.tasks
            if status:
                tasks = [t for t in tasks if t["donor_status"] == status]
            return tasks

    async def _enrich_contacts(
        self,
        client: httpx.AsyncClient,
        tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Fetch full task detail (with contacts) for each task."""
        sem = asyncio.Semaphore(20)

        async def _fetch_one(task: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                try:
                    resp = await client.get(f"/api/v1/tasks/{task['id']}")
                    if resp.status_code == 200:
                        return resp.json()
                except Exception:
                    pass
            return task

        return list(await asyncio.gather(*[_fetch_one(t) for t in tasks]))

    # ------------------------------------------------------------------
    # Get single task
    # ------------------------------------------------------------------

    async def get_task(self, donor_task_id: int) -> dict[str, Any] | None:
        """Fetch a single donor task. Returns None on 404 or error."""
        try:
            client = self._get_client()
            resp = await client.get(f"/api/v1/tasks/{donor_task_id}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return _map_task(resp.json())
        except Exception as exc:
            logger.warning("donor_client: get_task(%d) failed: %s", donor_task_id, exc)
            return None

    # ------------------------------------------------------------------
    # Update status
    # ------------------------------------------------------------------

    async def update_status(self, donor_task_id: int, new_gtd_status: str) -> bool:
        """Push a status change back to the donor DB. Returns True on success."""
        donor_status = GTD_TO_DONOR_STATUS.get(new_gtd_status)
        if not donor_status:
            logger.error("donor_client: unsupported GTD status '%s'", new_gtd_status)
            return False

        try:
            client = self._get_client()
            if donor_status == "completed":
                resp = await client.post(f"/api/v1/tasks/{donor_task_id}/complete")
            else:
                resp = await client.put(
                    f"/api/v1/tasks/{donor_task_id}",
                    json={"status": donor_status},
                )
            resp.raise_for_status()
            _cache.stale = True
            logger.info("donor_client: pushed status '%s' for task %d", donor_status, donor_task_id)
            return True
        except Exception as exc:
            logger.error(
                "donor_client: update_status(%d, %s) failed: %s",
                donor_task_id,
                donor_status,
                exc,
            )
            return False

    # ------------------------------------------------------------------
    # Consistency check
    # ------------------------------------------------------------------

    async def check_consistency(self) -> dict[str, Any]:
        """Compare cached tasks against a live fetch. Returns a report."""
        if _cache.stale or not _cache.tasks:
            return {
                "cache_populated": False,
                "checked_count": 0,
                "inconsistencies": [],
                "message": "Cache not yet populated; no baseline to compare.",
            }

        cached_by_id = {t["donor_task_id"]: t for t in _cache.tasks}

        try:
            client = self._get_client()
            resp = await client.get("/api/v1/tasks", params={"limit": 500})
            resp.raise_for_status()
            live_list: list[dict[str, Any]] = resp.json()
        except Exception as exc:
            logger.warning("donor_client: consistency check fetch failed: %s", exc)
            return {
                "cache_populated": True,
                "checked_count": 0,
                "inconsistencies": [],
                "error": str(exc),
            }

        inconsistencies: list[dict[str, Any]] = []

        for live in live_list:
            task_id = live["id"]
            cached = cached_by_id.get(task_id)
            live_gtd_status = DONOR_TO_GTD_STATUS.get(live.get("status", ""), "next_action")
            if cached and cached["status"] != live_gtd_status:
                entry = {
                    "donor_task_id": task_id,
                    "cached_status": cached["status"],
                    "live_status": live_gtd_status,
                }
                inconsistencies.append(entry)
                logger.warning("donor_client: consistency drift %s", entry)

        live_ids = {t["id"] for t in live_list}
        for cached_id in cached_by_id:
            if cached_id not in live_ids:
                entry = {
                    "donor_task_id": cached_id,
                    "cached_status": cached_by_id[cached_id]["status"],
                    "live_status": "missing_from_live",
                }
                inconsistencies.append(entry)
                logger.warning("donor_client: cached task %d missing from live", cached_id)

        return {
            "cache_populated": True,
            "cache_age_seconds": round(time.monotonic() - _cache.fetched_at, 1),
            "checked_count": len(live_list),
            "inconsistencies": inconsistencies,
        }


# Module-level singleton
donor_client = DonorClient()
