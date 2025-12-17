"""
Google Drive integration for Commander.

Provides OAuth authentication and meeting transcript fetching from Google Meet recordings.

Setup:
1. Uses the same Google Cloud project and OAuth credentials as Calendar
2. Requires the drive.readonly scope to be added
3. Users may need to re-authorize if they previously authorized without Drive scope
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import traceback
from typing import Any, Dict, List, Optional, Union
import uuid

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

# Google Drive API scopes
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

# Meet Recordings folder name (Google creates this automatically)
MEET_RECORDINGS_FOLDER_NAME = "Meet Recordings"


# --------------------------------------------------------------------------- #
# Google Drive Integration Class
# --------------------------------------------------------------------------- #

class DriveIntegration:
    """
    Google Drive integration for fetching meeting transcripts.
    
    Usage:
        drive = DriveIntegration()
        
        # Check if connected
        if not drive.is_connected():
            auth_url = drive.get_auth_url()
            # User visits URL and authorizes
            drive.complete_auth(authorization_code)
        
        # Get transcript content
        content = drive.get_transcript_content(file_id)
    """
    
    def __init__(self, credentials_file: Union[str, Path] = DEFAULT_CREDENTIALS_FILE):
        """
        Initialize Drive integration.
        
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
        """Check if the Drive integration is connected and has valid credentials."""
        if not has_token("google_drive"):
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
            about = service.about().get(fields="user").execute()
            return about.get("user", {}).get("emailAddress")
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
            save_token("google_drive", {
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
        Disconnect Drive by removing stored credentials.
        
        Returns:
            True if credentials were removed
        """
        self._credentials = None
        self._service = None
        return delete_token("google_drive")
    
    # ----------------------------------------------------------------------- #
    # Private: Credentials & Service
    # ----------------------------------------------------------------------- #
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh Drive credentials."""
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        token_data = get_token("google_drive")
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
                save_token("google_drive", {
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
        """Get the Drive API service, initializing if needed."""
        if self._service:
            return self._service
        
        creds = self._get_credentials()
        if not creds:
            raise ValueError("Not authenticated. Call get_auth_url() and complete_auth() first.")
        
        self._service = build("drive", "v3", credentials=creds)
        return self._service
    
    # ----------------------------------------------------------------------- #
    # Meet Recordings Folder Operations
    # ----------------------------------------------------------------------- #
    
    def find_meet_recordings_folder(self) -> Optional[Dict[str, Any]]:
        """
        Find the Meet Recordings folder in the user's Drive.
        
        Google Meet automatically creates this folder when recordings are enabled.
        
        Returns:
            Folder metadata dict or None if not found
        """
        service = self._get_service()
        
        try:
            # Search for the Meet Recordings folder
            results = service.files().list(
                q=f"name='{MEET_RECORDINGS_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces="drive",
                fields="files(id, name, createdTime)",
                pageSize=1,
            ).execute()
            
            files = results.get("files", [])
            return files[0] if files else None
            
        except HttpError as e:
            print(f"Error finding Meet Recordings folder: {e}")
            return None
    
    def list_transcript_files(
        self,
        max_results: int = 20,
        modified_after: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        List transcript files (Google Docs) in the Meet Recordings folder.
        
        Args:
            max_results: Maximum number of files to return
            modified_after: Only return files modified after this time
        
        Returns:
            List of file metadata dicts
        """
        service = self._get_service()
        
        try:
            folder = self.find_meet_recordings_folder()

            if not folder:
                print("Meet Recordings folder not found")
                return []

            folder_id = folder["id"]
 
            # Build query for Google Docs (transcripts) in the folder
            query_parts = [
                f"'{folder_id}' in parents",
                "mimeType='application/vnd.google-apps.document'",
                "trashed=false",
            ]
            
            if modified_after:
                query_parts.append(f"modifiedTime > '{modified_after.isoformat()}'")
            
            query = " and ".join(query_parts)
            
            results = service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, createdTime, modifiedTime, webViewLink)",
                pageSize=max_results,
                orderBy="modifiedTime desc",
            ).execute()
            
            return results.get("files", [])
            
        except HttpError as e:
            print(f"Error listing transcript files: {e}")
            return []
    
    # ----------------------------------------------------------------------- #
    # Transcript Content Operations
    # ----------------------------------------------------------------------- #
    
    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: The Google Drive file ID
        
        Returns:
            File metadata dict or None on error
        """
        service = self._get_service()
        
        try:
            return service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, createdTime, modifiedTime, webViewLink, parents",
            ).execute()
        except HttpError as e:
            print(f"Error getting file metadata: {e}")
            return None
    
    def get_transcript_content(self, file_id: str) -> Optional[str]:
        """
        Get the text content of a transcript (Google Doc).
        
        Args:
            file_id: The Google Drive file ID of the transcript
        
        Returns:
            Plain text content of the transcript or None on error
        """
        service = self._get_service()
        
        try:
            # Export the Google Doc as plain text
            content = service.files().export(
                fileId=file_id,
                mimeType="text/plain",
            ).execute()
            
            # Content is returned as bytes
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return content
            
        except HttpError as e:
            print(f"Error getting transcript content: {e}")
            return None
    
    # ----------------------------------------------------------------------- #
    # Webhook Operations
    # ----------------------------------------------------------------------- #
    
    def setup_webhook(
        self,
        webhook_url: str,
        folder_id: str,
        expiration_hours: int = 24 * 7,  # 1 week default
    ) -> Optional[Dict[str, Any]]:
        """
        Set up a webhook to watch for changes in the Meet Recordings folder.
        
        Args:
            webhook_url: The URL to receive push notifications
            folder_id: The folder to watch. If None, watches Meet Recordings folder.
            expiration_hours: Hours until the webhook expires (max ~1 week)
        
        Returns:
            Watch channel info or None on error
        """
        service = self._get_service()
        
        try:
            # Calculate expiration time
            expiration = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
            expiration_ms = int(expiration.timestamp() * 1000)
            
            # Create a unique channel ID
            channel_id = f"commander-drive-{uuid.uuid4().hex[:8]}"
            
            # Set up the watch
            channel = service.files().watch(
                fileId=folder_id,
                body={
                    "id": channel_id,
                    "type": "web_hook",
                    "address": webhook_url,
                    "expiration": str(expiration_ms),
                },
            ).execute()
            
            # Save webhook info for later reference
            save_token("google_drive_webhook", {
                "channel_id": channel["id"],
                "resource_id": channel.get("resourceId"),
                "folder_id": folder_id,
                "webhook_url": webhook_url,
                "expiration": expiration.isoformat(),
            })
            
            return channel
            
        except HttpError as e:
            print(f"Error setting up webhook: {e}")
            return None
    
    def stop_webhook(self, channel_id: str, resource_id: str) -> bool:
        """
        Stop a webhook channel.
        
        Args:
            channel_id: The channel ID from setup_webhook
            resource_id: The resource ID from setup_webhook
        
        Returns:
            True if stopped successfully
        """
        service = self._get_service()
        
        try:
            service.channels().stop(
                body={
                    "id": channel_id,
                    "resourceId": resource_id,
                },
            ).execute()
            
            # Remove saved webhook info
            delete_token("google_drive_webhook")
            
            return True
        except HttpError as e:
            print(f"Error stopping webhook: {e}")
            return False
    
    def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get the current webhook configuration if any."""
        return get_token("google_drive_webhook")


# --------------------------------------------------------------------------- #
# Singleton Instance
# --------------------------------------------------------------------------- #

# Global instance for easy access
_drive_instance: Optional[DriveIntegration] = None


def get_drive(credentials_file: Union[str, Path] = DEFAULT_CREDENTIALS_FILE) -> DriveIntegration:
    """
    Get the global Drive integration instance.
    
    Args:
        credentials_file: Path to credentials file. Only used when
                         creating a new instance (first call).
                         Defaults to 'data/gmail_credentials.json'.
    """
    global _drive_instance
    if _drive_instance is None:
        _drive_instance = DriveIntegration(credentials_file=credentials_file)
    return _drive_instance


def get_connected_drive() -> Optional[DriveIntegration]:
    """
    Get a connected Drive instance, or None if not connected.
    
    This is a convenience helper to avoid repetitive connection checks.
    """
    try:
        drive = get_drive()
        if not drive.is_connected():
            print("Google Drive not connected")
            return None
        return drive
    except FileNotFoundError as e:
        print(f"Drive credentials not found: {e}")
        return None


def get_drive_status() -> Dict[str, Any]:
    """Get the current Drive connection status."""
    try:
        drive = get_drive()
        connected = drive.is_connected()
        webhook_info = drive.get_webhook_info()
        
        return {
            "connected": connected,
            "email": drive.get_user_email() if connected else None,
            "webhook_active": webhook_info is not None,
            "webhook_expiration": webhook_info.get("expiration") if webhook_info else None,
        }
    except FileNotFoundError:
        return {
            "connected": False,
            "email": None,
            "webhook_active": False,
            "webhook_expiration": None,
        }


def disconnect_drive() -> bool:
    """Disconnect the Drive integration."""
    global _drive_instance
    if _drive_instance:
        result = _drive_instance.disconnect()
        _drive_instance = None
        return result
    return delete_token("google_drive")

