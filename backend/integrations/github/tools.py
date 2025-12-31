"""
GitHub tools integration.

Provides GitHub tools using native PyGithub by default.
Set ENABLE_MCP_TOOLS=true to use MCP instead (spawns Node.js process).

For a lightweight implementation, see tools_native.py which uses PyGithub directly.
"""
import os
from typing import Optional

from .oauth import get_github_client


class GitHubMCPError(Exception):
    """Error related to GitHub MCP operations."""
    pass


# Check if MCP tools are enabled (disabled by default for memory)
MCP_TOOLS_ENABLED = os.getenv("ENABLE_MCP_TOOLS", "false").lower() == "true"


async def get_github_tools(user_id: str):
    """
    Get GitHub tools for a specific user.
    
    By default, uses native PyGithub (lightweight, no extra processes).
    Set ENABLE_MCP_TOOLS=true to use MCP instead (spawns Node.js process).
    
    Args:
        user_id: The user's ID to fetch their GitHub credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
    """
    # Use native PyGithub by default (lightweight)
    if not MCP_TOOLS_ENABLED:
        from .tools_native import get_github_tools_native
        return await get_github_tools_native(user_id)
    
    # MCP path (spawns Node.js process - memory intensive)
    github_client = get_github_client(user_id)
    access_token = github_client.get_access_token()
    
    if not access_token:
        return {}, {}
    
    try:
        # Lazy import to avoid loading MCP modules when disabled
        from mcp_use.client import MCPClient
        from mcp_use.agents.adapters.langchain_adapter import LangChainAdapter
        
        # Build MCP config with user's token
        mcp_configs = {
            "mcpServers": {
                "github": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {
                        "GITHUB_PERSONAL_ACCESS_TOKEN": access_token
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
            "merge_pull_request",
            "update_issue",
            "create_issue",
            "create_branch",
            "create_pull_request",
            "create_repository",
        ]
        read_tool_names = [
            "search_repositories",
            "list_issues",
            "list_pull_requests",
            "list_branches",
            "list_commits",
            "list_files",
        ]
        
        read_tools = {tool.name: tool for tool in tools if tool.name in read_tool_names}
        write_tools = {tool.name: tool for tool in tools if tool.name in write_tool_names}
        
        return read_tools, write_tools
        
    except Exception as e:
        print(f"GitHub MCP tools error: {e}")

