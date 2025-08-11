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
    GitHubRepository,
    GitHubBranch,
    GitHubLanguage,
    GitHubCommit,
    PortRecommendation,
    GitHubRepositoryAnalysis,
    # API functions
    get_github_repository_info,
    get_github_branches,
    get_github_recent_commits,
    get_comprehensive_repository_analysis,
    get_repo_recommended_ports,
    get_github_languages_detailed,
    analyze_repository_structure,
    get_primary_language,
    # Port analysis
    get_language_default_ports,
    get_framework_specific_ports,
    # Deployment
    deploy_repository_container,
    get_container_deployment_preview,
    # CI/CD
    generate_github_actions_workflow,
    create_ci_workflow_for_repo,
    preview_ci_workflow
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
        run_container(image, tag, container_name="auto_detected_container")
        recommended_ports, port_info = get_repo_recommended_ports("") if repo_path else ([], {})
        return {
            "status": "running", 
            "image": f"{image}:{tag}",
            "ports_detected": recommended_ports,
            "message": f"Container running with auto-detected ports: {recommended_ports}"
        }
    else:
        # Fallback to default behavior
        run_container(image, tag, container_name="default_container")
        return {
            "status": "running", 
            "image": f"{image}:{tag}",
            "ports_used": [8000],
            "message": "Container running with default port 8000 (no repo_path provided for auto-detection)"
        }

@app.get("/detect_ports")
def detect_ports_endpoint(repo_path: str = Query(...)):
    """Endpoint to detect ports from a repository without running container"""
    recommended_ports, port_info = get_repo_recommended_ports("") if repo_path else ([], {})
    
    return {
        "repo_path": repo_path,
        "port_detection": port_info,
        "recommended_ports": recommended_ports,
        "detection_summary": {
            "dockerfile_found": bool(port_info.get("dockerfile")),
            "package_json_found": bool(port_info.get("package_json")), 
            "total_detected": len(recommended_ports)
        }
    }

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

# ---------- GitHub Actions & Repository Analysis ----------
@app.get("/github/repository/{owner}/{repo}", response_model=GitHubRepository)
async def get_repository_info(owner: str, repo: str):
    """Get comprehensive GitHub repository information"""
    repo_full_name = f"{owner}/{repo}"
    repo_info = get_github_repository_info(repo_full_name)
    if not repo_info:
        raise HTTPException(status_code=404, detail=f"Repository {repo_full_name} not found")
    return repo_info

@app.get("/github/repository/{owner}/{repo}/branches", response_model=List[GitHubBranch])
async def get_repository_branches(owner: str, repo: str):
    """Get all branches for a GitHub repository"""
    repo_full_name = f"{owner}/{repo}"
    branches = get_github_branches(repo_full_name)
    return branches

@app.get("/github/repository/{owner}/{repo}/languages", response_model=List[GitHubLanguage])
async def get_repository_languages(owner: str, repo: str):
    """Get detailed language information for a GitHub repository"""
    repo_full_name = f"{owner}/{repo}"
    languages = get_github_languages_detailed(repo_full_name)
    return languages

@app.get("/github/repository/{owner}/{repo}/commits", response_model=List[GitHubCommit])
async def get_repository_commits(owner: str, repo: str, count: int = Query(10, ge=1, le=100)):
    """Get recent commits for a GitHub repository"""
    repo_full_name = f"{owner}/{repo}"
    commits = get_github_recent_commits(repo_full_name, count)
    return commits

@app.get("/github/repository/{owner}/{repo}/analysis", response_model=GitHubRepositoryAnalysis)
async def get_repository_analysis(owner: str, repo: str):
    """Get comprehensive repository analysis including structure and recommendations"""
    repo_full_name = f"{owner}/{repo}"
    analysis = get_comprehensive_repository_analysis(repo_full_name)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis failed for repository {repo_full_name}")
    return analysis

@app.get("/github/repository/{owner}/{repo}/structure")
async def get_repository_structure(owner: str, repo: str):
    """Analyze repository structure and technology stack"""
    repo_full_name = f"{owner}/{repo}"
    structure = analyze_repository_structure(repo_full_name)
    return structure

@app.get("/github/repository/{owner}/{repo}/primary-language")
async def get_repository_primary_language(owner: str, repo: str):
    """Get the primary programming language of a repository"""
    repo_full_name = f"{owner}/{repo}"
    primary_lang = get_primary_language(repo_full_name)
    if not primary_lang:
        raise HTTPException(status_code=404, detail=f"Could not determine primary language for {repo_full_name}")
    return {"repository": repo_full_name, "primary_language": primary_lang}

@app.get("/github/repository/{owner}/{repo}/recommended-ports")
async def get_repository_recommended_ports(owner: str, repo: str):
    """Get recommended ports for a repository based on its technology stack"""
    repo_full_name = f"{owner}/{repo}"
    ports, details = get_repo_recommended_ports(repo_full_name)
    return {
        "repository": repo_full_name,
        "recommended_ports": ports,
        "port_analysis": details
    }

@app.get("/github/repository/{owner}/{repo}/framework-ports")
async def get_repository_framework_ports(owner: str, repo: str):
    """Get framework-specific port recommendations"""
    repo_full_name = f"{owner}/{repo}"
    framework_ports = get_framework_specific_ports(repo_full_name)
    return {
        "repository": repo_full_name,
        "framework_ports": framework_ports
    }

@app.get("/language/{language}/default-ports")
async def get_language_ports(language: str):
    """Get default ports for a specific programming language"""
    ports = get_language_default_ports(language)
    return {
        "language": language,
        "default_ports": ports
    }

# ---------- Smart Deployment Endpoints ----------
@app.post("/deploy/smart")
async def smart_deploy_repository(
    owner: str = Query(...),
    repo: str = Query(...),
    repo_path: str = Query(...),
    image_name: str = Query(...),
    tag: str = Query("latest")
):
    """Intelligently deploy a repository container with automatic port detection"""
    repo_full_name = f"{owner}/{repo}"
    try:
        result = deploy_repository_container(repo_full_name, repo_path, image_name, tag)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart deployment failed: {str(e)}")

@app.get("/deploy/preview")
async def get_deployment_preview(
    owner: str = Query(...),
    repo: str = Query(...),
    repo_path: str = Query(...)
):
    """Preview deployment configuration for a repository"""
    repo_full_name = f"{owner}/{repo}"
    try:
        preview = get_container_deployment_preview(repo_full_name, repo_path)
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

# ---------- GitHub Actions CI/CD Workflow Generation ----------
@app.post("/github/workflow/generate")
async def generate_workflow(
    owner: str = Query(...),
    repo: str = Query(...),
    workflow_name: str = Query("ci"),
    repo_path: str = Query(None)
):
    """Generate GitHub Actions CI/CD workflow for a repository"""
    repo_full_name = f"{owner}/{repo}"
    
    # Use default path if not provided
    if not repo_path:
        repo_path = f"repos/{repo}"
    
    try:
        result = generate_github_actions_workflow(repo_full_name, repo_path, workflow_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow generation failed: {str(e)}")

@app.post("/github/workflow/create")
async def create_workflow(
    owner: str = Query(...),
    repo: str = Query(...),
    local_repo_path: str = Query(None)
):
    """Create CI workflow for a repository in repos/{repo_name} folder"""
    repo_full_name = f"{owner}/{repo}"
    try:
        result = create_ci_workflow_for_repo(repo_full_name, local_repo_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CI workflow creation failed: {str(e)}")

@app.get("/github/workflow/preview")
async def preview_workflow(
    owner: str = Query(...),
    repo: str = Query(...)
):
    """Preview GitHub Actions workflow without creating files"""
    repo_full_name = f"{owner}/{repo}"
    try:
        preview = preview_ci_workflow(repo_full_name)
        if preview.get("status") == "error":
            raise HTTPException(status_code=500, detail=preview.get("error"))
        return preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow preview failed: {str(e)}")

@app.get("/github/repository/{owner}/{repo}/ci-recommendations")
async def get_ci_recommendations(owner: str, repo: str):
    """Get CI/CD recommendations based on repository analysis"""
    repo_full_name = f"{owner}/{repo}"
    try:
        # Get comprehensive analysis
        analysis = get_comprehensive_repository_analysis(repo_full_name)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Could not analyze repository {repo_full_name}")
        
        # Get additional details
        ports, port_details = get_repo_recommended_ports(repo_full_name)
        primary_language = get_primary_language(repo_full_name)
        structure_info = analyze_repository_structure(repo_full_name)
        
        recommendations = {
            "repository": repo_full_name,
            "primary_language": primary_language,
            "recommended_ports": ports,
            "testing_framework": "auto-detected",
            "build_tool": structure_info.get("build_tools", []),
            "frameworks": structure_info.get("detected_frameworks", []),
            "deployment_strategy": "docker" if structure_info.get("has_dockerfile") else "platform-specific",
            "branches_for_ci": [
                analysis.repository.default_branch,
                "develop" if any(b.name == "develop" for b in analysis.branches) else None
            ],
            "recommended_triggers": [
                f"push to {analysis.repository.default_branch}",
                "pull requests",
                "manual workflow dispatch"
            ],
            "security_recommendations": [
                "Use secrets for Docker credentials",
                "Enable dependency scanning",
                "Add SAST (Static Application Security Testing)",
                "Use least privilege permissions"
            ]
        }
        
        # Remove None values
        recommendations["branches_for_ci"] = [b for b in recommendations["branches_for_ci"] if b]
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CI recommendations failed: {str(e)}")

# ---------- MCP mount ----------
mcp = FastApiMCP(app)
mcp.mount_http()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
