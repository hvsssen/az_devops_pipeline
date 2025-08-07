from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel
import httpx
import os
import webbrowser
from typing import List

app = FastAPI()

# Environment variables
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
if not (GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET):
    raise RuntimeError("GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET must be set")

# Pydantic models
class Book(BaseModel):
    title: str
    author: str

class Repository(BaseModel):
    name: str
    full_name: str
    description: str | None
    url: str

class DeployRequest(BaseModel):
    repo_full_name: str
    azure_resource_group: str
    aks_cluster_name: str

class LoginResponse(BaseModel):
    login_url: str
    message: str

# Method: Generate GitHub OAuth login URL
def get_github_login_url():
    return (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=repo%20read:user"
    )

# Method: Open login URL in browser
def open_login_in_browser():
    url = get_github_login_url()
    webbrowser.open(url)
    return url

# Method: Exchange OAuth code for access token
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

# Method: Fetch user repositories
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

# Method: Deploy to Azure (placeholder)
async def deploy_to_azure(repo_full_name: str, resource_group: str, cluster_name: str) -> dict:
    return {
        "status": "Deployment initiated",
        "repo": repo_full_name,
        "resource_group": resource_group,
        "aks_cluster": cluster_name
    }

# Browser login endpoint
@app.get("/github/login-browser")
async def github_login_browser():
    url = open_login_in_browser()
    return {"message": f"Opened GitHub login in browser: {url}"}

# MCP-compatible login endpoint
@app.get("/github/login", response_model=LoginResponse)
async def github_login_mcp():
    url = get_github_login_url()
    return {"login_url": url, "message": "Please open this URL in a browser to authenticate"}

# OAuth callback
@app.get("/callback", response_model=List[Repository])
async def github_callback(code: str = Query(...)):
    token = await exchange_code_for_token(code)
    return await fetch_repositories(token)

# Book endpoints
@app.get("/books", response_model=List[Book])
async def get_books():
    return [{"title": "Book1", "author": "Author1"}]

@app.post("/books", response_model=Book)
async def create_book(book: Book):
    return book

# Deployment endpoint
@app.post("/deploy", response_model=dict)
async def deploy_repository(deploy: DeployRequest):
    return await deploy_to_azure(
        deploy.repo_full_name,
        deploy.azure_resource_group,
        deploy.aks_cluster_name
    )

# Initialize and mount FastApiMCP
mcp = FastApiMCP(app)
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)