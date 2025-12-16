"""
Google Calendar integration for Commander.

Provides OAuth authentication and calendar event creation for scheduling meetings.

Setup:
1. Create a Google Cloud project and enable Google Calendar API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download the credentials JSON and save as 'data/gmail_credentials.json'
4. Run the OAuth flow to authorize the application
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import traceback
from typing import Any, Dict, List, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..token_storage import (
    get_token,
    save_token,
    delete_token,
    has_token,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

from ...config import settings

DEFAULT_CREDENTIALS_FILE = settings.gmail_credentials_path

# Google Calendar API scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]


# --------------------------------------------------------------------------- #
# Google Calendar Integration Class
# --------------------------------------------------------------------------- #

class CalendarIntegration:
    """
    Google Calendar integration for creating calendar events.
    
    Usage:
        calendar = CalendarIntegration()
        
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
    
    def __init__(self, credentials_file: Union[str, Path] = DEFAULT_CREDENTIALS_FILE):
        """
        Initialize Calendar integration.
        
        Args:
            credentials_file: Path to the OAuth credentials JSON file.
        
        Raises:
            FileNotFoundError: If credentials file doesn't exist
        """
        self._credentials_file = Path(credentials_file)
        if not self._credentials_file.exists():
            raise FileNotFoundError(
                f"Google credentials file not found at {self._credentials_file}. "
                "Please download OAuth credentials from Google Cloud Console."
            )
        
        self._service = None
        self._credentials: Optional[Credentials] = None
        self._flow: Optional[InstalledAppFlow] = None
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if the Calendar integration is connected and has valid credentials."""
        if not has_token("google_calendar"):
            return False
        
        try:
            creds = self._get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False
    
    def get_user_email(self) -> Optional[str]:
        """Get the email address of the connected user."""
        if not self.is_connected():
            return None
        
        try:
            service = self._get_service()
            # Get primary calendar to find user email
            calendar = service.calendars().get(calendarId="primary").execute()
            return calendar.get("id")  # Primary calendar ID is the user's email
        except Exception:
            return None
    
    # ----------------------------------------------------------------------- #
    # OAuth Flow
    # ----------------------------------------------------------------------- #
    
    def get_auth_url(self, redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob") -> str:
        """
        Get the OAuth authorization URL for the user to visit.
        
        Args:
            redirect_uri: The redirect URI for OAuth. Use "urn:ietf:wg:oauth:2.0:oob" 
                         for copy/paste flow, or a web callback URL for web apps.
        
        Returns:
            The authorization URL for the user to visit
        """
        self._flow = InstalledAppFlow.from_client_secrets_file(
            str(self._credentials_file),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        
        auth_url, _ = self._flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        
        return auth_url
    
    def complete_auth(self, authorization_code: str) -> bool:
        """
        Complete the OAuth flow with the authorization code.
        
        Args:
            authorization_code: The code returned after user authorization
        
        Returns:
            True if authentication was successful
        """
        if self._flow is None:
            raise ValueError("Must call get_auth_url() first to start the OAuth flow")
        
        try:
            self._flow.fetch_token(code=authorization_code)
            creds = self._flow.credentials
            
            # Save credentials
            save_token("google_calendar", {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            })
            
            self._credentials = creds
            self._service = None  # Reset service to use new credentials
            self._flow = None
            
            return True
        except Exception as e:
            print(f"Error completing OAuth: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect Calendar by removing stored credentials.
        
        Returns:
            True if credentials were removed
        """
        self._credentials = None
        self._service = None
        return delete_token("google_calendar")
    
    # ----------------------------------------------------------------------- #
    # Private: Credentials & Service
    # ----------------------------------------------------------------------- #
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Calendar credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        token_data = get_token("google_calendar")
        if not token_data:
            return None
        
        try:
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", SCOPES),
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                save_token("google_calendar", {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else SCOPES,
                })
            
            self._credentials = creds
            return creds
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _get_service(self):
        """Get the Calendar API service, initializing if needed."""
        if self._service:
            return self._service
        
        creds = self._get_credentials()
        if not creds:
            raise ValueError("Not authenticated. Call run_local_auth_flow() or complete_auth() first.")
        
        self._service = build("calendar", "v3", credentials=creds)
        return self._service
    
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
# Singleton Instance
# --------------------------------------------------------------------------- #

# Global instance for easy access
_calendar_instance: Optional[CalendarIntegration] = None


def get_calendar(credentials_file: Union[str, Path] = DEFAULT_CREDENTIALS_FILE) -> CalendarIntegration:
    """
    Get the global Calendar integration instance.
    
    Args:
        credentials_file: Path to credentials file. Only used when
                         creating a new instance (first call).
                         Defaults to 'data/gmail_credentials.json'.
    """
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = CalendarIntegration(credentials_file=credentials_file)
    return _calendar_instance


def get_calendar_status() -> Dict[str, Any]:
    """Get the current Calendar connection status."""
    try:
        calendar = get_calendar()
        connected = calendar.is_connected()
        return {
            "connected": connected,
            "email": calendar.get_user_email() if connected else None,
        }
    except FileNotFoundError:
        return {"connected": False, "email": None}


def disconnect_calendar() -> bool:
    """Disconnect the Calendar integration."""
    global _calendar_instance
    if _calendar_instance:
        result = _calendar_instance.disconnect()
        _calendar_instance = None
        return result
    return delete_token("google_calendar")
