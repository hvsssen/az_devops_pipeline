"""
Git Utilities and Helpers

Common utilities for Git operations including URL parsing,
validation, formatting, and local Git repository management.
"""

import os
import subprocess
import logging
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
import re
from datetime import datetime

from ..models import RepositoryStats, GitCommit


def parse_git_url(git_url: str) -> Dict[str, str]:
    """Parse Git URL to extract owner, repository, and other components"""
    try:
        # Handle SSH URLs (git@github.com:owner/repo.git)
        ssh_pattern = r"git@github\.com:([^/]+)/(.+)\.git"
        ssh_match = re.match(ssh_pattern, git_url)
        
        if ssh_match:
            owner, repo = ssh_match.groups()
            return {
                "owner": owner,
                "repo": repo,
                "url_type": "ssh",
                "host": "github.com",
                "full_name": f"{owner}/{repo}"
            }
        
        # Handle HTTPS URLs
        parsed = urlparse(git_url)
        if parsed.hostname == "github.com":
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]
                
                # Remove .git extension if present
                if repo.endswith(".git"):
                    repo = repo[:-4]
                
                return {
                    "owner": owner,
                    "repo": repo,
                    "url_type": "https",
                    "host": parsed.hostname,
                    "full_name": f"{owner}/{repo}"
                }
        
        raise ValueError("URL format not recognized")
        
    except Exception as e:
        logging.error(f"Failed to parse Git URL: {e}")
        raise ValueError(f"Invalid Git URL format: {git_url}")


def validate_git_url(git_url: str) -> bool:
    """Validate if a URL is a valid Git repository URL"""
    try:
        parse_git_url(git_url)
        return True
    except ValueError:
        return False


def format_repo_name(repo_name: str) -> str:
    """Format repository name for file system safety"""
    # Remove invalid characters for file systems
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', repo_name)
    # Remove leading/trailing dots and spaces
    safe_name = safe_name.strip('. ')
    return safe_name or "unnamed_repo"


def get_local_repo_info(repo_path: str) -> Dict[str, Any]:
    """Get information about a local Git repository"""
    try:
        if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return {"status": "error", "error": "Not a Git repository"}
        
        # Change to repository directory
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Get current branch
            current_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            # Get remote origin URL
            remote_url = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            # Get last commit info
            last_commit = subprocess.run(
                ["git", "log", "-1", "--format=%H|%an|%ae|%s|%ad", "--date=iso"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            # Get repository status
            status_output = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            # Parse last commit info
            commit_parts = last_commit.split("|")
            last_commit_info = None
            if len(commit_parts) == 5:
                last_commit_info = {
                    "sha": commit_parts[0],
                    "author_name": commit_parts[1],
                    "author_email": commit_parts[2],
                    "message": commit_parts[3],
                    "date": commit_parts[4]
                }
            
            return {
                "status": "ok",
                "current_branch": current_branch,
                "remote_url": remote_url,
                "last_commit": last_commit_info,
                "has_changes": bool(status_output),
                "repo_path": repo_path
            }
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {e.stderr}")
        return {"status": "error", "error": f"Git command failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Failed to get local repo info: {e}")
        return {"status": "error", "error": str(e)}


def get_local_branches(repo_path: str) -> List[str]:
    """Get list of local branches in a repository"""
    try:
        if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return []
        
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            result = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                capture_output=True, text=True, check=True
            )
            
            branches = [branch.strip() for branch in result.stdout.split("\n") if branch.strip()]
            return branches
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get local branches: {e.stderr}")
        return []
    except Exception as e:
        logging.error(f"Error getting local branches: {e}")
        return []


def pull_latest_changes(repo_path: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """Pull latest changes from remote repository"""
    try:
        if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return {"status": "error", "error": "Not a Git repository"}
        
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Switch to branch if specified
            if branch:
                subprocess.run(["git", "checkout", branch], capture_output=True, text=True, check=True)
            
            # Pull latest changes
            result = subprocess.run(
                ["git", "pull", "origin"],
                capture_output=True, text=True, check=True
            )
            
            return {
                "status": "ok",
                "message": "Successfully pulled latest changes",
                "output": result.stdout
            }
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Git pull failed: {e.stderr}")
        return {"status": "error", "error": f"Git pull failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Pull changes error: {e}")
        return {"status": "error", "error": str(e)}


def get_repository_size(repo_path: str) -> int:
    """Get repository size in bytes"""
    try:
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(repo_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    except Exception as e:
        logging.error(f"Failed to calculate repository size: {e}")
        return 0


def analyze_repository_stats(repo_path: str) -> RepositoryStats:
    """Analyze local repository and generate statistics"""
    try:
        if not os.path.exists(repo_path) or not os.path.exists(os.path.join(repo_path, ".git")):
            return RepositoryStats()
        
        original_cwd = os.getcwd()
        os.chdir(repo_path)
        
        try:
            # Get total commits
            commit_count_result = subprocess.run(
                ["git", "rev-list", "--all", "--count"],
                capture_output=True, text=True, check=True
            )
            total_commits = int(commit_count_result.stdout.strip())
            
            # Get total branches
            branches = get_local_branches(repo_path)
            total_branches = len(branches)
            
            # Get contributors
            contributors_result = subprocess.run(
                ["git", "shortlog", "-sn", "--all"],
                capture_output=True, text=True, check=True
            )
            total_contributors = len(contributors_result.stdout.strip().split("\n")) if contributors_result.stdout.strip() else 0
            
            # Get last activity
            last_commit_result = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=iso"],
                capture_output=True, text=True, check=True
            )
            last_activity = None
            if last_commit_result.stdout.strip():
                try:
                    last_activity = datetime.fromisoformat(last_commit_result.stdout.strip().replace(' ', 'T'))
                except:
                    pass
            
            # Get repository size
            repo_size = get_repository_size(repo_path) // 1024  # Convert to KB
            
            return RepositoryStats(
                total_commits=total_commits,
                total_branches=total_branches,
                total_contributors=total_contributors,
                last_activity=last_activity,
                repository_size=repo_size
            )
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed during analysis: {e.stderr}")
        return RepositoryStats()
    except Exception as e:
        logging.error(f"Repository analysis error: {e}")
        return RepositoryStats()


def create_git_ignore(repo_path: str, template: str = "python") -> Dict[str, Any]:
    """Create or update .gitignore file with template"""
    try:
        gitignore_templates = {
            "python": """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
env/
.venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Distribution / packaging
dist/
build/
*.egg-info/
""",
            "node": """# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/

# Build outputs
dist/
build/

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
""",
            "general": """# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE files
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log

# Environment
.env
"""
        }
        
        gitignore_path = os.path.join(repo_path, ".gitignore")
        template_content = gitignore_templates.get(template, gitignore_templates["general"])
        
        with open(gitignore_path, "w") as f:
            f.write(template_content)
        
        return {
            "status": "ok",
            "message": f"Created .gitignore with {template} template",
            "path": gitignore_path
        }
        
    except Exception as e:
        logging.error(f"Failed to create .gitignore: {e}")
        return {"status": "error", "error": str(e)}
