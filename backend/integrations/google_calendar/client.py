"""
Google Calendar integration for Commander.

Provides calendar event creation and listing for scheduling meetings.

Setup:
1. Create a Google Cloud project and enable Google Calendar API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download the credentials JSON and save as 'data/gmail_credentials.json'
4. Run the OAuth flow to authorize the application
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from googleapiclient.errors import HttpError

from ...config import settings
from ..google.oauth import GoogleOAuthClient
from ..token_storage import delete_token


# --------------------------------------------------------------------------- #
# Google Calendar Integration Class
# --------------------------------------------------------------------------- #

class CalendarIntegration(GoogleOAuthClient):
    """
    Google Calendar integration for creating calendar events.
    
    Extends GoogleOAuthClient to inherit OAuth flow and credential management.
    
    Usage:
        calendar = CalendarIntegration(user_id="user_id")
        
        # Check if connected
        if not calendar.is_connected():
            auth_url = calendar.get_auth_url()
            # User visits URL and authorizes
            calendar.complete_auth(authorization_code)
        
        # Create a meeting
        calendar.create_event(
            title="Team Meeting",
            description="Weekly sync",
            start_time="2025-12-20T10:00:00",
            duration_mins=30,
            attendees=["user@example.com"]
        )
    """
    
    # Google OAuth configuration
    SERVICE_NAME = "google_calendar"
    API_NAME = "calendar"
    API_VERSION = "v3"
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize the Calendar integration for a specific user."""
        super().__init__(user_id=user_id)
    
    # ----------------------------------------------------------------------- #
    # User Info (required by base class)
    # ----------------------------------------------------------------------- #
    
    def get_user_email(self) -> Optional[str]:
        """Get the email address of the connected user."""
        if not self.is_connected():
            return None
        
        try:
            service = self._get_service()
            # Get primary calendar to find user email
            calendar = service.calendars().get(calendarId="primary").execute()
            return calendar.get("id")  # Primary calendar ID is the user's email
        except Exception as e:
            print(f"Error getting user email: {e}")
            return None
    
    # ----------------------------------------------------------------------- #
    # Calendar Event Operations
    # ----------------------------------------------------------------------- #
    
    def create_event(
        self,
        title: str,
        description: str,
        start_time: str,
        duration_mins: int = 30,
        attendees: Optional[List[str]] = None,
        timezone_str: str = "UTC",
    ) -> Optional[Dict[str, Any]]:
        """
        Create a calendar event.
        
        Args:
            title: Event title/summary
            description: Event description
            start_time: Start time in ISO format (e.g., "2025-12-20T10:00:00")
            duration_mins: Duration in minutes (default: 30)
            attendees: Optional list of attendee email addresses
            timezone_str: Timezone for the event (default: "UTC")
        
        Returns:
            Created event data or None on error
        """
        service = self._get_service()
        
        try:
            # Parse start time
            if start_time.endswith("Z"):
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            elif "+" in start_time or start_time.count("-") > 2:
                # Already has timezone info
                start_dt = datetime.fromisoformat(start_time)
            else:
                # No timezone info, assume local/provided timezone
                start_dt = datetime.fromisoformat(start_time)
            
            end_dt = start_dt + timedelta(minutes=duration_mins)
            
            # Build event body
            event_body: Dict[str, Any] = {
                "summary": title,
                "description": description,
                "start": {
                    "dateTime": start_dt.isoformat(),
                    "timeZone": timezone_str,
                },
                "end": {
                    "dateTime": end_dt.isoformat(),
                    "timeZone": timezone_str,
                },
            }
            
            # Add attendees if provided
            if attendees:
                event_body["attendees"] = [{"email": email} for email in attendees]
                # Send email notifications to attendees
                event_body["sendUpdates"] = "all"
            
            # Create the event
            event = service.events().insert(
                calendarId="primary",
                body=event_body,
                sendUpdates="all" if attendees else "none",
            ).execute()
            
            return event
            
        except HttpError as e:
            print(f"Error creating calendar event: {e}")
            return None
        except ValueError as e:
            print(f"Error parsing date/time: {e}")
            return None
    
    def list_upcoming_events(
        self,
        max_results: int = 10,
        time_min: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        List upcoming calendar events.
        
        Args:
            max_results: Maximum number of events to return
            time_min: Minimum start time (default: now)
        
        Returns:
            List of event dictionaries
        """
        service = self._get_service()
        
        try:
            if time_min is None:
                time_min = datetime.now(timezone.utc)
            
            events_result = service.events().list(
                calendarId="primary",
                timeMin=time_min.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            return events_result.get("items", [])
            
        except HttpError as e:
            print(f"Error listing events: {e}")
            return []


# --------------------------------------------------------------------------- #
# User-Specific Instance Helper
# --------------------------------------------------------------------------- #

def get_calendar(user_id: str) -> CalendarIntegration:
    """
    Get a Calendar integration instance for a specific user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        CalendarIntegration configured for the user
    """
    return CalendarIntegration(user_id=user_id)




