from .branch_selector import select_branch
from .workflows import create_deploy_workflow
from ...docker import build_image

def setup_ci_cd(owner: str, repo: str, token: str):
    branch = select_branch(owner, repo, token)
    docker_image = f"{repo.lower()}:{branch}"

    print(f"\n📦 Building Docker image {docker_image}...")
    build_image(docker_image)

    print("\n⚙️ Creating GitHub Actions workflow...")
    create_deploy_workflow(branch, docker_image)

    print("\n🎉 CI/CD pipeline ready!")
