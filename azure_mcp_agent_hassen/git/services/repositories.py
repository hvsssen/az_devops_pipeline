"""
Repository Management Services

Business logic for repository operations including cloning,
fetching repository information, and GitHub API interactions.
"""

import os
import subprocess
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import httpx

from ..models import Repository, CloneRequest, CloneResult, GitCommit, GitBranch, RepositoryStats
from ..auth import validate_token


async def fetch_user_repositories(token: str) -> List[Repository]:
    """Fetch repositories for authenticated user"""
    try:
        if not await validate_token(token):
            raise ValueError("Invalid or expired token")
        
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/user/repos", headers=headers)
            response.raise_for_status()
            repos_data = response.json()
            
            repositories = []
            for repo in repos_data:
                repositories.append(Repository(
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    ssh_url=repo["ssh_url"],
                    private=repo["private"],
                    default_branch=repo.get("default_branch", "main"),
                    language=repo.get("language"),
                    stars_count=repo.get("stargazers_count", 0),
                    forks_count=repo.get("forks_count", 0)
                ))
            
            return repositories
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error fetching repositories: {e}")
        raise ValueError(f"Failed to fetch repositories: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error fetching repositories: {e}")
        raise ValueError(f"Repository fetch error: {str(e)}")


async def get_repository_info(owner: str, repo: str, token: Optional[str] = None) -> Repository:
    """Get detailed information about a specific repository"""
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
            response.raise_for_status()
            repo_data = response.json()
            
            return Repository(
                name=repo_data["name"],
                full_name=repo_data["full_name"],
                description=repo_data.get("description"),
                url=repo_data["html_url"],
                clone_url=repo_data["clone_url"],
                ssh_url=repo_data["ssh_url"],
                private=repo_data["private"],
                default_branch=repo_data.get("default_branch", "main"),
                language=repo_data.get("language"),
                stars_count=repo_data.get("stargazers_count", 0),
                forks_count=repo_data.get("forks_count", 0)
            )
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error getting repository info: {e}")
        raise ValueError(f"Failed to get repository info: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error getting repository info: {e}")
        raise ValueError(f"Repository info error: {str(e)}")


def clone_repository(clone_request: CloneRequest) -> CloneResult:
    """Clone a GitHub repository to local directory"""
    try:
        # Parse repository URL to get name
        parsed_url = urlparse(clone_request.repo_url)
        repo_name = os.path.splitext(os.path.basename(parsed_url.path))[0]
        
        # Determine target directory
        if clone_request.target_dir:
            base_dir = clone_request.target_dir
        else:
            base_dir = "./repos"
        
        repo_path = os.path.join(base_dir, repo_name)
        
        # Create base directory if it doesn't exist
        os.makedirs(base_dir, exist_ok=True)
        
        # Check if repository already exists
        if os.path.exists(repo_path):
            return CloneResult(
                status="exists",
                repo_path=repo_path,
                repo_name=repo_name,
                message=f"Repository already exists at {repo_path}"
            )
        
        # Build git clone command
        cmd = ["git", "clone"]
        
        if clone_request.branch:
            cmd.extend(["--branch", clone_request.branch])
        
        if clone_request.depth:
            cmd.extend(["--depth", str(clone_request.depth)])
        
        if clone_request.recursive:
            cmd.append("--recursive")
        
        cmd.extend([clone_request.repo_url, repo_path])
        
        # Execute clone command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return CloneResult(
            status="success",
            repo_path=repo_path,
            repo_name=repo_name,
            message=f"Successfully cloned repository to {repo_path}",
            branch=clone_request.branch
        )
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Git clone failed: {e.stderr}")
        return CloneResult(
            status="error",
            repo_path="",
            repo_name=repo_name if 'repo_name' in locals() else "unknown",
            message=f"Clone failed: {e.stderr}"
        )
    except Exception as e:
        logging.error(f"Clone repository error: {e}")
        return CloneResult(
            status="error",
            repo_path="",
            repo_name=repo_name if 'repo_name' in locals() else "unknown",
            message=f"Clone error: {str(e)}"
        )


async def get_repository_branches(owner: str, repo: str, token: Optional[str] = None) -> List[GitBranch]:
    """Get all branches for a repository"""
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.github.com/repos/{owner}/{repo}/branches", headers=headers)
            response.raise_for_status()
            branches_data = response.json()
            
            branches = []
            for branch in branches_data:
                branches.append(GitBranch(
                    name=branch["name"],
                    commit_sha=branch["commit"]["sha"],
                    is_protected=branch.get("protected", False)
                ))
            
            return branches
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error getting branches: {e}")
        raise ValueError(f"Failed to get branches: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error getting branches: {e}")
        raise ValueError(f"Branches error: {str(e)}")


async def get_repository_commits(owner: str, repo: str, branch: str = "main", 
                               limit: int = 10, token: Optional[str] = None) -> List[GitCommit]:
    """Get recent commits for a repository branch"""
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        params = {"sha": branch, "per_page": limit}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            commits_data = response.json()
            
            commits = []
            for commit in commits_data:
                commits.append(GitCommit(
                    sha=commit["sha"],
                    author_name=commit["commit"]["author"]["name"],
                    author_email=commit["commit"]["author"]["email"],
                    message=commit["commit"]["message"],
                    date=commit["commit"]["author"]["date"],
                    url=commit["html_url"]
                ))
            
            return commits
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error getting commits: {e}")
        raise ValueError(f"Failed to get commits: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error getting commits: {e}")
        raise ValueError(f"Commits error: {str(e)}")


async def search_repositories(query: str, sort: str = "stars", order: str = "desc", 
                            limit: int = 10, token: Optional[str] = None) -> List[Repository]:
    """Search GitHub repositories"""
    try:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": limit
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/search/repositories", headers=headers, params=params)
            response.raise_for_status()
            search_data = response.json()
            
            repositories = []
            for repo in search_data.get("items", []):
                repositories.append(Repository(
                    name=repo["name"],
                    full_name=repo["full_name"],
                    description=repo.get("description"),
                    url=repo["html_url"],
                    clone_url=repo["clone_url"],
                    ssh_url=repo["ssh_url"],
                    private=repo["private"],
                    default_branch=repo.get("default_branch", "main"),
                    language=repo.get("language"),
                    stars_count=repo.get("stargazers_count", 0),
                    forks_count=repo.get("forks_count", 0)
                ))
            
            return repositories
            
    except httpx.HTTPError as e:
        logging.error(f"HTTP error searching repositories: {e}")
        raise ValueError(f"Failed to search repositories: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error searching repositories: {e}")
        raise ValueError(f"Repository search error: {str(e)}")
