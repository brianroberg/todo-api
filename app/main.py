from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.auth.dependencies import get_current_api_key
from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import Base, engine
from app.routers import (
    areas_router,
    dashboard_router,
    inbox_router,
    next_actions_router,
    projects_router,
    review_router,
    someday_maybe_router,
    tags_router,
    tickler_router,
)
from app.sse import router as sse_router

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="A RESTful API implementing David Allen's Getting Things Done (GTD) methodology",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(inbox_router)
app.include_router(next_actions_router)
app.include_router(someday_maybe_router)
app.include_router(projects_router)
app.include_router(tickler_router)
app.include_router(areas_router)
app.include_router(tags_router)
app.include_router(review_router)
app.include_router(sse_router)
app.include_router(dashboard_router)


@app.get("/openapi.json", include_in_schema=False)
def openapi_json(_api_key=Depends(get_current_api_key)):
    """Authenticated OpenAPI schema endpoint."""
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False)
def docs(_api_key=Depends(get_current_api_key)):
    """Authenticated Swagger UI endpoint."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False)
def redoc(_api_key=Depends(get_current_api_key)):
    """Authenticated ReDoc endpoint."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.app_name} - ReDoc",
    )


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}
