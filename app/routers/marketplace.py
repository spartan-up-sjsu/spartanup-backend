# in app/routers/marketplace.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Marketplace"])
async def get_marketplace():
    return {"message": "Marketplace data"}