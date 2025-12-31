"""
Slack MCP tools integration.

Provides Slack tools via the Model Context Protocol (MCP) server,
using OAuth tokens stored per-user for authentication.

NOTE: MCP tools are disabled by default to avoid spawning Node.js processes
on every request, which causes severe memory issues on constrained servers.
Enable with ENABLE_MCP_TOOLS=true environment variable.

For a lightweight alternative, see tools_native.py which uses slack_sdk directly.
"""
import os
from typing import Optional

from .oauth import get_slack_client


class SlackMCPError(Exception):
    """Error related to Slack MCP operations."""
    pass


# Check if MCP tools are enabled (disabled by default for memory)
MCP_TOOLS_ENABLED = os.getenv("ENABLE_MCP_TOOLS", "false").lower() == "true"


async def get_slack_tools(user_id: str):
    """
    Get Slack tools for a specific user.
    
    By default, uses native slack_sdk (lightweight, no extra processes).
    Set ENABLE_MCP_TOOLS=true to use MCP instead (spawns Node.js process).
    
    Args:
        user_id: The user's ID to fetch their Slack credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
    """
    # Use native SDK by default (lightweight)
    if not MCP_TOOLS_ENABLED:
        from .tools_native import get_slack_tools_native
        return await get_slack_tools_native(user_id)
    
    # MCP path (spawns Node.js process - memory intensive)
    slack_client = get_slack_client(user_id)
    access_token = slack_client.get_access_token()
    team_id = slack_client.get_team_id()
    
    if not access_token:
        return {}, {}
    
    # Lazy import to avoid loading MCP modules when disabled
    from mcp_use.client import MCPClient
    from mcp_use.agents.adapters.langchain_adapter import LangChainAdapter
    
    # Build MCP config with user's token
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
