from app.routers.areas import router as areas_router
from app.routers.dashboard import router as dashboard_router
from app.routers.donor_tasks import router as donor_tasks_router
from app.routers.inbox import router as inbox_router
from app.routers.next_actions import router as next_actions_router
from app.routers.projects import router as projects_router
from app.routers.review import router as review_router
from app.routers.someday_maybe import router as someday_maybe_router
from app.routers.tags import router as tags_router
from app.routers.tickler import router as tickler_router

__all__ = [
    "inbox_router",
    "next_actions_router",
    "someday_maybe_router",
    "projects_router",
    "tickler_router",
    "areas_router",
    "tags_router",
    "review_router",
    "dashboard_router",
    "donor_tasks_router",
]
