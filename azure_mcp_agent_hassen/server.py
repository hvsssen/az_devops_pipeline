from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_mcp import FastApiMCP
import webbrowser
from typing import List
from dotenv import load_dotenv
import os
from fastapi import Body

# Import utils - Clean modular structure  
from azure_mcp_agent_hassen.CI.git import (
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

from azure_mcp_agent_hassen.CI.docker import (
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

from azure_mcp_agent_hassen.CI.github_actions import (
    # Models
    WorkflowJob,
    WorkflowConfig,
    # Services
    create_deploy_workflow,
    setup_ci_cd,
    select_branch
)

from azure_mcp_agent_hassen.CD.terraform import (
    TerraformConfig,
    TerraformStatus, 
    TerraformGenerateRequest,
    write_tf_file,
    init,
    plan,
    apply,
    destroy
)

# Import new Azure deployment services
from azure_mcp_agent_hassen.azure.services.acr import ACRService
from azure_mcp_agent_hassen.azure.services.helm import HelmService  
from azure_mcp_agent_hassen.azure.services.deployment import AzureDeploymentService

load_dotenv()
users = get_all_users()

# Initialize services
acr_service = ACRService()
helm_service = HelmService()
deployment_service = AzureDeploymentService()

app = FastAPI()

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------- Web UI Documentation ----------
@app.get("/")
async def documentation_home(request: Request):
    logged_in = len(users) > 0
    return templates.TemplateResponse("documentation.html", {"request": request, "logged_in": logged_in})

@app.get("/workflow/order")
async def get_workflow_order():
    """
    🚀 Complete DevOps Workflow Order Guide
    
    This endpoint provides the correct order of operations for using the MCP DevOps Agent.
    Follow this sequence for successful end-to-end automation.
    """
    return {
        "workflow_title": "🚀 Azure MCP DevOps Agent - Complete Workflow Order",
        "description": "Follow this exact sequence for successful end-to-end DevOps automation",
        "prerequisites": {
            "required_tools": [
                "Azure CLI installed and accessible",
                "Docker installed and running", 
                "Terraform CLI installed",
                "Git configured",
                "Azure subscription with appropriate permissions"
            ],
            "required_authentication": [
                "Azure CLI login completed",
                "GitHub OAuth token (for private repos)",
                "Docker Hub credentials (for image pushing)"
            ]
        },
        "workflow_steps": [
            {
                "step": 1,
                "category": "🔐 Prerequisites & Authentication",
                "endpoint": "/azure/login",
                "method": "GET",
                "description": "Launch Azure CLI login process",
                "required": True,
                "dependencies": [],
                "expected_result": "Azure authentication completed",
                "next_steps": ["Verify with /azure/subscriptions"]
            },
            {
                "step": 2,
                "category": "🔐 Prerequisites & Authentication", 
                "endpoint": "/azure/subscriptions",
                "method": "GET",
                "description": "Verify Azure access and list available subscriptions",
                "required": True,
                "dependencies": ["Step 1: Azure login"],
                "expected_result": "List of accessible Azure subscriptions",
                "next_steps": ["Proceed to GitHub operations"]
            },
            {
                "step": 3,
                "category": "🐙 GitHub Operations",
                "endpoint": "/github/login",
                "method": "GET", 
                "description": "Initiate GitHub OAuth authentication",
                "required": False,
                "dependencies": [],
                "expected_result": "GitHub OAuth URL for authentication",
                "next_steps": ["Complete OAuth in browser, then clone repository"]
            },
            {
                "step": 4,
                "category": "🐙 GitHub Operations",
                "endpoint": "/clone",
                "method": "GET",
                "parameters": {"repo_url": "https://github.com/user/repo"},
                "description": "Clone repository for local development",
                "required": True,
                "dependencies": [],
                "expected_result": "Repository cloned to ./repos/repo-name",
                "next_steps": ["Analyze repository structure"]
            },
            {
                "step": 5,
                "category": "🔍 Repository Analysis",
                "endpoint": "/detect_ports", 
                "method": "GET",
                "parameters": {"repo_path": "./repos/repo-name"},
                "description": "Analyze repository for exposed ports and configurations",
                "required": True,
                "dependencies": ["Step 4: Repository cloned"],
                "expected_result": "Detected ports and container configuration",
                "next_steps": ["Parse Dockerfile if exists"]
            },
            {
                "step": 6,
                "category": "🔍 Repository Analysis",
                "endpoint": "/dockerfile/parse",
                "method": "GET", 
                "parameters": {"repo_path": "./repos/repo-name"},
                "description": "Parse Dockerfile and extract build configuration",
                "required": False,
                "dependencies": ["Step 5: Port detection completed"],
                "expected_result": "Dockerfile configuration details",
                "next_steps": ["Proceed to Docker build and deploy"]
            },
            {
                "step": 7,
                "category": "🐳 Docker Operations",
                "endpoint": "/deploy",
                "method": "POST",
                "parameters": {
                    "repo_full_name": "user/repo",
                    "image_name": "app-name", 
                    "tag": "latest",
                    "repo_path": "./repos/repo-name"
                },
                "description": "Build Docker image from repository",
                "required": True,
                "dependencies": ["Step 4: Repository cloned", "Step 5: Port detection"],
                "expected_result": "Docker image built successfully",
                "next_steps": ["Test container locally or proceed to infrastructure"]
            },
            {
                "step": 8,
                "category": "🐳 Docker Operations (Optional)",
                "endpoint": "/run_container",
                "method": "GET",
                "parameters": {
                    "image": "app-name",
                    "tag": "latest",
                    "repo_path": "./repos/repo-name"
                },
                "description": "Run container locally for testing",
                "required": False,
                "dependencies": ["Step 7: Docker image built"],
                "expected_result": "Container running locally with detected ports",
                "next_steps": ["Stop container and proceed to infrastructure"]
            },
            {
                "step": 9,
                "category": "🏗️ Infrastructure as Code",
                "endpoint": "/terraform/generate",
                "method": "POST",
                "parameters": {
                    "config": {
                        "user_id": "unique_user_id",
                        "cluster_name": "production-aks",
                        "region": "eastus",
                        "node_count": 3,
                        "vm_size": "Standard_DS2_v2",
                        "auto_scaling": True,
                        "min_nodes": 1,
                        "max_nodes": 5,
                        "enable_monitoring": True,
                        "private_cluster": False,
                        "dns_domain": "myapp.local",
                        "enable_oidc": True,
                        "tags": {"environment": "production", "project": "webapp"}
                    },
                    "repo_path": "./repos/repo-name",
                    "use_remote_backend": True
                },
                "description": "Generate Terraform configuration for AKS cluster",
                "required": True,
                "dependencies": ["Step 1: Azure authentication"],
                "expected_result": "main.tf and backend.tf files created",
                "next_steps": ["Initialize Terraform"]
            },
            {
                "step": 10,
                "category": "🏗️ Infrastructure as Code",
                "endpoint": "/terraform/init",
                "method": "GET",
                "parameters": {"repo_path": "./repos/repo-name"},
                "description": "Initialize Terraform with Azure backend",
                "required": True,
                "dependencies": ["Step 9: Terraform files generated", "Step 1: Azure authentication"],
                "expected_result": "Terraform initialized with Azure storage backend",
                "next_steps": ["Plan infrastructure changes"]
            },
            {
                "step": 11,
                "category": "🏗️ Infrastructure as Code",
                "endpoint": "/terraform/plan",
                "method": "GET",
                "parameters": {"repo_path": "./repos/repo-name"},
                "description": "Show Terraform execution plan",
                "required": True,
                "dependencies": ["Step 10: Terraform initialized"],
                "expected_result": "Detailed plan of infrastructure changes",
                "next_steps": ["Review plan, then apply if correct"]
            },
            {
                "step": 12,
                "category": "🏗️ Infrastructure as Code (CRITICAL)",
                "endpoint": "/terraform/apply",
                "method": "GET",
                "parameters": {"repo_path": "./repos/repo-name", "auto_approve": True},
                "description": "Apply Terraform changes - CREATES REAL AZURE RESOURCES",
                "required": False,
                "dependencies": ["Step 11: Plan reviewed and approved"],
                "expected_result": "AKS cluster and associated resources created in Azure",
                "next_steps": ["Monitor deployment, configure kubectl"],
                "warning": "⚠️ This creates billable Azure resources. Ensure plan is correct before applying."
            },
            {
                "step": 13,
                "category": "☁️ Azure Monitoring",
                "endpoint": "/azure/vms",
                "method": "GET",
                "description": "Monitor Azure resource usage and costs",
                "required": False,
                "dependencies": ["Step 12: Infrastructure deployed"],
                "expected_result": "Cost analysis and resource utilization data",
                "next_steps": ["Regular monitoring and optimization"]
            },
            {
                "step": 14,
                "category": "🧹 Cleanup (When needed)",
                "endpoint": "/terraform/destroy",
                "method": "GET",
                "parameters": {"repo_path": "./repos/repo-name", "auto_approve": True},
                "description": "Destroy all Terraform-managed resources",
                "required": False,
                "dependencies": ["Infrastructure no longer needed"],
                "expected_result": "All Azure resources destroyed, costs stopped",
                "next_steps": ["Verify all resources are cleaned up"],
                "warning": "⚠️ This permanently deletes all infrastructure. Ensure data is backed up."
            }
        ],
        "common_error_recovery": {
            "terraform_init_backend_changed": {
                "error": "Backend configuration changed",
                "solution": "Delete .terraform directory and backend.tf, regenerate with /terraform/generate, then init again"
            },
            "azure_auth_expired": {
                "error": "Azure authentication expired",
                "solution": "Run /azure/login again to refresh authentication"
            },
            "docker_build_failed": {
                "error": "Docker build failed",
                "solution": "Check Dockerfile syntax, ensure all dependencies are available"
            },
            "terraform_state_locked": {
                "error": "Terraform state is locked",
                "solution": "Wait for other operations to complete or force unlock if necessary"
            }
        },
        "best_practices": [
            "Always run /azure/login before any Azure operations",
            "Test Docker builds locally before infrastructure deployment",
            "Review Terraform plans carefully before applying",
            "Use unique user_id and cluster names to avoid conflicts",
            "Monitor costs regularly with /azure/vms",
            "Clean up resources when not needed to avoid unnecessary costs",
            "Keep Terraform state backed up in Azure Storage",
            "Use meaningful tags for resource organization"
        ],
        "cost_warnings": [
            "⚠️ AKS clusters incur ongoing costs even when idle",
            "⚠️ VM sizes like Standard_DS2_v2 have different pricing",
            "⚠️ Auto-scaling can increase costs during high load",
            "⚠️ Monitoring and Log Analytics workspace have separate costs",
            "⚠️ Always destroy test resources when finished"
        ]
    }

@app.get("/web/login")
async def web_github_login():
    url = get_github_login_url()
    return RedirectResponse(url)

@app.get("/workflow/validate")
async def validate_workflow_prerequisites():
    """
    🔍 Validate Workflow Prerequisites
    
    Checks if all required tools and authentication are available
    before starting the workflow.
    """
    validation_results = {
        "overall_status": "checking",
        "ready_for_workflow": False,
        "checks": {},
        "missing_requirements": [],
        "next_steps": []
    }
    
    try:
        # Check Azure CLI
        import subprocess
        try:
            result = subprocess.run(["az", "account", "show"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                validation_results["checks"]["azure_cli"] = {
                    "status": "✅ Ready",
                    "details": "Azure CLI authenticated"
                }
            else:
                validation_results["checks"]["azure_cli"] = {
                    "status": "❌ Not Authenticated",
                    "details": "Run /azure/login first"
                }
                validation_results["missing_requirements"].append("Azure authentication")
        except Exception as e:
            validation_results["checks"]["azure_cli"] = {
                "status": "❌ Not Available",
                "details": f"Azure CLI not found: {str(e)}"
            }
            validation_results["missing_requirements"].append("Azure CLI installation")
        
        # Check Docker
        try:
            result = subprocess.run(["docker", "version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                validation_results["checks"]["docker"] = {
                    "status": "✅ Ready",
                    "details": "Docker is running"
                }
            else:
                validation_results["checks"]["docker"] = {
                    "status": "❌ Not Running",
                    "details": "Docker daemon not accessible"
                }
                validation_results["missing_requirements"].append("Docker daemon")
        except Exception as e:
            validation_results["checks"]["docker"] = {
                "status": "❌ Not Available", 
                "details": f"Docker not found: {str(e)}"
            }
            validation_results["missing_requirements"].append("Docker installation")
        
        # Check Terraform
        try:
            result = subprocess.run(["terraform", "version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                validation_results["checks"]["terraform"] = {
                    "status": "✅ Ready",
                    "details": "Terraform CLI available"
                }
            else:
                validation_results["checks"]["terraform"] = {
                    "status": "❌ Error",
                    "details": "Terraform command failed"
                }
                validation_results["missing_requirements"].append("Terraform CLI")
        except Exception as e:
            validation_results["checks"]["terraform"] = {
                "status": "❌ Not Available",
                "details": f"Terraform not found: {str(e)}"
            }
            validation_results["missing_requirements"].append("Terraform installation")
        
        # Check Git
        try:
            result = subprocess.run(["git", "version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                validation_results["checks"]["git"] = {
                    "status": "✅ Ready",
                    "details": "Git is available"
                }
            else:
                validation_results["checks"]["git"] = {
                    "status": "❌ Error",
                    "details": "Git command failed"
                }
                validation_results["missing_requirements"].append("Git")
        except Exception as e:
            validation_results["checks"]["git"] = {
                "status": "❌ Not Available",
                "details": f"Git not found: {str(e)}"
            }
            validation_results["missing_requirements"].append("Git installation")
        
        # Determine overall status
        if len(validation_results["missing_requirements"]) == 0:
            validation_results["overall_status"] = "✅ Ready"
            validation_results["ready_for_workflow"] = True
            validation_results["next_steps"] = [
                "All prerequisites satisfied!",
                "Start with Step 1: /azure/login (if not already authenticated)",
                "Follow the complete workflow order from /workflow/order"
            ]
        else:
            validation_results["overall_status"] = "❌ Not Ready"
            validation_results["ready_for_workflow"] = False
            validation_results["next_steps"] = [
                f"Install missing requirements: {', '.join(validation_results['missing_requirements'])}",
                "Re-run /workflow/validate to check again",
                "Once all checks pass, follow /workflow/order"
            ]
        
        return validation_results
        
    except Exception as e:
        return {
            "overall_status": "❌ Validation Failed",
            "ready_for_workflow": False,
            "error": str(e),
            "next_steps": ["Check system configuration and try again"]
        }

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
    docker_image: str = Query(None),
    registry_type: str = Query("dockerhub", description="Registry type: 'dockerhub' or 'acr'"),
    acr_name: str = Query(None, description="ACR name (required if registry_type is 'acr')")
):
    try:
        if not docker_image:
            docker_image = f"{repo.lower()}:latest"
        
        # Validate ACR parameters
        if registry_type.lower() == "acr" and not acr_name:
            raise HTTPException(status_code=400, detail="acr_name is required when registry_type is 'acr'")
        
        # Create the workflow using your service
        create_deploy_workflow(branch, repo, docker_image, registry_type, acr_name)

        response = {
            "status": "success",
            "message": f"Workflow created for {owner}/{repo}",
            "branch": branch,
            "docker_image": docker_image,
            "registry_type": registry_type,
            "workflow_path": f".github/workflows/deploy.yml"
        }
        
        if registry_type.lower() == "acr":
            response["acr_name"] = acr_name
            response["image_url"] = f"{acr_name}.azurecr.io/{docker_image}"
            response["secrets_needed"] = ["ACR_USERNAME", "ACR_PASSWORD"]
        else:
            response["image_url"] = f"docker.io/[username]/{docker_image}"
            response["secrets_needed"] = ["DOCKER_USERNAME", "DOCKER_PASSWORD"]
        
        return response
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

# ---------- TERRAFORM ----------



# Track Terraform initialization status per repo_path
terraform_init_status = {}

@app.get("/terraform/init")
def terraform_init(repo_path: str = Query(...)):
    """Initialize Terraform in the given repo path."""
    try:
        result = init(repo_path)
        # Mark as initialized if successful
        if result.status == "success":
            terraform_init_status[repo_path] = True
        return result.__dict__ if hasattr(result, '__dict__') else result
    except Exception as e:
        return {"status": "error", "message": f"Error initializing Terraform: {str(e)}"}

@app.get("/terraform/plan")
def terraform_plan(repo_path: str = Query(...)):
    """Show Terraform plan for the given repo path."""
    try:
        if not terraform_init_status.get(repo_path):
            return {"status": "error", "message": "Terraform not initialized. Please run /terraform/init first."}
        result = plan(repo_path)
        return result.__dict__ if hasattr(result, '__dict__') else result
    except Exception as e:
        return {"status": "error", "message": f"Error running Terraform plan: {str(e)}"}

@app.get("/terraform/apply")
def terraform_apply(repo_path: str = Query(...), auto_approve: bool = True):
    """Apply Terraform changes in the given repo path."""
    try:
        if not terraform_init_status.get(repo_path):
            return {"status": "error", "message": "Terraform not initialized. Please run /terraform/init first."}
        result = apply(repo_path, auto_approve)
        return result.__dict__ if hasattr(result, '__dict__') else result
    except Exception as e:
        return {"status": "error", "message": f"Error applying Terraform: {str(e)}"}

@app.get("/terraform/destroy")
def terraform_destroy(repo_path: str = Query(...), auto_approve: bool = True):
    """Destroy Terraform-managed resources in the given repo path."""
    try:
        if not terraform_init_status.get(repo_path):
            return {"status": "error", "message": "Terraform not initialized. Please run /terraform/init first."}
        result = destroy(repo_path, auto_approve)
        return result.__dict__ if hasattr(result, '__dict__') else result
    except Exception as e:
        return {"status": "error", "message": f"Error destroying Terraform resources: {str(e)}"}



@app.post("/terraform/generate")
async def terraform_generate_main_tf(request: TerraformGenerateRequest):
    """Generate a main.tf file in the given repo_path using the provided config."""
    try:
        # Ensure repo_path exists and is accessible
        import os
        repo_path = os.path.abspath(request.repo_path)
        
        # Create directory if it doesn't exist
        if not os.path.exists(repo_path):
            os.makedirs(repo_path, exist_ok=True)
            
        # Test write permissions
        test_file = os.path.join(repo_path, 'test_write.txt')
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except PermissionError as pe:
            return {"status": "error", "message": f"Permission denied writing to {repo_path}: {str(pe)}"}
        
        tf_path = write_tf_file(repo_path, request.config, request.use_remote_backend)
        terraform_init_status[request.repo_path] = False
        return {"status": "success", "main_tf_path": tf_path}
    except Exception as e:
        return {"status": "error", "message": f"Error generating Terraform files: {str(e)}"}


# ---------- Azure Container Registry (ACR) Endpoints ----------

@app.post("/acr/create")
async def create_acr_registry(
    name: str = Body(...),
    resource_group: str = Body(...),
    location: str = Body(default="eastus")
):
    """Create Azure Container Registry"""
    return await acr_service.create_acr(name, resource_group, location)

@app.get("/acr/login")
async def login_to_acr(name: str = Query(...)):
    """Login to Azure Container Registry"""
    return await acr_service.login_to_acr(name)

@app.post("/acr/push")
async def push_to_acr(
    local_image: str = Body(...),
    acr_name: str = Body(...),
    repo_name: str = Body(...),
    tag: str = Body(default="latest")
):
    """Push Docker image to ACR"""
    return await acr_service.push_image_to_acr(local_image, acr_name, repo_name, tag)

@app.get("/acr/repositories")
async def list_acr_repositories(acr_name: str = Query(...)):
    """List repositories in ACR"""
    return await acr_service.list_acr_repositories(acr_name)

@app.post("/acr/attach-aks")
async def attach_acr_to_aks(
    acr_name: str = Body(...),
    aks_name: str = Body(...),
    resource_group: str = Body(...)
):
    """Attach ACR to AKS cluster"""
    return await acr_service.attach_acr_to_aks(acr_name, aks_name, resource_group)

# ---------- Helm Charts Endpoints ----------

@app.post("/helm/create-chart")
async def create_helm_chart(
    chart_name: str = Body(...),
    app_name: str = Body(...),
    image_repository: str = Body(...),
    image_tag: str = Body(default="latest"),
    port: int = Body(default=80),
    namespace: str = Body(default="default")
):
    """Create Helm chart for application"""
    # Use the exact repos/mcp-test-app directory as the base path
    repo_base_path = os.path.abspath(os.path.join(os.getcwd(), "repos", "mcp-test-app"))
    helm_service_with_path = HelmService(base_path=repo_base_path)
    return await helm_service_with_path.create_helm_chart(
        chart_name, app_name, image_repository, image_tag, port, namespace
    )

@app.post("/helm/install")
async def install_helm_chart(
    chart_name: str = Body(...),
    release_name: str = Body(...),
    namespace: str = Body(default="default"),
    values_override: dict = Body(default=None)
):
    """Install Helm chart to Kubernetes"""
    # Use the exact repos/mcp-test-app directory as the base path
    repo_base_path = os.path.abspath(os.path.join(os.getcwd(), "repos", "mcp-test-app"))
    helm_service_with_path = HelmService(base_path=repo_base_path)
    return await helm_service_with_path.install_helm_chart(
        chart_name, release_name, namespace, values_override
    )

@app.post("/helm/upgrade")
async def upgrade_helm_release(
    release_name: str = Body(...),
    chart_name: str = Body(...),
    namespace: str = Body(default="default"),
    values_override: dict = Body(default=None)
):
    """Upgrade existing Helm release"""
    return await helm_service.upgrade_helm_release(
        release_name, chart_name, namespace, values_override
    )

@app.delete("/helm/uninstall")
async def uninstall_helm_release(
    release_name: str = Body(...),
    namespace: str = Body(default="default")
):
    """Uninstall Helm release"""
    return await helm_service.uninstall_helm_release(release_name, namespace)

@app.get("/helm/releases")
async def list_helm_releases(namespace: str = Query(default="default")):
    """List Helm releases in namespace"""
    return await helm_service.list_helm_releases(namespace)

# ---------- Complete Azure Deployment Endpoints ----------

@app.post("/azure/deploy-complete")
async def deploy_complete_application(
    # Terraform configuration
    terraform_config: dict = Body(...),
    repo_path: str = Body(...),
    
    # Container configuration
    image_name: str = Body(...),
    image_tag: str = Body(default="latest"),
    app_port: int = Body(default=80),
    
    # Registry choice
    registry_choice: str = Body(default="acr"),  # "acr" or "dockerhub"
    docker_username: str = Body(default=None),  # Required for dockerhub
    acr_name: str = Body(default=None),  # Optional, will be generated if not provided
    
    # Deployment configuration
    app_name: str = Body(default=None),  # Will use image_name if not provided
    namespace: str = Body(default="default"),
    replica_count: int = Body(default=2)
):
    """
    Complete Azure deployment workflow:
    1. Apply Terraform (creates AKS + optionally ACR)
    2. Push container to chosen registry (ACR or Docker Hub)
    3. Create and deploy Helm chart to AKS
    """
    config = {
        "terraform_config": terraform_config,
        "repo_path": repo_path,
        "image_name": image_name,
        "image_tag": image_tag,
        "app_port": app_port,
        "registry_choice": registry_choice,
        "docker_username": docker_username,
        "acr_name": acr_name,
        "app_name": app_name or image_name,
        "namespace": namespace,
        "replica_count": replica_count
    }
    
    return await deployment_service.deploy_complete_application(config)

@app.post("/azure/cleanup-deployment")
async def cleanup_complete_deployment(
    repo_path: str = Body(...),
    app_name: str = Body(...),
    namespace: str = Body(default="default"),
    cleanup_helm: bool = Body(default=True),
    cleanup_terraform: bool = Body(default=True)
):
    """Clean up complete deployment (Helm + Terraform)"""
    config = {
        "repo_path": repo_path,
        "app_name": app_name,
        "namespace": namespace,
        "cleanup_helm": cleanup_helm,
        "cleanup_terraform": cleanup_terraform
    }
    
    return await deployment_service.cleanup_deployment(config)

@app.get("/azure/registry-choice-guide")
async def get_registry_choice_guide():
    """Guide for choosing between ACR and Docker Hub"""
    return {
        "title": "Container Registry Choice Guide",
        "options": {
            "acr": {
                "name": "Azure Container Registry (ACR)",
                "advantages": [
                    "Integrated with Azure and AKS",
                    "Private registry in your Azure subscription", 
                    "Automatic authentication with AKS",
                    "Built-in security scanning",
                    "Geo-replication support",
                    "Azure RBAC integration"
                ],
                "disadvantages": [
                    "Azure-specific (vendor lock-in)",
                    "Additional cost for storage",
                    "Requires Azure subscription"
                ],
                "best_for": [
                    "Production Azure workloads",
                    "Private enterprise applications",
                    "Applications requiring tight Azure integration",
                    "Teams already using Azure heavily"
                ],
                "cost": "Pay for storage and bandwidth usage"
            },
            "dockerhub": {
                "name": "Docker Hub",
                "advantages": [
                    "Universal compatibility",
                    "Large ecosystem and community",
                    "Free tier available",
                    "Well-known and established",
                    "Easy to use and share publicly"
                ],
                "disadvantages": [
                    "Public by default (private repos cost extra)",
                    "Rate limiting on free tier",
                    "Less integrated with Azure",
                    "Requires separate authentication setup"
                ],
                "best_for": [
                    "Open source projects",
                    "Development and testing",
                    "Multi-cloud deployments",
                    "Cost-sensitive projects"
                ],
                "cost": "Free for public repos, paid for private repos"
            }
        },
        "recommendation": {
            "use_acr_when": [
                "Deploying to Azure AKS in production",
                "Need private registry with Azure integration",
                "Security and compliance are priorities",
                "Already have Azure subscription and budget"
            ],
            "use_dockerhub_when": [
                "Building open source or public projects",
                "Need multi-cloud compatibility", 
                "Want to minimize Azure costs",
                "In development/testing phase"
            ]
        },
        "configuration_examples": {
            "acr_deployment": {
                "registry_choice": "acr",
                "acr_name": "myappregistry",  # Optional, will be auto-generated
                "docker_username": None  # Not needed for ACR
            },
            "dockerhub_deployment": {
                "registry_choice": "dockerhub", 
                "acr_name": None,  # Not needed for Docker Hub
                "docker_username": "your_dockerhub_username"  # Required
            }
        }
    }


# ---------- MCP mount ----------
mcp = FastApiMCP(app)
mcp.mount_http()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
