"""
Slack MCP tools integration.

Provides Slack tools via the Model Context Protocol (MCP) server,
using OAuth tokens stored per-user for authentication.
"""
from typing import Optional

from mcp_use.client import MCPClient
from mcp_use.agents.adapters.langchain_adapter import LangChainAdapter

from .oauth import get_slack_client


class SlackMCPError(Exception):
    """Error related to Slack MCP operations."""
    pass


async def get_slack_tools(user_id: str):
    """
    Get Slack tools from MCP server for a specific user.
    
    Uses the user's stored OAuth token to authenticate with Slack.
    
    Args:
        user_id: The user's ID to fetch their Slack credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
        
    Raises:
        SlackMCPError: If user hasn't connected Slack
    """
    # Get user's Slack access token
    slack_client = get_slack_client(user_id)
    access_token = slack_client.get_access_token()
    team_id = slack_client.get_team_id()
    
    if not access_token:
        raise SlackMCPError(
            "Slack not connected. Please connect your Slack workspace in Integrations."
        )
    
    # Build MCP config with user's token
    # Note: The official MCP Slack server uses SLACK_BOT_TOKEN but works with user tokens too
    mcp_configs = {
        "mcpServers": {
            "slack": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-slack"],
                "env": {
                    "SLACK_BOT_TOKEN": access_token,
                    "SLACK_TEAM_ID": team_id or "",
                }
            }
        }
    }
    
    # Initialize MCP client
    client = MCPClient.from_dict(mcp_configs)
    
    # Create adapter instance
    adapter = LangChainAdapter()
    
    # Get LangChain tools
    tools = await adapter.create_tools(client)
    
    # Categorize tools into read and write operations
    # These are the typical tools from @modelcontextprotocol/server-slack
    write_tool_names = [
        "slack_post_message",
        "slack_reply_to_thread",
        "slack_add_reaction",
        "slack_upload_file",
    ]
    read_tool_names = [
        "slack_list_channels",
        "slack_get_channel_history",
        "slack_get_thread_replies",
        "slack_search_messages",
        "slack_get_users",
        "slack_get_user_profile",
    ]
    
    read_tools = {tool.name: tool for tool in tools if tool.name in read_tool_names}
    write_tools = {tool.name: tool for tool in tools if tool.name in write_tool_names}
    
    return read_tools, write_tools


def is_slack_connected(user_id: str) -> bool:
    """
    Check if a user has connected their Slack workspace.
    
    Args:
        user_id: The user's ID
        
    Returns:
        True if Slack is connected, False otherwise
    """
    slack_client = get_slack_client(user_id)
    return slack_client.is_connected()


def get_slack_team_name(user_id: str) -> Optional[str]:
    """
    Get the connected Slack workspace name for a user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Slack team/workspace name or None if not connected
    """
    slack_client = get_slack_client(user_id)
    return slack_client.get_team_name()

