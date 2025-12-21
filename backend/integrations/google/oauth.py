"""
Base class for Google OAuth integrations.

Provides common OAuth flow, credential management, and service initialization
for all Google API integrations (Gmail, Calendar, Drive, etc.).
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from ...config import settings
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
    
    def __init__(self, user_id: str):
        """
        Initialize the Google OAuth client.
        
        Gets credentials from settings.google_credentials_dict.
        Credentials are validated at startup, so they're guaranteed to be available.
        
        Args:
            user_id: The user's ID. Required for per-user token operations.
        """
        if not user_id:
            raise ValueError("user_id is required")


        self._user_id = user_id
        self._credentials_dict = settings.google_credentials_dict
        
        self._service = None
        self._credentials: Optional[Credentials] = None
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if the integration is connected and has valid credentials."""
        if not has_token(self._user_id, self.SERVICE_NAME):
            print(f"[{self.SERVICE_NAME}] No token found for user {self._user_id}")
            return False
        
        try:
            creds = self._get_credentials()
            if creds is None:
                print(f"[{self.SERVICE_NAME}] Failed to get credentials")
                return False
            if not creds.valid:
                print(f"[{self.SERVICE_NAME}] Credentials not valid - expired: {creds.expired}, token exists: {creds.token is not None}")
                return False

            return True
            
        except Exception as e:
            print(f"[{self.SERVICE_NAME}] Exception checking connection: {e}")
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
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """
        Get the OAuth authorization URL for the user to visit.
        
        Args:
            redirect_uri: The redirect URI for OAuth callback.
        
        Returns:
            The authorization URL for the user to visit
        """
        flow = Flow.from_client_config(
            self._credentials_dict,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri,
        )
        
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )
        
        return auth_url
    
    def complete_auth(self, authorization_code: str, redirect_uri: str) -> bool:
        """
        Complete the OAuth flow with the authorization code.
        
        Args:
            authorization_code: The code returned after user authorization
            redirect_uri: Must match the redirect_uri used in get_auth_url()
        
        Returns:
            True if authentication was successful
        """
        try:
            # Create a new flow with the same redirect_uri to exchange the code
            flow = Flow.from_client_config(
                self._credentials_dict,
                scopes=self.SCOPES,
                redirect_uri=redirect_uri,
            )
            
            flow.fetch_token(code=authorization_code)
            creds = flow.credentials
            
            # Save credentials with expiry
            save_token(self._user_id, self.SERVICE_NAME, {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            })
            
            self._credentials = creds
            self._service = None  # Reset service to use new credentials
            
            return True
        except Exception as e:
            print(f"Error completing OAuth: {e}")
            return False
    

    def disconnect(self) -> bool:
        """
        Disconnect by removing stored credentials.
        
        Returns:
            True if credentials were removed
        """
        self._credentials = None
        self._service = None
        return delete_token(self._user_id, self.SERVICE_NAME)
    
    # ----------------------------------------------------------------------- #
    # Credentials & Service
    # ----------------------------------------------------------------------- #
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh credentials from token storage."""
        from datetime import datetime
        
        if self._credentials and self._credentials.valid:
            return self._credentials
        
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        if not token_data:
            return None
        
        try:
            # Parse expiry if present
            expiry = None
            if token_data.get("expiry"):
                expiry = datetime.fromisoformat(token_data["expiry"])
            
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", self.SCOPES),
                expiry=expiry,
            )
            
            # Refresh if expired or token is invalid
            if (creds.expired or not creds.valid) and creds.refresh_token:
                creds.refresh(Request())
                # Save refreshed token with expiry
                save_token(self._user_id, self.SERVICE_NAME, {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if creds.scopes else self.SCOPES,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None,
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
        
        return build(self.API_NAME, self.API_VERSION, credentials=creds)
