# /src/api/routers/utils.py

from fastapi import APIRouter

utils_router = APIRouter(
    prefix="/utils",
    tags=["utils"]
)

@utils_router.get("/health")
def health():
    """
    Simple check to see if the API is running.
    """
    return {"status": "ok"}
