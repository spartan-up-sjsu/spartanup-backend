from fastapi import APIRouter, Depends
from app.routers.dependencies import get_current_user  # adjust the import path as needed

router = APIRouter()

@router.get("/")
def read_marketplace(current_user: str = Depends(get_current_user)):
    return {"message": f"Welcome to the marketplace, {current_user}"}
