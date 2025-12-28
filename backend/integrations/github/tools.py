"""
GitHub MCP tools integration.

Provides GitHub tools via the Model Context Protocol (MCP) server,
using OAuth tokens stored per-user for authentication.
"""
from mcp_use.client import MCPClient
from mcp_use.agents.adapters.langchain_adapter import LangChainAdapter

from .oauth import get_github_client


class GitHubMCPError(Exception):
    """Error related to GitHub MCP operations."""
    pass


async def get_github_tools(user_id: str):
    """
    Get GitHub tools from MCP server for a specific user.
    
    Uses the user's stored OAuth token to authenticate with GitHub.
    
    Args:
        user_id: The user's ID to fetch their GitHub credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
        
    Raises:
        GitHubMCPError: If user hasn't connected GitHub
    """
    # Get user's GitHub access token
    github_client = get_github_client(user_id)
    access_token = github_client.get_access_token()
    
    if not access_token:
        raise GitHubMCPError(
            "GitHub not connected. Please connect your GitHub account in Integrations."
        )
    
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

