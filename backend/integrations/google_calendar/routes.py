"""
Google Calendar integration API routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from ...auth import User, get_current_user


router = APIRouter(prefix="/integrations/calendar", tags=["calendar"])


# --------------------------------------------------------------------------- #
# Response Models
# --------------------------------------------------------------------------- #

class CalendarAuthUrlResponse(BaseModel):
    auth_url: str
    instructions: str


class CalendarStatusResponse(BaseModel):
    connected: bool
    email: Optional[str] = None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #

@router.get("/status", response_model=CalendarStatusResponse)
def calendar_status(user: User = Depends(get_current_user)):
    """Get Google Calendar connection status."""
    from .client import get_calendar

    calendar = get_calendar(user.id)
    return CalendarStatusResponse(
        connected=calendar.is_connected(), 
        email=calendar.get_user_email() if calendar.is_connected() else None
    )


@router.get("/auth-url", response_model=CalendarAuthUrlResponse)
def calendar_auth_url(
    redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob"),
    user: User = Depends(get_current_user),
):
    """
    Get Google Calendar OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    from .client import get_calendar
    calendar = get_calendar(user.id)
    auth_url = calendar.get_auth_url(redirect_uri=redirect_uri)
    return CalendarAuthUrlResponse(
        auth_url=auth_url,
        instructions="Visit the URL to authorize, then call /integrations/calendar/auth?code=YOUR_CODE (GET)."
    )


@router.get("/auth", response_model=CalendarStatusResponse)
def calendar_auth(
    code: str = Query(..., description="Authorization code returned by Google"),
    redirect_uri: str = Query(..., description="Must match the redirect_uri used in auth-url"),
    state: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
):
    """
    Complete Google Calendar OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/calendar/auth?code=AUTH_CODE&redirect_uri=https://yourapp.com/callback
    """
    from .client import get_calendar
    calendar = get_calendar(user.id)
    success = calendar.complete_auth(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    return CalendarStatusResponse(connected=True, email=calendar.get_user_email())


@router.post("/disconnect", response_model=CalendarStatusResponse)
def calendar_disconnect(user: User = Depends(get_current_user)):
    """Disconnect Google Calendar integration."""
    from .client import get_calendar
    calendar = get_calendar(user.id)
    calendar.disconnect()
    return CalendarStatusResponse(connected=False, email=None)
