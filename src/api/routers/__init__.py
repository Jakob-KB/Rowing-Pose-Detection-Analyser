# /src/api/routers/__init__.py

from fastapi import APIRouter

from .utils import utils_router
from .sessions import sessions_router

# Create a primary API router
router = APIRouter()


# Mount each sub-router under its own path segment
router.include_router(utils_router)
router.include_router(sessions_router)
