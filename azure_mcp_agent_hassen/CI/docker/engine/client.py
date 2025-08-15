"""
Docker Engine Client

Core Docker engine operations including authentication, image management,
container operations, and registry interactions.
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from ..models import DockerRegistryCredentials, ContainerInfo, ImageInfo

load_dotenv()


def docker_login(credentials: Optional[DockerRegistryCredentials] = None) -> Dict[str, Any]:
    """Login to Docker registry"""
    try:
        if not credentials:
            # Use environment variables
            username = os.getenv("DOCKER_USERNAME")
            password = os.getenv("DOCKER_PASSWORD")
            registry = os.getenv("DOCKER_REGISTRY", "docker.io")
            
            if not username or not password:
                return {
                    "status": "error",
                    "error": "DOCKER_USERNAME or DOCKER_PASSWORD not set in environment variables"
                }
            
            credentials = DockerRegistryCredentials(
                username=username,
                password=password,
                registry=registry
            )
        
        cmd = ["docker", "login"]
        if credentials.registry != "docker.io":
            cmd.append(credentials.registry)
        
        cmd.extend(["--username", credentials.username, "--password", credentials.password])
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "message": "Docker login successful",
            "registry": credentials.registry
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Docker login failed: {e.stderr}")
        return {"status": "error", "error": f"Docker login failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Docker login error: {e}")
        return {"status": "error", "error": str(e)}


def docker_logout(registry: Optional[str] = None) -> Dict[str, Any]:
    """Logout from Docker registry"""
    try:
        cmd = ["docker", "logout"]
        if registry:
            cmd.append(registry)
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "message": f"Logged out from {registry or 'default registry'}"
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Docker logout failed: {e.stderr}")
        return {"status": "error", "error": f"Docker logout failed: {e.stderr}"}


def build_image(repo_path: str, image_name: str, tag: str = "latest",
               dockerfile: str = "Dockerfile", build_args: Optional[Dict[str, str]] = None,
               no_cache: bool = False) -> Dict[str, Any]:
    """Build Docker image"""
    try:
        # Ensure image name includes Docker Hub username if not already present
        if "/" not in image_name:
            username = os.getenv("DOCKER_USERNAME")
            if username:
                image_name = f"{username}/{image_name}"
        
        full_image_name = f"{image_name}:{tag}"
        
        cmd = ["docker", "build", "-t", full_image_name]
        
        if dockerfile != "Dockerfile":
            cmd.extend(["-f", dockerfile])
        
        if build_args:
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        
        if no_cache:
            cmd.append("--no-cache")
        
        cmd.append(repo_path)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "image": full_image_name,
            "message": f"Built Docker image: {full_image_name}",
            "build_log": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Docker build failed: {e.stderr}")
        return {"status": "error", "error": f"Docker build failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Docker build error: {e}")
        return {"status": "error", "error": str(e)}


def push_image(image_name: str, tag: str = "latest") -> Dict[str, Any]:
    """Push Docker image to registry"""
    try:
        # Ensure image name includes Docker Hub username if not already present
        if "/" not in image_name:
            username = os.getenv("DOCKER_USERNAME")
            if username:
                image_name = f"{username}/{image_name}"
        
        full_image_name = f"{image_name}:{tag}"
        
        result = subprocess.run(
            ["docker", "push", full_image_name],
            capture_output=True, text=True, check=True
        )
        
        return {
            "status": "ok",
            "image": full_image_name,
            "message": f"Pushed Docker image: {full_image_name}",
            "push_log": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Docker push failed: {e.stderr}")
        return {"status": "error", "error": f"Docker push failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Docker push error: {e}")
        return {"status": "error", "error": str(e)}


def pull_image(image_name: str, tag: str = "latest") -> Dict[str, Any]:
    """Pull Docker image from registry"""
    try:
        full_image_name = f"{image_name}:{tag}"
        
        result = subprocess.run(
            ["docker", "pull", full_image_name],
            capture_output=True, text=True, check=True
        )
        
        return {
            "status": "ok",
            "image": full_image_name,
            "message": f"Pulled Docker image: {full_image_name}",
            "pull_log": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Docker pull failed: {e.stderr}")
        return {"status": "error", "error": f"Docker pull failed: {e.stderr}"}
    except Exception as e:
        logging.error(f"Docker pull error: {e}")
        return {"status": "error", "error": str(e)}


def list_images() -> Dict[str, Any]:
    """List all Docker images"""
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"],
            capture_output=True, text=True, check=True
        )
        
        images = []
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        
        for line in lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 5:
                    images.append(ImageInfo(
                        repository=parts[0],
                        tag=parts[1],
                        image_id=parts[2],
                        size=parts[3],
                        created=parts[4]
                    ))
        
        return {
            "status": "ok",
            "images": [img.dict() for img in images],
            "count": len(images)
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to list images: {e.stderr}")
        return {"status": "error", "error": f"Failed to list images: {e.stderr}"}
    except Exception as e:
        logging.error(f"List images error: {e}")
        return {"status": "error", "error": str(e)}


def remove_image(image_name: str, tag: str = "latest", force: bool = False) -> Dict[str, Any]:
    """Remove Docker image"""
    try:
        full_image_name = f"{image_name}:{tag}"
        cmd = ["docker", "rmi"]
        
        if force:
            cmd.append("--force")
        
        cmd.append(full_image_name)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        return {
            "status": "ok",
            "message": f"Removed Docker image: {full_image_name}",
            "output": result.stdout
        }
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to remove image: {e.stderr}")
        return {"status": "error", "error": f"Failed to remove image: {e.stderr}"}
    except Exception as e:
        logging.error(f"Remove image error: {e}")
        return {"status": "error", "error": str(e)}
