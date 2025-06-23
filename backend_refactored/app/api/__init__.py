"""
API package initialization and router configuration.
"""

from fastapi import APIRouter
from app.api.routes import (
    issues_router,
    sprints_router,
    sprints_compat_router,
    codex_router,
    health_router
)

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(issues_router)
api_router.include_router(sprints_router)
api_router.include_router(codex_router)
api_router.include_router(health_router)

# Include compatibility routes at root level (not under /api)
# api_router.include_router(sprints_compat_router)

__all__ = ["api_router"]
