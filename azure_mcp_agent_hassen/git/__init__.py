"""
Git Package

Comprehensive Git and GitHub management package providing modular access to
repository operations, authentication, and GitHub API interactions.

This package provides a clean, modular interface for:
- GitHub OAuth authentication and session management
- Repository cloning, fetching, and management
- GitHub API interactions for repositories, commits, and branches
- Local Git repository analysis and utilities
- URL parsing and validation for Git operations
"""

# Core models
from .models import (
    Repository,
    LoginResponse,
    AuthToken,
    GitHubUser,
    CloneRequest,
    CloneResult,
    GitCommit,
    GitBranch,
    PullRequest,
    GitHubWebhook,
    RepositoryStats
)

# Authentication
from .auth import (
    get_github_login_url,
    initiate_github_login,
    exchange_code_for_token,
    get_authenticated_user,
    store_user_session,
    get_user_session,
    get_all_users,
    validate_token
)

# Repository services
from .services import (
    fetch_user_repositories,
    get_repository_info,
    clone_repository,
    get_repository_branches,
    get_repository_commits,
    search_repositories
)

# Utilities
from .utils import (
    parse_git_url,
    validate_git_url,
    format_repo_name,
    get_local_repo_info,
    get_local_branches,
    pull_latest_changes,
    analyze_repository_stats
)

__all__ = [
    # Models
    "Repository",
    "LoginResponse",
    "AuthToken",
    "GitHubUser",
    "CloneRequest",
    "CloneResult",
    "GitCommit",
    "GitBranch",
    "PullRequest",
    "GitHubWebhook",
    "RepositoryStats",
    
    # Authentication
    "get_github_login_url",
    "initiate_github_login",
    "exchange_code_for_token",
    "get_authenticated_user",
    "store_user_session",
    "get_user_session",
    "get_all_users",
    "validate_token",
    
    # Repository services
    "fetch_user_repositories",
    "get_repository_info",
    "clone_repository",
    "get_repository_branches",
    "get_repository_commits",
    "search_repositories",
    
    # Utilities
    "parse_git_url",
    "validate_git_url",
    "format_repo_name",
    "get_local_repo_info",
    "get_local_branches",
    "pull_latest_changes",
    "analyze_repository_stats"
]

__version__ = "1.0.0"
__author__ = "Azure MCP DevOps Agent"
__description__ = "Modular Git and GitHub management package"
