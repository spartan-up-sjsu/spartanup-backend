from fastapi import APIRouter, Depends, HTTPException
from ..config import settings
from ..schemas.user_schema import UserLogin
from ..core import security
from urllib.parse import urlencode
from fastapi.responses import RedirectResponse
import traceback
import requests
import json


router = APIRouter()



@router.get("/google/login")
def google_login():

    google_auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "access_type": "offline",  
        "prompt": "consent",      
    }
    auth_url = f"{google_auth_endpoint}?{urlencode(params)}"
    return RedirectResponse(auth_url)

@router.get("/google/callback")

def google_callback(code: str = None):
    if not code:
        raise HTTPException(status_code=400, detail="No code provided by Google OAuth.")
    
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    
    try:
        token_response = requests.post(token_url, data=token_data)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal error during token exchange: {e}")
    
    # print("Token response status:", token_response.status_code)
    # print("Token response body:", token_response.text)
    
    if not token_response.ok:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange code for token: {token_response.text}"
        )
    
    tokens = token_response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token not found in response.")
    
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_info_response = requests.get(user_info_url, headers=headers)
    
    # print("User info response status:", user_info_response.status_code)
    # print("User info response body:", user_info_response.text)
    
    if not user_info_response.ok:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch user info from Google: {user_info_response.text}"
        )


    user_info = user_info_response.json()

    email = user_info.get("email")
    if not email.endswith(".edu"):
        raise HTTPException(status_code=403, detail = "Access denied, not an edu email")
    

    try:
        with open("user_info.json","w") as f:
            json.dump(user_info, f, indent = 4)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error saving userinfo")

    jwt_token = security.create_access_token(user_info["email"])
    return {
        "message": "Logged in with Google successfully!",
    }

