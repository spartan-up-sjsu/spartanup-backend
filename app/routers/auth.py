from fastapi import APIRouter, HTTPException
from app.core import security
from fastapi.responses import RedirectResponse
from ..config import logger, user_collection, settings
from authlib.integrations.requests_client import OAuth2Session
import traceback
from datetime import datetime
from datetime import timezone   

router = APIRouter()

GOOGLE_CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
GOOGLE_SCOPES = ['openid', 'email', 'profile']

def create_jwt_session(email: str) -> dict:
    """Create a new JWT session with both access and refresh tokens"""
    access_token = security.create_access_token(email)
    refresh_token = security.create_refresh_token(email)
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
        
        # Upsert user data
        user_collection.update_one(
            {"email": email},
            {"$set": user_data},
            upsert=True
        )

        # Create new JWT sessios
        tokens = create_jwt_session(email)




        # Redirect directly to the marketplace on successful login.
        front_end_callback_url = "http://localhost:3000/marketplace"
        response = RedirectResponse(front_end_callback_url)

    
        # Set cookies for future requests)
        response.set_cookie(
            key="access_token",
            value=tokens["access_token"],
            httponly=True,
            max_age=15 * 60,
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            samesite="lax"
        )

        return response
        

        # return {
        #     "message": "Logged in with Google successfully!",
        #     **tokens
        # }

    except Exception as e:
        logger.error(f"OAuth error: {str(e)}")
        traceback.print_exc()
        front_end_callback_url = "http://localhost:3000/callback"
        response = RedirectResponse(front_end_callback_url)
        return response
        #raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
    

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        email = security.verify_refresh_token(refresh_token)
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        # Verify user exists in database
        user = user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Create new JWT session
        return create_jwt_session(email)
        
    except Exception as e:
        logger.error(f"Refresh token error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid refresh token")
