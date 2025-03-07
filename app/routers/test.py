# from fastapi import APIRouter, Depends, HTTPException, Request
# from app.routers.dependencies import get_current_user  # Your dependency that checks the access token

# router = APIRouter()


# #Test Axios working http://localhost:8000/protected
# @router.get("/protected")
# async def protected_route(current_user: str = Depends(get_current_user)):
#     return {"message": "You have access", "user": current_user}