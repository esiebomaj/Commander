"""
Base class for Google OAuth integrations.

Provides common OAuth flow, credential management, and service initialization
for all Google API integrations (Gmail, Calendar, Drive, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..token_storage import (
    get_token,
    save_token,
    delete_token,
    has_token,
)


class GoogleOAuthClient(ABC):
    """
    Abstract base class for Google OAuth integrations.
    
    Provides common OAuth flow, credential management, and API service
    initialization. Subclasses must define class attributes and implement
    `get_user_email()`.
    
    Class Attributes (must be defined by subclasses):
        SERVICE_NAME: Token storage key (e.g., "gmail", "google_calendar")
        API_NAME: Google API name (e.g., "gmail", "calendar", "drive")
        API_VERSION: API version (e.g., "v1", "v3")
        SCOPES: List of OAuth scopes required
    
    Usage:
        class MyIntegration(GoogleOAuthClient):
            SERVICE_NAME = "my_service"
            API_NAME = "myapi"
            API_VERSION = "v1"
            SCOPES = ["https://www.googleapis.com/auth/myapi"]
            
            def get_user_email(self) -> Optional[str]:
                # Implementation specific to this API
                ...
    """
    
    # Subclasses must define these
    SERVICE_NAME: str
    API_NAME: str
    API_VERSION: str
    SCOPES: List[str]
    
    def __init__(self, credentials_file: Union[str, Path]):
        """
        Initialize the Google OAuth client.
        
        Args:
            credentials_file: Path to the OAuth credentials JSON file
                downloaded from Google Cloud Console.
        
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
        """Check if the integration is connected and has valid credentials."""
        if not has_token(self.SERVICE_NAME):
            return False
        
        try:
            creds = self._get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False
    
    @abstractmethod
    def get_user_email(self) -> Optional[str]:
        """
        Get the email address of the connected user.
        
        Each Google API has a different way to retrieve this,
        so subclasses must implement this method.
        
        Returns:
            Email address or None if not connected/available
        """
        pass
    
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
            scopes=self.SCOPES,
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
            save_token(self.SERVICE_NAME, {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
            })
            
            self._credentials = creds
            self._service = None  # Reset service to use new credentials
            self._flow = None
            
            return True
        except Exception as e:
            print(f"Error completing OAuth: {e}")
            return False
    
    def run_local_auth_flow(self, port: int = 8080) -> bool:
        """
        Run the complete OAuth flow locally (opens browser).
        
        This is a convenience method for command-line usage.
        
        Args:
            port: Local port for the OAuth callback
        
        Returns:
            True if authentication was successful
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._credentials_file),
                scopes=self.SCOPES,
            )
            creds = flow.run_local_server(port=port)
            
            # Save credentials
            save_token(self.SERVICE_NAME, {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
            })
            
            self._credentials = creds
            self._service = None
            
            print(f"Successfully authenticated as {self.get_user_email()}")
            return True
        except Exception as e:
            print(f"Error during OAuth flow: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect by removing stored credentials.
        
        Returns:
            True if credentials were removed
        """
        self._credentials = None
        self._service = None
        return delete_token(self.SERVICE_NAME)
    
    # ----------------------------------------------------------------------- #
    # Credentials & Service
    # ----------------------------------------------------------------------- #
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh credentials from token storage."""
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        token_data = get_token(self.SERVICE_NAME)
        if not token_data:
            return None
        
        try:
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", self.SCOPES),
            )
            
            # Refresh if expired
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token
                save_token(self.SERVICE_NAME, {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
                })
            
            self._credentials = creds
            return creds
        except Exception as e:
            print(f"Error loading credentials: {e}")
            return None
    
    def _get_service(self):
        """
        Get the Google API service, initializing if needed.
        
        Returns:
            The Google API service resource
        
        Raises:
            ValueError: If not authenticated
        """
        if self._service:
            return self._service
        
        creds = self._get_credentials()
        if not creds:
            raise ValueError(
                "Not authenticated. Call get_auth_url() and complete_auth() first."
            )
        
        self._service = build(self.API_NAME, self.API_VERSION, credentials=creds)
        return self._service
