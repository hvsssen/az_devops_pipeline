from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP
import webbrowser
from typing import List
from dotenv import load_dotenv
import os

# Import utils
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
from docker_utils import docker_login, build_image, push_image,run_container, DeployRequest

load_dotenv()
users = get_users()

app = FastAPI()

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------- Web UI Documentation ----------
@app.get("/")
async def documentation_home(request: Request):
    logged_in = len(users) > 0
    return templates.TemplateResponse("documentation.html", {"request": request, "logged_in": logged_in})

@app.get("/web/login")
async def web_github_login():
    url = get_github_login_url()
    return RedirectResponse(url)

@app.get("/callback")
async def github_callback(code: str = Query(...)):
    token = await exchange_code_for_token(code)
    repos = await fetch_repositories(token)
    users[token] = repos
    return RedirectResponse("/")


@app.post("/web/clone")
async def web_clone(request: Request, repo_url: str = Form(...)):
    try:
        path = clone_repo(repo_url)
        message = f"Repository cloned successfully: {path}"
    except Exception as e:
        message = f"Error: {str(e)}"
    return templates.TemplateResponse("index.html", {"request": request, "logged_in": True, "message": message})

@app.post("/web/deploy")
async def web_deploy(request: Request, repo_path: str = Form(...), image_name: str = Form(...), tag: str = Form("latest")):
    try:
        docker_login()
        built_image = build_image(repo_path, image_name, tag)
        push_image(image_name, tag)
        message = f"✅ Deployment successful: {built_image}"
    except Exception as e:
        message = f"❌ Deployment failed: {str(e)}"
    return templates.TemplateResponse("index.html", {"request": request, "logged_in": True, "message": message})

# ---------- MCP ----------
@app.get("/github/repos", response_model=List[Repository])
async def get_repositories(token: str = Query(None)):
    if not token:
        if not users:
            raise HTTPException(status_code=401, detail="No authorized users. Authorize first via /github/login.")
        return list(users.values())[0]
    if token not in users:
        raise HTTPException(status_code=404, detail="Token not found. Authorize first via /github/login.")
    return users[token]

@app.get("/github/login", response_model=LoginResponse)
async def github_login_mcp():
    url = get_github_login_url()
    webbrowser.open_new_tab(url)
    return {"login_url": url, "message": "Please open this URL in a browser to authenticate"}

@app.get("/clone")
def clone_repository(repo_url: str = Query(...)):
    try:
        path = clone_repo(repo_url)
        return {"message": "Repository cloned successfully", "local_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deploy")
async def deploy(request: DeployRequest):
    try:
        docker_login()
        built_image = build_image(request.repo_path, request.image_name, request.tag)
        push_image(request.image_name, request.tag)
        return {"status": "success", "image": f"{request.image_name}:{request.tag}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
@app.get("/run_container")
def run_docker_container(image: str = Query(...), tag: str = "latest"):
    run_container(image, tag, container_name="my_test_container", ports={8000: 8000})
    return {"status": "running", "image": f"{image}:{tag}"}
# ---------- MCP mount ----------
mcp = FastApiMCP(app)
mcp.mount_http()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
