"""
Google Drive integration for Commander.

Provides meeting transcript fetching from Google Meet recordings.

Setup:
1. Uses the same Google Cloud project and OAuth credentials as Calendar
2. Requires the drive.readonly scope to be added
3. Users may need to re-authorize if they previously authorized without Drive scope
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid

from googleapiclient.errors import HttpError

from ...config import settings
from ..google.oauth import GoogleOAuthClient
from ..token_storage import (
    save_webhook_info,
    get_webhook_info as get_webhook_info_from_storage,
    clear_webhook_info,
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Meet Recordings folder name (Google creates this automatically)
MEET_RECORDINGS_FOLDER_NAME = "Meet Recordings"


# --------------------------------------------------------------------------- #
# Google Drive Integration Class
# --------------------------------------------------------------------------- #

class DriveIntegration(GoogleOAuthClient):
    """
    Google Drive integration for fetching meeting transcripts.
    
    Extends GoogleOAuthClient to inherit OAuth flow and credential management.
    
    Usage:
        drive = DriveIntegration(user_id="user_id")
        
        # Check if connected
        if not drive.is_connected():
            auth_url = drive.get_auth_url()
            # User visits URL and authorizes
            drive.complete_auth(authorization_code)
        
        # Get transcript content
        content = drive.get_transcript_content(file_id)
    """
    
    # Google OAuth configuration
    SERVICE_NAME = "google_drive"
    API_NAME = "drive"
    API_VERSION = "v3"
    SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    
    def __init__(self, user_id: Optional[str] = None):
        """Initialize the Drive integration for a specific user."""
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
            about = service.about().get(fields="user").execute()
            return about.get("user", {}).get("emailAddress")
        except Exception:
            return None
    
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
            channel_id = f"commander-drive-{self._user_id}-{uuid.uuid4().hex[:8]}"
            
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
            
            # Save webhook info in token data
            save_webhook_info(self._user_id, self.SERVICE_NAME, {
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

            print(f"Stopped webhook for user {self._user_id}")
            # Remove webhook info from token data
            clear_webhook_info(self._user_id, self.SERVICE_NAME)
            
            return True
        except HttpError as e:
            print(f"Error stopping webhook: {e}")
            return False
    
    def get_webhook_info(self) -> Optional[Dict[str, Any]]:
        """Get the current webhook configuration if any."""
        return get_webhook_info_from_storage(self._user_id, self.SERVICE_NAME)

    def get_drive_status(self) -> Dict[str, Any]:
        """Get the current webhook status."""
         
        # Check if webhook is still valid (compare expiration time)
        webhook_info = self.get_webhook_info()

        webhook_active = False
        webhook_expiration = None
        print(f"webhook_info: {webhook_info}")
        if webhook_info and webhook_info.get("expiration"):
            webhook_expiration = webhook_info["expiration"]

            try:
                expiration_dt = datetime.fromisoformat(webhook_expiration.replace("Z", "+00:00"))
                webhook_active = expiration_dt > datetime.now(expiration_dt.tzinfo)
            except (ValueError, TypeError):
                webhook_active = False
        
        return {
            "connected": self.is_connected(), 
            "email": self.get_user_email() if self.is_connected() else None,
            "webhook_active": webhook_active,
            "webhook_expiration": webhook_expiration,
        }

# --------------------------------------------------------------------------- #
# User-Specific Instance Helper
# --------------------------------------------------------------------------- #

def get_drive(user_id: str) -> DriveIntegration:
    """
    Get a Drive integration instance for a specific user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        DriveIntegration configured for the user
    """
    return DriveIntegration(user_id=user_id)


def get_connected_drive(user_id: str) -> Optional[DriveIntegration]:
    """
    Get a connected Drive instance for a user, or None if not connected.
    
    This is a convenience helper to avoid repetitive connection checks.
    """
    drive = get_drive(user_id)
    if not drive.is_connected():
        print("Google Drive not connected")
        return None
    return drive




