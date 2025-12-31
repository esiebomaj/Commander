"""
Slack tools using native slack_sdk.

Lightweight alternative to MCP that uses direct API calls instead of
spawning Node.js processes. Much more memory efficient.

This is the default implementation used by tools.py when MCP is disabled.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ...models import ActionType
from ...user_context import get_current_user_id
from .client import get_slack
from .oauth import get_slack_client


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class SlackPostMessageInput(BaseModel):
    """Input schema for posting a message to Slack."""
    channel: str = Field(..., description="Channel ID or name (e.g., 'C1234567890' or '#general')")
    text: str = Field(..., description="The message text to send")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class SlackReplyToThreadInput(BaseModel):
    """Input schema for replying to a Slack thread."""
    channel: str = Field(..., description="Channel ID where the thread exists")
    thread_ts: str = Field(..., description="Timestamp of the parent message")
    text: str = Field(..., description="The reply text")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class SlackAddReactionInput(BaseModel):
    """Input schema for adding a reaction to a message."""
    channel: str = Field(..., description="Channel ID where the message exists")
    timestamp: str = Field(..., description="Timestamp of the message to react to")
    name: str = Field(..., description="Reaction emoji name (without colons, e.g., 'thumbsup')")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class SlackOpenDMInput(BaseModel):
    """Input schema for opening a DM conversation with a user."""
    slack_user_id: str = Field(..., description="Slack user ID to open DM with (e.g., 'U1234567890')")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class SlackListChannelsInput(BaseModel):
    """Input schema for listing Slack channels and DMs."""
    limit: int = Field(100, description="Maximum number of conversations to return")
    types: str = Field("public_channel,private_channel,im,mpim", description="Comma-separated types: public_channel, private_channel, im (DMs), mpim (group DMs)")


class SlackGetChannelHistoryInput(BaseModel):
    """Input schema for getting channel message history."""
    channel: str = Field(..., description="Channel ID to get history from")
    limit: int = Field(20, description="Maximum number of messages to return")


class SlackSearchMessagesInput(BaseModel):
    """Input schema for searching messages."""
    query: str = Field(..., description="Search query string")
    count: int = Field(20, description="Maximum number of results to return")


class SlackGetUsersInput(BaseModel):
    """Input schema for listing users."""
    limit: int = Field(100, description="Maximum number of users to return")


# --------------------------------------------------------------------------- #
# Write Tools (actions that modify state)
# --------------------------------------------------------------------------- #

@tool(args_schema=SlackPostMessageInput)
def slack_post_message(
    channel: str,
    text: str,
    **kwargs,
) -> Dict[str, Any]:
    """Post a new message to a Slack channel. Use slack_reply_to_thread for thread replies."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected. Please authenticate first."}
    
    return slack.post_message(channel=channel, text=text)


@tool(args_schema=SlackReplyToThreadInput)
def slack_reply_to_thread(
    channel: str,
    thread_ts: str,
    text: str,
    **kwargs,
) -> Dict[str, Any]:
    """Reply to a specific thread in Slack. Use for responding to existing conversations."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected. Please authenticate first."}
    
    return slack.post_message(channel=channel, text=text, thread_ts=thread_ts)


@tool(args_schema=SlackAddReactionInput)
def slack_add_reaction(
    channel: str,
    timestamp: str,
    name: str,
    **kwargs,
) -> Dict[str, Any]:
    """Add an emoji reaction to a message. Use for quick acknowledgments."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected. Please authenticate first."}
    
    return slack.add_reaction(channel=channel, timestamp=timestamp, name=name)


@tool(args_schema=SlackOpenDMInput)
def slack_open_dm(
    slack_user_id: str,
    **kwargs,
) -> Dict[str, Any]:
    """Open a direct message conversation with a user. Returns the DM channel ID for messaging."""
    current_user_id = get_current_user_id()
    slack = get_slack(current_user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected. Please authenticate first."}
    
    result = slack.open_dm(user_id=slack_user_id)
    if result.get("success"):
        result["user_id"] = slack_user_id
    return result


# --------------------------------------------------------------------------- #
# Read Tools (fetch data without modifying state)
# --------------------------------------------------------------------------- #

@tool(args_schema=SlackListChannelsInput)
def slack_list_channels(
    limit: int = 100,
    types: str = "public_channel,private_channel,im,mpim",
    **kwargs,
) -> Dict[str, Any]:
    """List Slack channels and DMs. Includes public/private channels and direct messages by default."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected."}
    
    return slack.list_channels(limit=limit, types=types)


@tool(args_schema=SlackGetChannelHistoryInput)
def slack_get_channel_history(
    channel: str,
    limit: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Get recent messages from a Slack channel or DM."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected."}
    
    return slack.get_channel_history(channel=channel, limit=limit)


@tool(args_schema=SlackSearchMessagesInput)
def slack_search_messages(
    query: str,
    count: int = 20,
    **kwargs,
) -> Dict[str, Any]:
    """Search for messages in Slack matching a query."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected."}
    
    return slack.search_messages(query=query, count=count)


@tool(args_schema=SlackGetUsersInput)
def slack_get_users(
    limit: int = 100,
    **kwargs,
) -> Dict[str, Any]:
    """List users in the Slack workspace."""
    user_id = get_current_user_id()
    slack = get_slack(user_id)
    
    if not slack.is_connected():
        return {"success": False, "error": "Slack is not connected."}
    
    return slack.list_users(limit=limit)


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

SLACK_READ_TOOLS = [
    slack_list_channels,
    slack_get_channel_history,
    slack_search_messages,
    slack_get_users,
]

SLACK_WRITE_TOOLS = [
    slack_post_message,
    slack_reply_to_thread,
    slack_add_reaction,
    slack_open_dm,
]

# --------------------------------------------------------------------------- #
# Main Interface
# --------------------------------------------------------------------------- #

async def get_slack_tools_native(user_id: str):
    """
    Get Slack tools for a specific user using native slack_sdk.
    
    This is a lightweight alternative to MCP that uses direct API calls
    instead of spawning Node.js processes.
    
    Args:
        user_id: The user's ID to fetch their Slack credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
    """
    slack_oauth = get_slack_client(user_id)
    
    if not slack_oauth.is_connected():
        return {}, {}
    
    read_tools = {tool.name: tool for tool in SLACK_READ_TOOLS}
    write_tools = {tool.name: tool for tool in SLACK_WRITE_TOOLS}
    
    return read_tools, write_tools
