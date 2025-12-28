"""
Slack integration API routes.

Provides OAuth flow endpoints for connecting Slack workspaces.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ...auth import User, get_current_user
from .oauth import get_slack_client


router = APIRouter(prefix="/integrations/slack", tags=["slack"])


# --------------------------------------------------------------------------- #
# Response Models
# --------------------------------------------------------------------------- #

class SlackAuthUrlResponse(BaseModel):
    auth_url: str
    instructions: str


class SlackStatusResponse(BaseModel):
    connected: bool
    team_name: Optional[str] = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=SlackStatusResponse)
def slack_status(user: User = Depends(get_current_user)):
    """Get Slack connection status."""
    client = get_slack_client(user.id)
    return SlackStatusResponse(
        connected=client.is_connected(),
        team_name=client.get_team_name() if client.is_connected() else None,
    )


@router.get("/auth-url", response_model=SlackAuthUrlResponse)
def slack_auth_url(
    redirect_uri: str = Query(..., description="OAuth callback URL"),
    user: User = Depends(get_current_user),
):
    """
    Get Slack OAuth authorization URL.
    
    Pass your callback URL as redirect_uri.
    """
    client = get_slack_client(user.id)
    auth_url = client.get_auth_url(redirect_uri=redirect_uri)
    return SlackAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize Commander to access your Slack workspace.",
    )


@router.get("/auth", response_model=SlackStatusResponse)
async def slack_auth(
    code: str = Query(..., description="Authorization code returned by Slack"),
    redirect_uri: str = Query(..., description="Must match the redirect_uri used in auth-url"),
    state: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    """
    Complete Slack OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/slack/auth?code=AUTH_CODE&redirect_uri=https://yourapp.com/callback
    """
    client = get_slack_client(user.id)
    success = await client.complete_auth(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete Slack authentication")
    return SlackStatusResponse(connected=True, team_name=client.get_team_name())


@router.post("/disconnect", response_model=SlackStatusResponse)
def slack_disconnect(user: User = Depends(get_current_user)):
    """Disconnect Slack integration."""
    client = get_slack_client(user.id)
    client.disconnect()
    return SlackStatusResponse(connected=False, team_name=None)

