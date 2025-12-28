"""
GitHub OAuth client for MCP integration.

Provides OAuth 2.0 authentication flow for GitHub, storing tokens
per-user in the database for use with the GitHub MCP server.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

import httpx

from ..token_storage import get_token, save_token, delete_token, has_token
from ...config import settings


class GitHubOAuthClient:
    """
    GitHub OAuth client following the same pattern as GoogleOAuthClient.
    
    Handles the OAuth flow for GitHub and stores tokens per-user.
    The stored access_token can be used with the GitHub MCP server.
    """
    
    SERVICE_NAME = "github"
    # Default scopes - can be customized per use case
    # GitHub OAuth scopes required for all key MCP use cases (read and write repos/issues, workflow status, org info, etc.)
    DEFAULT_SCOPES = [
        # Write access tokens
        "repo",             # Full control of private repositories (includes write)
        "repo:status",      # Access commit statuses (write tool: merge_pull_request)
        "repo_deployment",  # Deployment status (not mapped directly but write action)
        "repo:invite",      # Accept repo invitations (write action)
        "public_repo",      # Access to public repositories (for writeable actions)
        "write:org",        # Modify orgs (write, e.g., create repo/branch in org context)
        "admin:repo_hook",  # Full control of repository hooks (may be needed for write tools)
        "admin:org_hook",   # Full control of org hooks
        "gist",             # Create gists (write)
        "workflow",         # Update GitHub Actions workflows (write)
        "write:discussion", # Write org/team discussions

        # Read access tokens
        "read:org",             # Read org membership, team, and projects (read_tools: list_issues, etc.)
        "read:public_key",      # List user's public SSH keys (read)
        "user",                 # Full control of user data (read)
        "notifications",        # Access notifications (read)
        "read:discussion",      # Read org/team discussions
        "codespace",            # Codespaces access (read, if browse files)
        "read:public_key",      # List user's public SSH keys (read)
    ]
    
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_BASE = "https://api.github.com"
    
    def __init__(self, user_id: str, scopes: Optional[list[str]] = None):
        """
        Initialize the GitHub OAuth client.
        
        Args:
            user_id: The user's ID
            scopes: Optional list of OAuth scopes. Defaults to DEFAULT_SCOPES.
        """
        if not user_id:
            raise ValueError("user_id is required")
        
        self._user_id = user_id
        self._client_id = settings.github_client_id
        self._client_secret = settings.github_client_secret
        self._scopes = scopes or self.DEFAULT_SCOPES
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if GitHub is connected for this user."""
        if not has_token(self._user_id, self.SERVICE_NAME):
            return False
        
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        return token_data is not None and "access_token" in token_data
    
    def get_username(self) -> Optional[str]:
        """Get the connected GitHub username."""
        token_data = get_token(self._user_id, self.SERVICE_NAME)
        if token_data:
            return token_data.get("username")
        return None
    
    # ----------------------------------------------------------------------- #
    # OAuth Flow
    # ----------------------------------------------------------------------- #
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """
        Get GitHub OAuth authorization URL.
        
        Args:
            redirect_uri: The redirect URI for OAuth callback.
        
        Returns:
            The authorization URL for the user to visit
        """
        params = {
            "client_id": self._client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self._scopes),
            "state": self._user_id,  # Use state for CSRF protection
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"
    
    async def complete_auth(self, code: str, redirect_uri: str) -> bool:
        """
        Exchange authorization code for access token.
        
        Args:
            code: The authorization code from GitHub
            redirect_uri: Must match the redirect_uri used in get_auth_url()
        
        Returns:
            True if authentication was successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Exchange code for token
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                token_data = response.json()

                if "error" in token_data:
                    print(f"GitHub OAuth error: {token_data}")
                    return False
                
                access_token = token_data.get("access_token")
                if not access_token:
                    print(f"No access_token in response: {token_data}")
                    return False
                
                # Fetch user info to get username
                user_response = await client.get(
                    f"{self.API_BASE}/user",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github+json",
                    },
                )

                user_response.raise_for_status()
                user_info = user_response.json()

                # Save the token with user info
                save_token(self._user_id, self.SERVICE_NAME, {
                    "access_token": access_token,
                    "token_type": token_data.get("token_type", "bearer"),
                    "scope": token_data.get("scope", ""),
                    "username": user_info.get("login"),
                    "github_user_id": user_info.get("id"),
                    "avatar_url": user_info.get("avatar_url"),
                })
                return True
                
        except httpx.HTTPError as e:
            print(f"HTTP error during GitHub OAuth: {e}")
            return False
        except Exception as e:
            print(f"Error completing GitHub OAuth: {e}")
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


def get_github_client(user_id: str) -> GitHubOAuthClient:
    """Factory function to get a GitHub OAuth client for a user."""
    return GitHubOAuthClient(user_id)

