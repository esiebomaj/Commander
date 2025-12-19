"""
Google Calendar integration API routes.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


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
def calendar_status():
    """Get Google Calendar connection status."""
    try:
        from . import get_calendar_status
        status = get_calendar_status()
        return CalendarStatusResponse(**status)
    except ImportError:
        raise HTTPException(status_code=500, detail="Google Calendar integration not available")


@router.get("/auth-url", response_model=CalendarAuthUrlResponse)
def calendar_auth_url(redirect_uri: str = Query(default="urn:ietf:wg:oauth:2.0:oob")):
    """
    Get Google Calendar OAuth authorization URL.
    
    For web apps, provide your callback URL as redirect_uri.
    For CLI/desktop, use the default which shows a code to copy.
    """
    try:
        from . import get_calendar
        calendar = get_calendar()
        auth_url = calendar.get_auth_url(redirect_uri=redirect_uri)
        return CalendarAuthUrlResponse(
            auth_url=auth_url,
            instructions="Visit the URL to authorize, then call /integrations/calendar/auth?code=YOUR_CODE (GET)."
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating auth URL: {str(e)}")


@router.get("/auth", response_model=CalendarStatusResponse)
def calendar_auth(code: str = Query(..., description="Authorization code returned by Google"), state: Optional[str] = Query(default=None)):
    """
    Complete Google Calendar OAuth using query parameters from the redirect callback.
    
    Example:
    /integrations/calendar/auth?state=STATE_VALUE&code=AUTH_CODE
    """
    from . import get_calendar
    calendar = get_calendar()
    success = calendar.complete_auth(code)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to complete authentication")
    return CalendarStatusResponse(connected=True, email=calendar.get_user_email())


@router.post("/disconnect", response_model=CalendarStatusResponse)
def calendar_disconnect():
    """Disconnect Google Calendar integration."""
    try:
        from . import disconnect_calendar
        disconnect_calendar()
        return CalendarStatusResponse(connected=False, email=None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")


