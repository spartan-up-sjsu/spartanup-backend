from fastapi import APIRouter, HTTPException
from app.core import security
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse
from ..config import logger, user_collection, settings
from authlib.integrations.requests_client import OAuth2Session
import traceback
from datetime import datetime
from datetime import timezone   
from fastapi.responses import JSONResponse
from fastapi import Request


router = APIRouter()

GOOGLE_CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
GOOGLE_SCOPES = ['openid', 'email', 'profile']

def create_jwt_session(user_id: str) -> dict:
    """Create a new JWT session with both access and refresh tokens"""
    access_token = security.create_access_token(user_id)
    refresh_token = security.create_refresh_token(user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/google/login")
def google_login():
    logger.info("Google login, starting")
    client = OAuth2Session(
        settings.GOOGLE_CLIENT_ID,
        settings.GOOGLE_CLIENT_SECRET,
        scope=GOOGLE_SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )
    uri, state = client.create_authorization_url(
        'https://accounts.google.com/o/oauth2/v2/auth',
        access_type='offline'
    )
    return RedirectResponse(uri)

@router.get("/google/callback")
def google_callback(code: str = None):
    if not code:
        raise HTTPException(status_code=400, detail="No code provided by Google OAuth.")
    logger.info("Exchange code for token")
    try:
        client = OAuth2Session(
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_CLIENT_SECRET,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        token = client.fetch_token(
            'https://oauth2.googleapis.com/token',
            code=code,
            grant_type='authorization_code'
        )
        
        # Fetch user info
        resp = client.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()
        
        email = user_info.get("email")
        if not email or not email.endswith(".edu"):
            raise HTTPException(status_code=401, detail="Access denied, user not an edu email")
        
        # Store or update user in database
        user_data = {
            "email": email,
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "google_refresh_token": token.get("refresh_token"),  # Store Google's refresh token
            "last_login": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        user_record = user_collection.find_one({"email": email})
        if not user_record:
            new_user = user_data.copy()  
            new_user["_id"] = user_collection.insert_one(user_data).inserted_id 
            user_id = str(new_user["_id"])
        else:
            user_id = str(user_record["_id"])

        user_collection.update_one(
            {"email": email},
            {"$set": user_data},
            upsert=True
        )

        front_end_callback_url = "http://localhost:3000/callback"
        response = RedirectResponse(front_end_callback_url)

        tokens = create_jwt_session(user_id)

        response.set_cookie(
            key="access_token",
            value= tokens["access_token"],
            httponly=True,
            secure= False,
            max_age= 60*60*24*7,
            samesite="lax",
            domain="localhost"
        )

        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            secure=False,  
            max_age= 10 * 365 * 24 * 60 * 60, #expire in 10 years
            samesite="lax",
            domain="localhost"
        )


        return response


    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        traceback.print_exc()
        front_end_callback_url = "http://localhost:3000/callback"
        response = RedirectResponse(front_end_callback_url)
        return response


@router.post("/signout", tags=["Auth"])
async def signout():
    response = JSONResponse ({"message": "Signout Successfully"})
    response.delete_cookie("access_token", domain="localhost", path="/")
    response.delete_cookie("refresh_token", domain="localhost", path="/")
    return response 
    

@router.post("/refresh", tags=["Auth"])
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    old_access_token = request.cookies.get("access_token")
    

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        user_id = security.verify_refresh_token(refresh_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        user = user_collection.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        new_access_tokens = security.create_access_token(user_id)

        response = JSONResponse({"message": "Access token refreshed successfully"})
        response.set_cookie(
            key="access_token",
            value= new_access_tokens,
            httponly=True,
            secure= True,
            max_age= 2*10,
            samesite="none",
        )

        return response
        
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")



