import os
import subprocess
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()  # Loads .env if it exists
class DeployRequest(BaseModel):
    repo_full_name: str
    tag: str
    image_name: str
    repo_path: str



def docker_login():
    username = os.getenv("DOCKER_USERNAME")
    password = os.getenv("DOCKER_PASSWORD")

    if not username or not password:
        raise ValueError("DOCKER_USERNAME or DOCKER_PASSWORD not set in environment variables.")

    subprocess.run([
        "docker", "login",
        "--username", username,
        "--password", password
    ], check=True)
    print("✅ Docker login successful.")

def build_image(repo_path: str, image_name: str, tag: str = "latest"):
    # Ensure image name includes Docker Hub username if not already present
    if "/" not in image_name:
        username = os.getenv("DOCKER_USERNAME")
        if username:
            image_name = f"{username}/{image_name}"
    
    full_image_name = f"{image_name}:{tag}"
    subprocess.run(["docker", "build", "-t", full_image_name, repo_path], check=True)
    print(f"✅ Built Docker image: {full_image_name}")
    return full_image_name

def push_image(image_name: str, tag: str = "latest"):
    # Ensure image name includes Docker Hub username if not already present
    if "/" not in image_name:
        username = os.getenv("DOCKER_USERNAME")
        if username:
            image_name = f"{username}/{image_name}"
    
    full_image_name = f"{image_name}:{tag}"
    subprocess.run(["docker", "push", full_image_name], check=True)
    print(f"✅ Pushed Docker image: {full_image_name}")
