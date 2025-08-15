from pathlib import Path
from ..utils.yaml_helpers import save_yaml_file

def create_deploy_workflow(branch: str, nameofrepo: str, docker_image: str):
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
                    },
                    {
                        "name": "Push Docker Image",
                        "run": (
                            "echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin\n"
                            f"docker tag {docker_image} ${{{{ secrets.DOCKER_USERNAME }}}}/{docker_image}\n"
                            f"docker push ${{{{ secrets.DOCKER_USERNAME }}}}/{docker_image}"
                        )
                    }
                ]
            }
        }
    }

    workflow_path = Path(f"C:\\Users\\Hassen\\azure_mcp_devops_agent\\repos\\{nameofrepo}\\.github\\workflows\\deploy.yml")
    save_yaml_file(workflow_path, workflow)
    print(f"✅ Workflow created at {workflow_path}")
    return workflow_path
