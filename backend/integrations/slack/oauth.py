"""
Slack OAuth client for MCP integration.

Provides OAuth 2.0 authentication flow for Slack, storing user tokens
per-user in the database for use with the Slack MCP server.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

import httpx

from ..token_storage import get_token, save_token, delete_token, has_token
from ...config import settings


class SlackOAuthClient:
    """
    Slack OAuth client following the same pattern as GitHubOAuthClient.
    
    Handles the OAuth flow for Slack and stores user tokens per-user.
    The stored access_token can be used with the Slack MCP server.
    
    Note: This uses USER tokens (xoxp-) not BOT tokens (xoxb-) so that
    actions are performed as the authenticated user.
    """
    
    SERVICE_NAME = "slack"
    
    # User token scopes for full MCP functionality
    # These are "User Token Scopes" in Slack App settings
    DEFAULT_SCOPES = [
        # Channel access
        "channels:read",          # View basic channel info
        "channels:history",       # View messages in public channels
        "groups:read",            # View private channels
        "groups:history",         # View messages in private channels
        "im:read",                # View direct messages
        "im:history",             # View DM history
        "mpim:read",              # View group DMs
        "mpim:history",           # View group DM history
        
        # Messaging
        "chat:write",             # Send messages as user
        
        # Users
        "users:read",             # View users
        "users:read.email",       # View user email addresses
        
        # Files
        "files:read",             # View files
        "files:write",            # Upload/edit files
        
        # Reactions
        "reactions:read",         # View reactions
        "reactions:write",        # Add/remove reactions
        
        # Search
        "search:read",            # Search messages and files
    ]
    
    AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
    TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    API_BASE = "https://slack.com/api"
    
    def __init__(self, user_id: str, scopes: Optional[list[str]] = None):
        """
        Initialize the Slack OAuth client.
        
        Args:
            user_id: The user's ID
            scopes: Optional list of OAuth scopes. Defaults to DEFAULT_SCOPES.
        """
        if not user_id:
            raise ValueError("user_id is required")
        
        self._user_id = user_id
        self._client_id = settings.slack_client_id
        self._client_secret = settings.slack_client_secret
        self._scopes = scopes or self.DEFAULT_SCOPES
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if Slack is connected for this user."""
        if not has_token(self._user_id, self.SERVICE_NAME):
            return False
        
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        return token_data is not None and "access_token" in token_data
    
    def get_team_name(self) -> Optional[str]:
        """Get the connected Slack workspace/team name."""
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        if token_data:
            return token_data.get("team_name")
        return None
    
    def get_team_id(self) -> Optional[str]:
        """Get the connected Slack team ID."""
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        if token_data:
            return token_data.get("team_id")
        return None
    
    # ----------------------------------------------------------------------- #
    # OAuth Flow
    # ----------------------------------------------------------------------- #
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """
        Get Slack OAuth authorization URL.
        
        Args:
            redirect_uri: The redirect URI for OAuth callback.
        
        Returns:
            The authorization URL for the user to visit
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            # Use user_scope for USER tokens (not scope which is for bot tokens)
            "user_scope": " ".join(self._scopes),
            "state": self._user_id,
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
    async def complete_auth(self, code: str, redirect_uri: str) -> bool:
        """
        Exchange authorization code for access token.
        
        Args:
            code: The authorization code from Slack
            redirect_uri: Must match the redirect_uri used in get_auth_url()
        
        Returns:
            True if authentication was successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get("ok"):
                    print(f"Slack OAuth error: {data.get('error')}")
                    return False
                
                # For user tokens, access_token is in authed_user
                authed_user = data.get("authed_user", {})
                access_token = authed_user.get("access_token")
                
                if not access_token:
                    print(f"No user access_token in response: {data}")
                    return False
                
                # Get team info
                team = data.get("team", {})
                
                # Save token with metadata
                save_token(self._user_id, self.SERVICE_NAME, {
                    "access_token": access_token,
                    "token_type": authed_user.get("token_type", "user"),
                    "scope": authed_user.get("scope", ""),
                    "slack_user_id": authed_user.get("id"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                })
                return True
                
        except httpx.HTTPError as e:
            print(f"HTTP error during Slack OAuth: {e}")
            return False
        except Exception as e:
            print(f"Error completing Slack OAuth: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Remove stored credentials.
        
        Returns:
            True if credentials were removed
        """
        return delete_token(self._user_id, self.SERVICE_NAME)
    
    # ----------------------------------------------------------------------- #
    # Token Access (for MCP)
    # ----------------------------------------------------------------------- #
    
    def get_access_token(self) -> Optional[str]:
        """
        Get stored access token for MCP use.
        
        Returns:
            The access token or None if not connected
        """
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        if token_data:
            return token_data.get("access_token")
        return None


def get_slack_client(user_id: str) -> SlackOAuthClient:
    """Factory function to get a Slack OAuth client for a user."""
    return SlackOAuthClient(user_id)

