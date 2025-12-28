from mcp_use.client import MCPClient
from mcp_use.agents.adapters.langchain_adapter import LangChainAdapter

mcp_configs = {
    "mcpServers": {
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat_J3"
            }
        }
    }
}

async def get_github_tools():
    """Get GitHub tools from MCP server."""
    # Initialize MCP client
    client = MCPClient.from_dict(mcp_configs)

    # Create adapter instance
    adapter = LangChainAdapter()

    # Get LangChain tools with a single line
    tools = await adapter.create_tools(client)

    # for tool in tools:
    #     print(tool.name)
    #     print(tool.description)
    #     print("".join([(k+": " + v.get("type", "") + " " + v.get("description", "") + "\n") for k, v in tool.args_schema.model_json_schema()["properties"].items()]))
    #     print("--------------------------------")

    write_tools = ["merge_pull_request", "update_issue", "create_issue", "create_branch", "create_pull_request", "create_repository"]
    read_tools = ["search_repositories", "list_issues", "list_pull_requests", "list_branches", "list_commits", "list_files"]

    read_tools = {tool.name: tool for tool in tools if tool.name in read_tools}
    write_tools = {tool.name: tool for tool in tools if tool.name in write_tools}

    return read_tools, write_tools

