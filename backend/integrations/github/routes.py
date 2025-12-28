"""
GitHub integration API routes.

Provides OAuth flow endpoints for connecting GitHub accounts.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ...auth import User, get_current_user
from .oauth import get_github_client


router = APIRouter(prefix="/integrations/github", tags=["github"])


# --------------------------------------------------------------------------- #
# Response Models
# --------------------------------------------------------------------------- #

class GitHubAuthUrlResponse(BaseModel):
    auth_url: str
    instructions: str


class GitHubStatusResponse(BaseModel):
    connected: bool
    username: Optional[str] = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=GitHubStatusResponse)
def github_status(user: User = Depends(get_current_user)):
    """Get GitHub connection status."""
    client = get_github_client(user.id)
    return GitHubStatusResponse(
        connected=client.is_connected(),
        username=client.get_username() if client.is_connected() else None,
    )


@router.get("/auth-url", response_model=GitHubAuthUrlResponse)
def github_auth_url(
    redirect_uri: str = Query(..., description="OAuth callback URL"),
    user: User = Depends(get_current_user),
):
    """
    Get GitHub OAuth authorization URL.
    
    Pass your callback URL as redirect_uri.
    """
    client = get_github_client(user.id)
    auth_url = client.get_auth_url(redirect_uri=redirect_uri)
    return GitHubAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize, then the callback will complete authentication.",
    )


@router.get("/auth", response_model=GitHubStatusResponse)
async def github_auth(
    code: str = Query(..., description="Authorization code returned by GitHub"),
    redirect_uri: str = Query(..., description="Must match the redirect_uri used in auth-url"),
    state: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    """
    Complete GitHub OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/github/auth?code=AUTH_CODE&redirect_uri=https://yourapp.com/callback
    """
    client = get_github_client(user.id)
    success = await client.complete_auth(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete GitHub authentication")
    return GitHubStatusResponse(connected=True, username=client.get_username())


@router.post("/disconnect", response_model=GitHubStatusResponse)
def github_disconnect(user: User = Depends(get_current_user)):
    """Disconnect GitHub integration."""
    client = get_github_client(user.id)
    client.disconnect()
    return GitHubStatusResponse(connected=False, username=None)

