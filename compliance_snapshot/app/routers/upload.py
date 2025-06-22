from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["health"])
async def root():
    """Return a simple JSON to confirm the app is running."""
    return {"status": "alive"}
