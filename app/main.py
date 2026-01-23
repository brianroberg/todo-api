from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.config import get_settings
from app.database import Base, engine
from app.routers import (
    areas_router,
    inbox_router,
    next_actions_router,
    projects_router,
    review_router,
    someday_maybe_router,
    tags_router,
    tickler_router,
)

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="A RESTful API implementing David Allen's Getting Things Done (GTD) methodology",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy"}
