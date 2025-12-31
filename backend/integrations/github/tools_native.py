"""
GitHub tools using native PyGithub.

Lightweight alternative to MCP that uses direct API calls instead of
spawning Node.js processes. Much more memory efficient.

This is the default implementation used by tools.py.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ...models import ActionType
from ...user_context import get_current_user_id
from .client import get_github
from .oauth import get_github_client


# --------------------------------------------------------------------------- #
# Tool Input Schemas
# --------------------------------------------------------------------------- #

class GitHubSearchReposInput(BaseModel):
    """Input schema for searching repositories."""
    query: str = Field(..., description="Search query string")
    limit: int = Field(10, description="Maximum number of results to return")


class GitHubListIssuesInput(BaseModel):
    """Input schema for listing issues."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    state: str = Field("open", description="Issue state: 'open', 'closed', or 'all'")
    limit: int = Field(30, description="Maximum number of issues to return")


class GitHubCreateIssueInput(BaseModel):
    """Input schema for creating an issue."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    title: str = Field(..., description="Issue title")
    body: Optional[str] = Field(None, description="Issue body/description")
    labels: Optional[List[str]] = Field(None, description="List of label names")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class GitHubUpdateIssueInput(BaseModel):
    """Input schema for updating an issue."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    issue_number: int = Field(..., description="Issue number")
    title: Optional[str] = Field(None, description="New title")
    body: Optional[str] = Field(None, description="New body")
    state: Optional[str] = Field(None, description="New state: 'open' or 'closed'")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class GitHubListPRsInput(BaseModel):
    """Input schema for listing pull requests."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    state: str = Field("open", description="PR state: 'open', 'closed', or 'all'")
    limit: int = Field(30, description="Maximum number of PRs to return")


class GitHubCreatePRInput(BaseModel):
    """Input schema for creating a pull request."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    title: str = Field(..., description="PR title")
    head: str = Field(..., description="Head branch name (the branch with changes)")
    base: str = Field(..., description="Base branch name (the branch to merge into)")
    body: Optional[str] = Field(None, description="PR body/description")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class GitHubMergePRInput(BaseModel):
    """Input schema for merging a pull request."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    pull_number: int = Field(..., description="PR number")
    merge_method: str = Field("merge", description="Merge method: 'merge', 'squash', or 'rebase'")
    commit_message: Optional[str] = Field(None, description="Custom commit message")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class GitHubListBranchesInput(BaseModel):
    """Input schema for listing branches."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    limit: int = Field(30, description="Maximum number of branches to return")


class GitHubCreateBranchInput(BaseModel):
    """Input schema for creating a branch."""
    owner: str = Field(..., description="Repository owner (username or org)")
    repo: str = Field(..., description="Repository name")
    branch_name: str = Field(..., description="Name for the new branch")
    source_branch: Optional[str] = Field(None, description="Branch to create from (default: repo's default branch)")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


class GitHubCreateRepoInput(BaseModel):
    """Input schema for creating a repository."""
    name: str = Field(..., description="Repository name (e.g., 'my-project')")
    description: Optional[str] = Field(None, description="Repository description")
    private: bool = Field(False, description="Whether the repository should be private")
    auto_init: bool = Field(True, description="Initialize with a README file")
    confidence: float = Field(0.7, ge=0, le=1, description="Model confidence in this action")


# --------------------------------------------------------------------------- #
# Read Tools
# --------------------------------------------------------------------------- #

@tool(args_schema=GitHubSearchReposInput)
def search_repositories(
    query: str,
    limit: int = 10,
    **kwargs,
) -> Dict[str, Any]:
    """Search for GitHub repositories matching a query."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.search_repositories(query=query, limit=limit)


@tool(args_schema=GitHubListIssuesInput)
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 30,
    **kwargs,
) -> Dict[str, Any]:
    """List issues for a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.list_issues(owner=owner, repo=repo, state=state, limit=limit)


@tool(args_schema=GitHubListPRsInput)
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 30,
    **kwargs,
) -> Dict[str, Any]:
    """List pull requests for a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.list_pull_requests(owner=owner, repo=repo, state=state, limit=limit)


@tool(args_schema=GitHubListBranchesInput)
def list_branches(
    owner: str,
    repo: str,
    limit: int = 30,
    **kwargs,
) -> Dict[str, Any]:
    """List branches for a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.list_branches(owner=owner, repo=repo, limit=limit)


# --------------------------------------------------------------------------- #
# Write Tools
# --------------------------------------------------------------------------- #

@tool(args_schema=GitHubCreateIssueInput)
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: Optional[str] = None,
    labels: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new issue in a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.create_issue(owner=owner, repo=repo, title=title, body=body, labels=labels)


@tool(args_schema=GitHubUpdateIssueInput)
def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: Optional[str] = None,
    body: Optional[str] = None,
    state: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update an existing issue in a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.update_issue(
        owner=owner, repo=repo, issue_number=issue_number,
        title=title, body=body, state=state,
    )


@tool(args_schema=GitHubCreatePRInput)
def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new pull request in a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.create_pull_request(
        owner=owner, repo=repo, title=title, head=head, base=base, body=body,
    )


@tool(args_schema=GitHubMergePRInput)
def merge_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    merge_method: str = "merge",
    commit_message: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Merge a pull request in a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.merge_pull_request(
        owner=owner, repo=repo, pull_number=pull_number,
        merge_method=merge_method, commit_message=commit_message,
    )


@tool(args_schema=GitHubCreateBranchInput)
def create_branch(
    owner: str,
    repo: str,
    branch_name: str,
    source_branch: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new branch in a GitHub repository."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.create_branch(
        owner=owner, repo=repo, branch_name=branch_name, source_branch=source_branch,
    )


@tool(args_schema=GitHubCreateRepoInput)
def create_repository(
    name: str,
    description: Optional[str] = None,
    private: bool = False,
    auto_init: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Create a new GitHub repository for the authenticated user."""
    user_id = get_current_user_id()
    github = get_github(user_id)
    
    if not github.is_connected():
        return {"success": False, "error": "GitHub is not connected. Please authenticate first."}
    
    return github.create_repository(
        name=name, description=description, private=private, auto_init=auto_init,
    )


# --------------------------------------------------------------------------- #
# Tool Registry
# --------------------------------------------------------------------------- #

GITHUB_READ_TOOLS = [
    search_repositories,
    list_issues,
    list_pull_requests,
    list_branches,
]

GITHUB_WRITE_TOOLS = [
    create_issue,
    update_issue,
    create_pull_request,
    merge_pull_request,
    create_branch,
    create_repository,
]

# Map action types to tool functions
GITHUB_TOOL_EXECUTORS = {
    ActionType.CREATE_ISSUE: create_issue,
    ActionType.UPDATE_ISSUE: update_issue,
    ActionType.CREATE_PULL_REQUEST: create_pull_request,
    ActionType.MERGE_PULL_REQUEST: merge_pull_request,
    ActionType.CREATE_BRANCH: create_branch,
}


# --------------------------------------------------------------------------- #
# Main Interface
# --------------------------------------------------------------------------- #

async def get_github_tools_native(user_id: str):
    """
    Get GitHub tools for a specific user using native PyGithub.
    
    This is a lightweight alternative to MCP that uses direct API calls
    instead of spawning Node.js processes.
    
    Args:
        user_id: The user's ID to fetch their GitHub credentials
        
    Returns:
        Tuple of (read_tools, write_tools) dictionaries
    """
    github_oauth = get_github_client(user_id)
    
    if not github_oauth.is_connected():
        return {}, {}
    
    read_tools = {tool.name: tool for tool in GITHUB_READ_TOOLS}
    write_tools = {tool.name: tool for tool in GITHUB_WRITE_TOOLS}
    
    return read_tools, write_tools

