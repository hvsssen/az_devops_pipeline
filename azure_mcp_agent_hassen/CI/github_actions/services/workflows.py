from pathlib import Path
from ..utils.yaml_helpers import save_yaml_file

def create_deploy_workflow(branch: str, nameofrepo: str, docker_image: str, registry_type: str = "dockerhub", acr_name: str = None):
    """
    Create deployment workflow with support for Docker Hub or Azure Container Registry
    
    Args:
        branch: Git branch to trigger on
        nameofrepo: Repository name
        docker_image: Docker image name
        registry_type: "dockerhub" or "acr"
        acr_name: ACR name (required if registry_type is "acr")
    """
    
    # Base workflow structure
    workflow = {
        "name": "Deploy",
        "on": {
            "push": {
                "branches": [branch]
            }
        },
        "jobs": {
            "build-and-deploy": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v3"},
                    {
                        "name": "Build Docker Image",
                        "run": f"docker build -t {docker_image} ."
                    }
                ]
            }
        }
    }
    
    # Add registry-specific push steps
    if registry_type.lower() == "acr" and acr_name:
        # Azure Container Registry workflow
        workflow["jobs"]["build-and-deploy"]["steps"].extend([
            {
                "name": "Login to Azure Container Registry",
                "run": (
                    f"echo ${{{{ secrets.ACR_PASSWORD }}}} | docker login {acr_name}.azurecr.io -u ${{{{ secrets.ACR_USERNAME }}}} --password-stdin"
                )
            },
            {
                "name": "Push Docker Image to ACR",
                "run": (
                    f"docker tag {docker_image} {acr_name}.azurecr.io/{docker_image}:latest\n"
                    f"docker push {acr_name}.azurecr.io/{docker_image}:latest"
                )
            },
            {
                "name": "Update Kubernetes Deployment",
                "run": (
                    "echo 'Image pushed successfully to ACR. Update your Kubernetes deployment to use the new image.'"
                )
            }
        ])
    else:
        # Docker Hub workflow (default)
        workflow["jobs"]["build-and-deploy"]["steps"].append({
            "name": "Push Docker Image",
            "run": (
                "echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin\n"
                f"docker tag {docker_image} ${{{{ secrets.DOCKER_USERNAME }}}}/{docker_image}\n"
                f"docker push ${{{{ secrets.DOCKER_USERNAME }}}}/{docker_image}"
            )
        })

    workflow_path = Path(f"C:\\Users\\Hassen\\azure_mcp_devops_agent\\repos\\{nameofrepo}\\.github\\workflows\\deploy.yml")
    save_yaml_file(workflow_path, workflow)
    print(f"✅ Workflow created at {workflow_path}")
    print(f"📦 Registry type: {registry_type.upper()}")
    if registry_type.lower() == "acr":
        print(f"🏗️  ACR: {acr_name}.azurecr.io")
        print("⚠️  Don't forget to set ACR_USERNAME and ACR_PASSWORD secrets in GitHub!")
    else:
        print("🐳 Docker Hub registry")
        print("⚠️  Don't forget to set DOCKER_USERNAME and DOCKER_PASSWORD secrets in GitHub!")
    
    return workflow_path
