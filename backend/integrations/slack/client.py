"""
Slack client for Commander.

Provides a wrapper around slack_sdk for interacting with Slack workspaces.
Handles authentication using stored OAuth tokens per user.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .oauth import get_slack_client as get_slack_oauth


class SlackClient:
    """
    Slack client for interacting with Slack workspaces.
    
    Uses the user's stored OAuth token for authentication.
    
    Usage:
        client = SlackClient(user_id="user_id")
        
        if client.is_connected():
            channels = client.list_channels()
            client.post_message(channel="C123", text="Hello!")
    """
    
    def __init__(self, user_id: str):
        """Initialize the Slack client for a specific user."""
        if not user_id:
            raise ValueError("user_id is required")
        
        self._user_id = user_id
        self._oauth = get_slack_oauth(user_id)
        self._client = None
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if Slack is connected for this user."""
        return self._oauth.is_connected()
    
    def get_team_name(self) -> Optional[str]:
        """Get the connected Slack workspace name."""
        return self._oauth.get_team_name()
    
    def get_team_id(self) -> Optional[str]:
        """Get the connected Slack team ID."""
        return self._oauth.get_team_id()
    
    # ----------------------------------------------------------------------- #
    # Internal: Get WebClient
    # ----------------------------------------------------------------------- #
    
    def _get_client(self):
        """Get the Slack WebClient, initializing if needed."""
        if self._client:
            return self._client
        
        import ssl
        import certifi
        from slack_sdk import WebClient
        
        access_token = self._oauth.get_access_token()
        if not access_token:
            raise ValueError("Slack is not connected. Please authenticate first.")
        
        # Create SSL context with certifi certificates (fixes macOS SSL issues)
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        self._client = WebClient(token=access_token, ssl=ssl_context)
        return self._client
    
    # ----------------------------------------------------------------------- #
    # Messaging
    # ----------------------------------------------------------------------- #
    
    def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post a message to a channel or DM.
        
        Args:
            channel: Channel ID (C...), DM ID (D...), or channel name (#general)
            text: Message text
            thread_ts: Optional thread timestamp to reply in a thread
        
        Returns:
            Dict with success status and result or error
        """
        try:
            client = self._get_client()
            result = client.chat_postMessage(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
            )
            return {
                "success": True,
                "channel": result["channel"],
                "ts": result["ts"],
                "message": result.get("message", {}),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_reaction(
        self,
        channel: str,
        timestamp: str,
        name: str,
    ) -> Dict[str, Any]:
        """
        Add an emoji reaction to a message.
        
        Args:
            channel: Channel ID where the message exists
            timestamp: Message timestamp
            name: Emoji name without colons (e.g., 'thumbsup')
        
        Returns:
            Dict with success status and error if any
        """
        try:
            client = self._get_client()
            client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=name,
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Direct Messages
    # ----------------------------------------------------------------------- #
    
    def open_dm(self, user_id: str) -> Dict[str, Any]:
        """
        Open a DM conversation with a user.
        
        Args:
            user_id: Slack user ID (U...)
        
        Returns:
            Dict with success status and channel info or error
        """
        try:
            client = self._get_client()
            result = client.conversations_open(users=[user_id])
            channel = result["channel"]
            return {
                "success": True,
                "channel_id": channel["id"],
                "is_im": channel.get("is_im", True),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Channels & Conversations
    # ----------------------------------------------------------------------- #
    
    def list_channels(
        self,
        limit: int = 100,
        types: str = "public_channel,private_channel,im,mpim",
    ) -> Dict[str, Any]:
        """
        List channels and DMs.
        
        Args:
            limit: Maximum number of conversations to return
            types: Comma-separated types (public_channel, private_channel, im, mpim)
        
        Returns:
            Dict with success status and channels list or error
        """
        try:
            client = self._get_client()
            result = client.conversations_list(
                limit=limit,
                types=types,
            )
            channels = []
            for ch in result.get("channels", []):
                info = {
                    "id": ch["id"],
                    "is_private": ch.get("is_private", False),
                    "is_im": ch.get("is_im", False),
                    "is_mpim": ch.get("is_mpim", False),
                }
                if ch.get("name"):
                    info["name"] = ch["name"]
                if ch.get("user"):
                    info["user"] = ch["user"]
                if ch.get("num_members"):
                    info["num_members"] = ch["num_members"]
                channels.append(info)
            return {"success": True, "channels": channels}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_channel_history(
        self,
        channel: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Get recent messages from a channel or DM.
        
        Args:
            channel: Channel or DM ID
            limit: Maximum number of messages to return
        
        Returns:
            Dict with success status and messages list or error
        """
        try:
            client = self._get_client()
            result = client.conversations_history(
                channel=channel,
                limit=limit,
            )
            messages = [
                {
                    "ts": msg["ts"],
                    "user": msg.get("user"),
                    "text": msg.get("text", ""),
                    "thread_ts": msg.get("thread_ts"),
                }
                for msg in result.get("messages", [])
            ]
            return {"success": True, "messages": messages}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Search
    # ----------------------------------------------------------------------- #
    
    def search_messages(
        self,
        query: str,
        count: int = 20,
    ) -> Dict[str, Any]:
        """
        Search for messages.
        
        Args:
            query: Search query string
            count: Maximum number of results
        
        Returns:
            Dict with success status, messages list and total count or error
        """
        try:
            client = self._get_client()
            result = client.search_messages(
                query=query,
                count=count,
            )
            matches = result.get("messages", {}).get("matches", [])
            messages = [
                {
                    "ts": msg["ts"],
                    "channel": msg.get("channel", {}).get("id"),
                    "user": msg.get("user"),
                    "text": msg.get("text", ""),
                    "permalink": msg.get("permalink"),
                }
                for msg in matches
            ]
            return {
                "success": True,
                "messages": messages,
                "total": result.get("messages", {}).get("total", 0),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Users
    # ----------------------------------------------------------------------- #
    
    def list_users(self, limit: int = 100) -> Dict[str, Any]:
        """
        List users in the workspace.
        
        Args:
            limit: Maximum number of users to return
        
        Returns:
            Dict with success status and users list or error
        """
        try:
            client = self._get_client()
            result = client.users_list(limit=limit)
            users = [
                {
                    "id": user["id"],
                    "name": user.get("name"),
                    "real_name": user.get("real_name"),
                    "email": user.get("profile", {}).get("email"),
                    "is_bot": user.get("is_bot", False),
                }
                for user in result.get("members", [])
                if not user.get("deleted", False)
            ]
            return {"success": True, "users": users}
        except Exception as e:
            return {"success": False, "error": str(e)}


# --------------------------------------------------------------------------- #
# Factory Function
# --------------------------------------------------------------------------- #

def get_slack(user_id: str) -> SlackClient:
    """
    Get a Slack client instance for a specific user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        SlackClient configured for the user
    """
    return SlackClient(user_id=user_id)

