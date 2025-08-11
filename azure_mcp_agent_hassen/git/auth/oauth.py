"""
GitHub OAuth Authentication

Handles GitHub OAuth flow, token management, and user authentication
for GitHub API access.
"""

import os
import webbrowser
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

from ..models import LoginResponse, AuthToken, GitHubUser

load_dotenv()

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

if not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET):
    raise RuntimeError("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set in environment variables")

# Global user storage (token -> user data)
authenticated_users: Dict[str, Dict[str, Any]] = {}


def get_github_login_url(scopes: Optional[str] = None) -> str:
    """Generate GitHub OAuth authorization URL"""
    if not scopes:
        scopes = "repo read:user"
    
    return (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&scope={scopes.replace(' ', '%20')}"
    )


def initiate_github_login(open_browser: bool = True) -> LoginResponse:
    """Initiate GitHub OAuth login process"""
    try:
        login_url = get_github_login_url()
        
        if open_browser:
            webbrowser.open_new_tab(login_url)
            message = "Browser opened for GitHub login. Please authorize the application."
        else:
            message = "Please visit the login URL to authorize the application."
        
        return LoginResponse(
            login_url=login_url,
            message=message
        )
        
    except Exception as e:
        logging.error(f"Failed to initiate GitHub login: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")


async def exchange_code_for_token(code: str) -> AuthToken:
    """Exchange OAuth code for access token"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": code
                },
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            
            access_token = data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to obtain access token")
            
            return AuthToken(
                access_token=access_token,
                token_type=data.get("token_type", "bearer"),
                scope=data.get("scope"),
                expires_in=data.get("expires_in")
            )
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error during token exchange: {e}")
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error during token exchange: {e}")
        raise HTTPException(status_code=500, detail=f"Token exchange error: {str(e)}")


async def get_authenticated_user(token: str) -> GitHubUser:
    """Get user information using access token"""
    try:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/user", headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            return GitHubUser(
                login=user_data["login"],
                id=user_data["id"],
                name=user_data.get("name"),
                email=user_data.get("email"),
                bio=user_data.get("bio"),
                avatar_url=user_data.get("avatar_url"),
                public_repos=user_data.get("public_repos", 0),
                followers=user_data.get("followers", 0),
                following=user_data.get("following", 0)
            )
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error getting user info: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        logging.error(f"Unexpected error getting user info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


def store_user_session(token: str, user: GitHubUser) -> None:
    """Store user session data"""
    authenticated_users[token] = {
        "user": user.dict(),
        "repositories": []
    }


def get_user_session(token: str) -> Optional[Dict[str, Any]]:
    """Get stored user session data"""
    return authenticated_users.get(token)


def get_all_users() -> Dict[str, Dict[str, Any]]:
    """Get all authenticated users (for debugging/admin)"""
    return authenticated_users


def revoke_user_session(token: str) -> bool:
    """Remove user session"""
    if token in authenticated_users:
        del authenticated_users[token]
        return True
    return False


async def validate_token(token: str) -> bool:
    """Validate GitHub access token"""
    try:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/user", headers=headers)
            return response.status_code == 200
            
    except Exception as e:
        logging.error(f"Token validation error: {e}")
        return False


async def refresh_user_data(token: str) -> Optional[GitHubUser]:
    """Refresh user data for existing token"""
    try:
        if await validate_token(token):
            user = await get_authenticated_user(token)
            
            # Update stored session
            if token in authenticated_users:
                authenticated_users[token]["user"] = user.dict()
            
            return user
        return None
        
    except Exception as e:
        logging.error(f"Failed to refresh user data: {e}")
        return None
