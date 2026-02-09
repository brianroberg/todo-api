"""Server-Sent Events for push-based dashboard updates."""

import asyncio
from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.service import AuthService
from app.database import get_db

router = APIRouter(tags=["Events"])

# Active SSE connections: api_key_id -> set of asyncio.Queue
_clients: dict[int, set[asyncio.Queue]] = defaultdict(set)


def notify_change(api_key_id: int) -> None:
    """Notify all connected SSE clients for this API key that data changed."""
    for queue in list(_clients.get(api_key_id, ())):
        try:
            queue.put_nowait("event: change\ndata: refresh\n\n")
        except asyncio.QueueFull:
            pass


@router.get("/events", include_in_schema=False)
async def sse_endpoint(
    key: str = Query(..., description="API key"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """SSE stream for real-time data change notifications."""
    api_key = AuthService.verify_api_key(db, key)
    if not api_key:
        return StreamingResponse(
            iter(["event: error\ndata: unauthorized\n\n"]),
            media_type="text/event-stream",
            status_code=401,
        )

    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=16)
    api_key_id = api_key.id
    _clients[api_key_id].add(queue)

    async def stream():
        try:
            yield "event: connected\ndata: ok\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield msg
                except TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            _clients[api_key_id].discard(queue)
            if not _clients[api_key_id]:
                del _clients[api_key_id]

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
