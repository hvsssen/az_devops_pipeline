from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel
import httpx
import os
import webbrowser
from typing import List
from dotenv import load_dotenv
from git_utils import (
    get_github_login_url,
    open_login_in_browser,
    exchange_code_for_token,
    fetch_repositories,
    get_users,
    clone_repo,
    Repository,
    LoginResponse,
)
from docker_utils import (docker_login, build_image, push_image, DeployRequest)


users = get_users()

print("hahahahhhahah", users)
app = FastAPI()

# Repository fetch endpoint
@app.get("/github/repos", response_model=List[Repository])
async def get_repositories(token: str = Query(None)):
    if not token:
        if not users:
            raise HTTPException(status_code=401, detail="No authorized users. Authorize first via /github/login.")
        return list(users.values())[0]  # Return first user's repos if no token provided
    if token not in users:
        raise HTTPException(status_code=404, detail="Token not found. Authorize first via /github/login.")
    return users[token]

    

# Browser login endpoint
@app.get("/github/login-browser")
async def github_login_browser():
    url = open_login_in_browser()
    return {"message": f"Opened GitHub login in browser: {url}"}

# MCP-compatible login endpoint
@app.get("/github/login", response_model=LoginResponse)
async def github_login_mcp():
    url = get_github_login_url()
    webbrowser.open_new_tab(url)
    return {"login_url": url, "message": "a web window with this url must be opened if not Please open this URL in a browser to authenticate"}

# OAuth callback
@app.get("/callback", response_model=List[Repository])
async def github_callback(code: str = Query(...)):
    token = await exchange_code_for_token(code)
    repos = await fetch_repositories(token)
    users[token] = repos  # Store token and repos in dict
    return repos



@app.get("/clone")
def clone_repository(repo_url: str = Query(..., description="GitHub repository URL")):
    try:
        path = clone_repo(repo_url)
        return {
            "message": "Repository cloned successfully",
            "local_path": path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deploy")
async def deploy(request: DeployRequest):
    try:
        # Step 1: Log in to Docker
        docker_login()

        # Step 2: Build Docker image
        built_image = build_image(
            repo_path=request.repo_path,
            image_name=request.image_name,
            tag=request.tag
        )

        # Step 3: Push Docker image to Docker Hub
        push_image(
            image_name=request.image_name,
            tag=request.tag
        )

        return {
            "status": "success",
            "image": f"{request.image_name}:{request.tag}"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
# Initialize and mount FastApiMCP
mcp = FastApiMCP(app)
mcp.mount_http()
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

