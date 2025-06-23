"""
API routes package initialization.
"""

from .issues import router as issues_router
from .sprints import router as sprints_router, compat_router as sprints_compat_router
from .codex import router as codex_router
from .health import router as health_router

__all__ = [
    "issues_router",
    "sprints_router",
    "sprints_compat_router",
    "codex_router", 
    "health_router"
]
