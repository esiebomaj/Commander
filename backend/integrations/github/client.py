"""
GitHub client for Commander.

Provides a wrapper around PyGithub for interacting with GitHub repositories.
Handles authentication using stored OAuth tokens per user.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .oauth import get_github_client as get_github_oauth


class GitHubClient:
    """
    GitHub client for interacting with GitHub repositories.
    
    Uses the user's stored OAuth token for authentication.
    
    Usage:
        client = GitHubClient(user_id="user_id")
        
        if client.is_connected():
            repos = client.list_repositories()
            client.create_issue(owner="owner", repo="repo", title="Bug")
    """
    
    def __init__(self, user_id: str):
        """Initialize the GitHub client for a specific user."""
        if not user_id:
            raise ValueError("user_id is required")
        
        self._user_id = user_id
        self._oauth = get_github_oauth(user_id)
        self._client = None
    
    # ----------------------------------------------------------------------- #
    # Connection Status
    # ----------------------------------------------------------------------- #
    
    def is_connected(self) -> bool:
        """Check if GitHub is connected for this user."""
        return self._oauth.is_connected()
    
    def get_username(self) -> Optional[str]:
        """Get the connected GitHub username."""
        return self._oauth.get_username()
    
    # ----------------------------------------------------------------------- #
    # Internal: Get PyGithub Client
    # ----------------------------------------------------------------------- #
    
    def _get_client(self):
        """Get the PyGithub client, initializing if needed."""
        if self._client:
            return self._client
        
        from github import Github
        
        access_token = self._oauth.get_access_token()
        if not access_token:
            raise ValueError("GitHub is not connected. Please authenticate first.")
        
        self._client = Github(access_token)
        return self._client
    
    # ----------------------------------------------------------------------- #
    # Repositories
    # ----------------------------------------------------------------------- #
    
    def list_repositories(
        self,
        limit: int = 30,
        visibility: str = "all",
    ) -> Dict[str, Any]:
        """
        List repositories for the authenticated user.
        
        Args:
            limit: Maximum number of repos to return
            visibility: 'all', 'public', or 'private'
        
        Returns:
            Dict with success status and repos list or error
        """
        try:
            client = self._get_client()
            user = client.get_user()
            repos = []
            
            for repo in user.get_repos(visibility=visibility)[:limit]:
                repos.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "url": repo.html_url,
                    "default_branch": repo.default_branch,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                })
            
            return {"success": True, "repositories": repos}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        auto_init: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new repository for the authenticated user.
        
        Args:
            name: Repository name
            description: Repository description (optional)
            private: Whether the repo should be private (default: False)
            auto_init: Initialize with a README (default: True)
        
        Returns:
            Dict with success status and repo info or error
        """
        try:
            client = self._get_client()
            user = client.get_user()
            
            repo = user.create_repo(
                name=name,
                description=description or "",
                private=private,
                auto_init=auto_init,
            )
            
            return {
                "success": True,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "private": repo.private,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "default_branch": repo.default_branch,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_repositories(
        self,
        query: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Search for repositories.
        
        Args:
            query: Search query string
            limit: Maximum number of results
        
        Returns:
            Dict with success status and repos list or error
        """
        try:
            client = self._get_client()
            repos = []
            
            for repo in client.search_repositories(query)[:limit]:
                repos.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "url": repo.html_url,
                    "stars": repo.stargazers_count,
                })
            
            return {"success": True, "repositories": repos}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Issues
    # ----------------------------------------------------------------------- #
    
    def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 30,
    ) -> Dict[str, Any]:
        """
        List issues for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: 'open', 'closed', or 'all'
            limit: Maximum number of issues to return
        
        Returns:
            Dict with success status and issues list or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            issues = []
            
            for issue in repository.get_issues(state=state)[:limit]:
                if issue.pull_request is None:  # Exclude PRs
                    issues.append({
                        "number": issue.number,
                        "title": issue.title,
                        "state": issue.state,
                        "body": issue.body[:500] if issue.body else None,
                        "user": issue.user.login if issue.user else None,
                        "labels": [l.name for l in issue.labels],
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "url": issue.html_url,
                    })
            
            return {"success": True, "issues": issues}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: Issue title
            body: Issue body (optional)
            labels: List of label names (optional)
        
        Returns:
            Dict with success status and issue info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            
            issue = repository.create_issue(
                title=title,
                body=body or "",
                labels=labels or [],
            )
            
            return {
                "success": True,
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: New state - 'open' or 'closed' (optional)
            labels: New labels (optional)
        
        Returns:
            Dict with success status and issue info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            issue = repository.get_issue(issue_number)
            
            kwargs = {}
            if title is not None:
                kwargs["title"] = title
            if body is not None:
                kwargs["body"] = body
            if state is not None:
                kwargs["state"] = state
            if labels is not None:
                kwargs["labels"] = labels
            
            if kwargs:
                issue.edit(**kwargs)
            
            return {
                "success": True,
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "url": issue.html_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def add_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue.
        
        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            body: Comment body
        
        Returns:
            Dict with success status and comment info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            issue = repository.get_issue(issue_number)
            
            comment = issue.create_comment(body)
            
            return {
                "success": True,
                "comment_id": comment.id,
                "url": comment.html_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Pull Requests
    # ----------------------------------------------------------------------- #
    
    def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        limit: int = 30,
    ) -> Dict[str, Any]:
        """
        List pull requests for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: 'open', 'closed', or 'all'
            limit: Maximum number of PRs to return
        
        Returns:
            Dict with success status and PRs list or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            prs = []
            
            for pr in repository.get_pulls(state=state)[:limit]:
                prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "user": pr.user.login if pr.user else None,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "mergeable": pr.mergeable,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "url": pr.html_url,
                })
            
            return {"success": True, "pull_requests": prs}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Head branch name
            base: Base branch name
            body: PR body (optional)
        
        Returns:
            Dict with success status and PR info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            
            pr = repository.create_pull(
                title=title,
                head=head,
                base=base,
                body=body or "",
            )
            
            return {
                "success": True,
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        merge_method: str = "merge",
        commit_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pull_number: PR number
            merge_method: 'merge', 'squash', or 'rebase'
            commit_message: Custom commit message (optional)
        
        Returns:
            Dict with success status and merge info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            pr = repository.get_pull(pull_number)
            
            result = pr.merge(
                merge_method=merge_method,
                commit_message=commit_message,
            )
            
            return {
                "success": True,
                "merged": result.merged,
                "sha": result.sha,
                "message": result.message,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ----------------------------------------------------------------------- #
    # Branches
    # ----------------------------------------------------------------------- #
    
    def list_branches(
        self,
        owner: str,
        repo: str,
        limit: int = 30,
    ) -> Dict[str, Any]:
        """
        List branches for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            limit: Maximum number of branches to return
        
        Returns:
            Dict with success status and branches list or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            branches = []
            
            for branch in repository.get_branches()[:limit]:
                branches.append({
                    "name": branch.name,
                    "protected": branch.protected,
                    "sha": branch.commit.sha if branch.commit else None,
                })
            
            return {"success": True, "branches": branches}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        source_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new branch.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name for the new branch
            source_branch: Branch to create from (default: repo's default branch)
        
        Returns:
            Dict with success status and branch info or error
        """
        try:
            client = self._get_client()
            repository = client.get_repo(f"{owner}/{repo}")
            
            # Get source branch SHA
            source = source_branch or repository.default_branch
            source_ref = repository.get_branch(source)
            sha = source_ref.commit.sha
            
            # Create the new branch
            ref = repository.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=sha,
            )
            
            return {
                "success": True,
                "branch": branch_name,
                "sha": ref.object.sha,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# --------------------------------------------------------------------------- #
# Factory Function
# --------------------------------------------------------------------------- #

def get_github(user_id: str) -> GitHubClient:
    """
    Get a GitHub client instance for a specific user.
    
    Args:
        user_id: The user's ID
    
    Returns:
        GitHubClient configured for the user
    """
    return GitHubClient(user_id=user_id)

