from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP
import webbrowser
from typing import List
from dotenv import load_dotenv
import os

# Import utils - Clean modular structure  
from .git import (
    # Core Models (only import ones that definitely exist)
    Repository,
    LoginResponse,
    CloneRequest,
    
    # Authentication & Session Management (will require OAuth env vars)
    get_github_login_url,
    initiate_github_login,
    exchange_code_for_token,
    get_all_users,
    push_repository_changes,
    
    # Repository Services
    fetch_user_repositories,
    clone_repository
    
    # Note: Additional imports like AuthToken, GitHubUser, CloneResult, etc.
    # may require the git package models to be properly configured
)

from .docker import (
    # Core operations
    docker_login, 
    build_image, 
    push_image, 
    run_container,
    # Utils
    parse_dockerfile_info,
    # Port detection utilities
    detect_project_ports,
    generate_container_name,
    # Models
    DeployRequest,
    ContainerRunOptions
)

from .azure import (
    # Auth & session
    launch_azure_login,
    load_azure_session,
    # VM operations
    get_azure_vm_usage_and_cost,
    get_azure_vm_details,
    # Resource management
    list_azure_resource_groups,
    # CLI
    az_command,
    az_command_async,
    # Models
    AzureLoginResponse,
    AzureSubscriptionsResponse,
    AzureVMUsageResponse,
    AzureResourceGroup,
    VMInstanceView,
    AzureCostEntry,
    AzureMetric
)

from .github_actions import (
    # Models
    WorkflowJob,
    WorkflowConfig,
    # Services
    create_deploy_workflow,
    setup_ci_cd,
    select_branch
)

load_dotenv()
users = get_all_users()

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
    auth_token = await exchange_code_for_token(code)
    access_token = auth_token.access_token
    repos = await fetch_user_repositories(access_token)
    users[access_token] = repos
    return RedirectResponse("/")


@app.post("/web/clone")
async def web_clone(request: Request, repo_url: str = Form(...)):
    try:
        clone_request = CloneRequest(repo_url=repo_url)
        clone_result = clone_repository(clone_request)
        path = clone_result.repo_path
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

@app.post("/web/push")
async def web_push(request: Request, repo_path: str = Form(...), commit_message: str = Form("Add workflow files")):
    try:
        # Ensure the path is absolute and in repos directory for security
        if not os.path.isabs(repo_path):
            repo_path = os.path.abspath(os.path.join("./repos", repo_path))
        
        result = push_repository_changes(repo_path, commit_message)
        
        if result["status"] == "success":
            message = f"✅ Push successful: {result['message']}"
        elif result["status"] == "info":
            message = f"ℹ️ {result['message']}"
        else:
            message = f"❌ Push failed: {result['message']}"
    except Exception as e:
        message = f"❌ Push failed: {str(e)}"
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
def clone_repository_endpoint(repo_url: str = Query(...)):
    try:
        clone_request = CloneRequest(repo_url=repo_url)
        clone_result = clone_repository(clone_request)
        return {"message": "Repository cloned successfully", "local_path": clone_result.repo_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/git/push")
def push_repository_endpoint(repo_path: str = Query(...), commit_message: str = Query("Add workflow files")):
    """Push all changes in a repository"""
    try:
        # Ensure the path is absolute and in repos directory for security
        if not os.path.isabs(repo_path):
            repo_path = os.path.abspath(os.path.join("./repos", repo_path))
        
        result = push_repository_changes(repo_path, commit_message)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": result["message"],
                "repo_path": repo_path,
                "commit_message": commit_message,
                "commit_output": result.get("commit_output", ""),
                "push_output": result.get("push_output", "")
            }
        elif result["status"] == "info":
            return {
                "status": "info",
                "message": result["message"],
                "repo_path": repo_path
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Push failed: {str(e)}")

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
def run_docker_container(image: str = Query(...), tag: str = "latest", repo_path: str = Query(None)):
    if repo_path:
        # Use auto-detection with repository context
        port_detection = detect_project_ports(repo_path)
        container_name = generate_container_name(image, tag)
        run_container(image, tag, container_name=container_name)
        
        return {
            "status": "running", 
            "image": f"{image}:{tag}",
            "container_name": container_name,
            "ports_detected": port_detection.detected_ports,
            "dockerfile_ports": port_detection.dockerfile_ports,
            "recommended_ports": port_detection.recommended_ports,
            "config_ports": port_detection.config_ports,
            "message": f"Container running with auto-detected ports: {port_detection.detected_ports}"
        }
    else:
        # Fallback to default behavior
        container_name = generate_container_name(image, tag)
        run_container(image, tag, container_name=container_name)
        return {
            "status": "running", 
            "image": f"{image}:{tag}",
            "container_name": container_name,
            "ports_used": [8000],
            "message": "Container running with default port 8000 (no repo_path provided for auto-detection)"
        }

@app.get("/detect_ports")
def detect_ports_endpoint(repo_path: str = Query(...)):
    """Endpoint to detect ports from a repository without running container"""
    try:
        port_detection = detect_project_ports(repo_path)
        
        return {
            "status": "success",
            "repo_path": repo_path,
            "port_detection": {
                "detected_ports": port_detection.detected_ports,
                "dockerfile_ports": port_detection.dockerfile_ports,
                "recommended_ports": port_detection.recommended_ports,
                "config_ports": port_detection.config_ports,
                "default_ports": port_detection.default_ports
            },
            "detection_summary": {
                "total_detected": len(port_detection.detected_ports),
                "dockerfile_found": len(port_detection.dockerfile_ports) > 0,
                "config_files_found": len(port_detection.config_ports) > 0,
                "has_recommendations": len(port_detection.recommended_ports) > 0
            },
            "suggested_container_name": generate_container_name("app", "latest")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Port detection failed: {str(e)}")

@app.get("/dockerfile/parse")
def parse_dockerfile_endpoint(repo_path: str = Query(...)):
    """Parse Dockerfile and extract configuration information"""
    try:
        dockerfile_path = os.path.join(repo_path, "Dockerfile")
        if not os.path.exists(dockerfile_path):
            raise HTTPException(status_code=404, detail="Dockerfile not found in repository")
        
        dockerfile_info = parse_dockerfile_info(dockerfile_path)
        
        return {
            "status": "success",
            "dockerfile_path": dockerfile_path,
            "base_image": dockerfile_info.base_image,
            "exposed_ports": dockerfile_info.exposed_ports,
            "env_vars": dockerfile_info.env_vars,
            "build_args": dockerfile_info.build_args,
            "labels": dockerfile_info.labels,
            "working_dir": dockerfile_info.working_dir,
            "entrypoint": dockerfile_info.entrypoint,
            "cmd": dockerfile_info.cmd
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dockerfile parsing failed: {str(e)}")


# ---------- Azure Integration ----------
async def azure_login_handler():
    """Wrapper for backward compatibility"""
    return launch_azure_login()

async def get_azure_subscriptions():
    """Wrapper for backward compatibility"""
    try:
        subscriptions = load_azure_session()
        if subscriptions:
            return AzureSubscriptionsResponse(
                status="ok",
                subscriptions=subscriptions,
                message=f"Successfully retrieved {len(subscriptions)} subscriptions"
            )
        else:
            return AzureSubscriptionsResponse(
                status="not_logged_in",
                message="Please log in first"
            )
    except Exception as e:
        return AzureSubscriptionsResponse(
            status="error",
            error=str(e),
            message="Failed to retrieve Azure subscriptions"
        )

async def azure_vm_usage_handler():
    """Wrapper for backward compatibility"""
    try:
        result = get_azure_vm_usage_and_cost()
        return AzureVMUsageResponse(
            status=result.get("status", "error"),
            vms=result.get("vms", []),
            total_cost=result.get("total_cost", 0.0),
            currency=result.get("currency"),
            debug=result.get("debug", []),
            vm_error=result.get("vm_error"),
            cost_error=result.get("cost_error")
        )
    except Exception as e:
        return AzureVMUsageResponse(
            status="error",
            vms=[],
            total_cost=0.0,
            debug=[f"Error: {str(e)}"]
        )

async def azure_vm_details_handler(vm_name: str, resource_group: str, subscription_id: str = None):
    """Wrapper for backward compatibility"""
    return get_azure_vm_details(vm_name, resource_group, subscription_id)

async def azure_health_check():
    """Azure health check"""
    try:
        # Simple check by trying to load session
        subscriptions = load_azure_session()
        if subscriptions:
            return {"status": "ok", "message": "Azure services are healthy"}
        else:
            return {"status": "not_logged_in", "message": "Please log in to Azure first"}
    except Exception as e:
        return {"status": "error", "message": f"Health check failed: {str(e)}"}

@app.get("/azure/login", response_model=AzureLoginResponse)
async def azure_login():
    """Launch Azure CLI login process"""
    return await azure_login_handler()

@app.get("/azure/subscriptions", response_model=AzureSubscriptionsResponse)  
async def azure_subscriptions():
    """Get list of Azure subscriptions"""
    return get_azure_subscriptions()

@app.get("/azure/vms", response_model=AzureVMUsageResponse)
async def azure_vm_usage():
    """Get Azure VM usage and cost information"""
    return await azure_vm_usage_handler()

@app.get("/azure/resource-groups")
async def azure_resource_groups(subscription_id: str = Query(None)):
    """List Azure resource groups"""
    return list_azure_resource_groups(subscription_id)

@app.get("/azure/vm-details")
async def azure_vm_details(vm_name: str = Query(...), resource_group: str = Query(...), subscription_id: str = Query(None)):
    """Get detailed information about a specific Azure VM"""
    return await azure_vm_details_handler(vm_name, resource_group, subscription_id)

@app.get("/azure/health")
async def azure_health():
    """Azure utilities health check"""
    return azure_health_check()

@app.post("/azure/command")
async def azure_command_async(command: str = Query(...)):
    """Execute Azure CLI command asynchronously"""
    result = await az_command_async(command)
    return {"command": command, "result": result}


# ---------- GitHub Actions CI/CD Endpoints ----------

@app.get("/github/workflow/create")
async def create_github_workflow(
    owner: str = Query(...),
    repo: str = Query(...),
    branch: str = Query("main"),
    docker_image: str = Query(None)
):
    try:
        if not docker_image:
            docker_image = f"{repo.lower()}:latest"
        
        # Create the workflow using your service
        create_deploy_workflow(branch, repo, docker_image)

        return {
            "status": "success",
            "message": f"Workflow created for {owner}/{repo}",
            "branch": branch,
            "docker_image": docker_image,
            "workflow_path": f".github/workflows/deploy.yml"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")

@app.post("/github/cicd/setup")
async def setup_cicd_pipeline(
    owner: str = Form(...),
    repo: str = Form(...),
    token: str = Form(...)
):
    try:
        # Use your CI/CD manager to setup the pipeline
        setup_ci_cd(owner, repo, token)
        
        return {
            "status": "success",
            "message": f"CI/CD pipeline setup completed for {owner}/{repo}",
            "next_steps": [
                "Check the .github/workflows/deploy.yml file",
                "Commit and push to trigger the workflow", 
                "Monitor the Actions tab in your GitHub repository"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CI/CD setup failed: {str(e)}")

@app.get("/github/branches/select")
async def select_repository_branch(
    owner: str = Query(...),
    repo: str = Query(...),
    token: str = Query(...)
):
    try:
        # Get branches using your branch selector
        selected_branch = select_branch(owner, repo, token)
        
        return {
            "status": "success",
            "selected_branch": selected_branch,
            "repository": f"{owner}/{repo}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Branch selection failed: {str(e)}")

@app.post("/github/webhook/handler")
async def github_webhook_handler(request: Request):
   
    try:
        payload = await request.json()
        event_type = request.headers.get("x-github-event")
        
        if event_type in ["push", "pull_request"]:
            repo_full_name = payload.get("repository", {}).get("full_name")
            branch = payload.get("ref", "").replace("refs/heads/", "") if event_type == "push" else payload.get("pull_request", {}).get("head", {}).get("ref")
            
            if repo_full_name and branch:
                # Extract owner and repo
                owner, repo = repo_full_name.split("/")
                
                # Clone/reclone the repository
                repo_url = payload.get("repository", {}).get("clone_url")
                if repo_url:
                    clone_request = CloneRequest(repo_url=repo_url)
                    clone_result = clone_repository(clone_request)
                    
                    # Build and push Docker image
                    docker_image = f"{repo.lower()}:{branch}"
                    docker_login()
                    built_image = build_image(clone_result.repo_path, repo.lower(), branch)
                    push_image(repo.lower(), branch)
                    
                    return {
                        "status": "success",
                        "action": "rebuilt_and_deployed",
                        "repository": repo_full_name,
                        "branch": branch,
                        "image": docker_image,
                        "event_type": event_type
                    }
        
        return {
            "status": "ignored",
            "message": "Event not handled",
            "event_type": event_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook handling failed: {str(e)}")

@app.get("/github/workflow/status")
async def get_workflow_status(
    owner: str = Query(...),
    repo: str = Query(...),
    workflow_id: str = Query(None)
):
    
    try:
        return {
            "status": "success",
            "repository": f"{owner}/{repo}",
            "workflow_id": workflow_id,
            "message": "Workflow status endpoint - implement with GitHub API calls",
            "note": "This endpoint can be enhanced to fetch real workflow status from GitHub API"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow status: {str(e)}")

# ---------- MCP mount ----------
mcp = FastApiMCP(app)
mcp.mount_http()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
