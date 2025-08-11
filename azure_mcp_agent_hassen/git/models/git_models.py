"""
Git and GitHub Data Models

Pydantic models for Git operations including repository information,
authentication responses, and GitHub API interactions.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


class Repository(BaseModel):
    """GitHub repository information"""
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    description: Optional[str] = Field(None, description="Repository description")
    url: str = Field(..., description="Repository HTML URL")
    clone_url: Optional[str] = Field(None, description="Repository clone URL")
    ssh_url: Optional[str] = Field(None, description="Repository SSH URL")
    private: bool = Field(default=False, description="Whether repository is private")
    default_branch: str = Field(default="main", description="Default branch name")
    language: Optional[str] = Field(None, description="Primary programming language")
    stars_count: int = Field(default=0, description="Number of stars")
    forks_count: int = Field(default=0, description="Number of forks")
    created_at: Optional[datetime] = Field(None, description="Repository creation date")
    updated_at: Optional[datetime] = Field(None, description="Last update date")


class LoginResponse(BaseModel):
    """GitHub OAuth login response"""
    login_url: str = Field(..., description="OAuth authorization URL")
    message: str = Field(..., description="Instructions for user")


class AuthToken(BaseModel):
    """GitHub authentication token information"""
    access_token: str = Field(..., description="GitHub access token")
    token_type: str = Field(default="bearer", description="Token type")
    scope: Optional[str] = Field(None, description="Token scope permissions")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Token creation time")


class GitHubUser(BaseModel):
    """GitHub user information"""
    login: str = Field(..., description="GitHub username")
    id: int = Field(..., description="GitHub user ID")
    name: Optional[str] = Field(None, description="User's display name")
    email: Optional[str] = Field(None, description="User's email address")
    bio: Optional[str] = Field(None, description="User's bio")
    avatar_url: Optional[str] = Field(None, description="User's avatar URL")
    public_repos: int = Field(default=0, description="Number of public repositories")
    followers: int = Field(default=0, description="Number of followers")
    following: int = Field(default=0, description="Number of users following")


class CloneRequest(BaseModel):
    """Repository clone request"""
    repo_url: str = Field(..., description="Repository URL to clone")
    target_dir: Optional[str] = Field(None, description="Target directory for clone")
    branch: Optional[str] = Field(None, description="Specific branch to clone")
    depth: Optional[int] = Field(None, description="Clone depth (shallow clone)")
    recursive: bool = Field(default=False, description="Clone submodules recursively")


class CloneResult(BaseModel):
    """Repository clone operation result"""
    status: str = Field(..., description="Clone operation status")
    repo_path: str = Field(..., description="Local path to cloned repository")
    repo_name: str = Field(..., description="Repository name")
    message: str = Field(..., description="Operation message")
    branch: Optional[str] = Field(None, description="Cloned branch")


class GitCommit(BaseModel):
    """Git commit information"""
    sha: str = Field(..., description="Commit SHA hash")
    author_name: str = Field(..., description="Commit author name")
    author_email: str = Field(..., description="Commit author email")
    message: str = Field(..., description="Commit message")
    date: datetime = Field(..., description="Commit date")
    url: Optional[str] = Field(None, description="Commit URL on GitHub")


class GitBranch(BaseModel):
    """Git branch information"""
    name: str = Field(..., description="Branch name")
    commit_sha: str = Field(..., description="Latest commit SHA")
    is_default: bool = Field(default=False, description="Whether this is the default branch")
    is_protected: bool = Field(default=False, description="Whether branch is protected")


class PullRequest(BaseModel):
    """GitHub pull request information"""
    number: int = Field(..., description="Pull request number")
    title: str = Field(..., description="Pull request title")
    description: Optional[str] = Field(None, description="Pull request description")
    state: str = Field(..., description="Pull request state (open, closed, merged)")
    author: str = Field(..., description="Pull request author")
    base_branch: str = Field(..., description="Target branch")
    head_branch: str = Field(..., description="Source branch")
    created_at: datetime = Field(..., description="Creation date")
    updated_at: datetime = Field(..., description="Last update date")
    mergeable: Optional[bool] = Field(None, description="Whether PR is mergeable")


class GitHubWebhook(BaseModel):
    """GitHub webhook configuration"""
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to trigger webhook")
    active: bool = Field(default=True, description="Whether webhook is active")
    secret: Optional[str] = Field(None, description="Webhook secret for verification")


class RepositoryStats(BaseModel):
    """Repository statistics and metrics"""
    total_commits: int = Field(default=0, description="Total number of commits")
    total_branches: int = Field(default=0, description="Total number of branches")
    total_contributors: int = Field(default=0, description="Total number of contributors")
    languages: Dict[str, int] = Field(default_factory=dict, description="Languages used with byte counts")
    last_activity: Optional[datetime] = Field(None, description="Last activity date")
    repository_size: int = Field(default=0, description="Repository size in KB")
