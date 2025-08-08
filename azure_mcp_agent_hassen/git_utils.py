# git_utils.py

from pydantic import BaseModel
from typing import List
import httpx
import os
import webbrowser
from fastapi import HTTPException
from dotenv import load_dotenv
import subprocess
from urllib.parse import urlparse

load_dotenv()
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

if not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET):
    raise RuntimeError("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set")

# Global user dict (token -> repos)
users = {}

class Repository(BaseModel):
    name: str
    full_name: str
    description: str | None
    url: str


class LoginResponse(BaseModel):
    login_url: str
    message: str

def get_users():
    return users


def get_github_login_url():
    return (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=repo%20read:user"
    )


def open_login_in_browser():
    url = get_github_login_url()
    webbrowser.open_new_tab(url)
    return url


async def exchange_code_for_token(code: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code
            },
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        return token


async def fetch_repositories(token: str) -> List[Repository]:
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.github.com/user/repos", headers=headers)
        response.raise_for_status()
        repos = response.json()
        return [
            Repository(
                name=repo["name"],
                full_name=repo["full_name"],
                description=repo.get("description"),
                url=repo["html_url"]
            ) for repo in repos
        ]


def clone_repo(repo_url: str, base_dir: str = "./repos") -> str:
    """Clone a GitHub repo to the local repos directory and return its path."""
    repo_name = os.path.splitext(os.path.basename(urlparse(repo_url).path))[0]
    repo_path = os.path.join(base_dir, repo_name)

    os.makedirs(base_dir, exist_ok=True)

    if os.path.exists(repo_path):
        print(f"Repo already cloned at {repo_path}")
    else:
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)
        print(f"Cloned repo to {repo_path}")

    return repo_path