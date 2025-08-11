"""
Docker Data Models

Pydantic models for Docker operations including deployment requests,
container information, and Dockerfile parsing results.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class DeployRequest(BaseModel):
    """Request model for Docker deployment operations"""
    repo_full_name: str = Field(..., description="Full repository name (owner/repo)")
    tag: str = Field(default="latest", description="Docker image tag")
    image_name: str = Field(..., description="Docker image name")
    repo_path: str = Field(..., description="Local path to repository")


class DockerfileInfo(BaseModel):
    """Information extracted from Dockerfile parsing"""
    base_image: Optional[str] = Field(None, description="Base image used in FROM instruction")
    exposed_ports: List[int] = Field(default_factory=list, description="Ports exposed by the container")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables defined")
    build_args: List[str] = Field(default_factory=list, description="Build arguments defined")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels defined in Dockerfile")
    working_dir: Optional[str] = Field(None, description="Working directory set in container")
    entrypoint: Optional[List[str]] = Field(None, description="Entrypoint command")
    cmd: Optional[List[str]] = Field(None, description="Default command to run")


class ContainerInfo(BaseModel):
    """Information about a Docker container"""
    container_id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Image used to create container")
    status: str = Field(..., description="Container status (running, stopped, etc.)")
    ports: List[str] = Field(default_factory=list, description="Port mappings")
    created: str = Field(..., description="Creation timestamp")
    command: Optional[str] = Field(None, description="Command running in container")


class ImageInfo(BaseModel):
    """Information about a Docker image"""
    image_id: str = Field(..., description="Image ID")
    repository: str = Field(..., description="Image repository name")
    tag: str = Field(..., description="Image tag")
    size: str = Field(..., description="Image size")
    created: str = Field(..., description="Creation timestamp")


class BuildContext(BaseModel):
    """Docker build context configuration"""
    dockerfile_path: str = Field(default="Dockerfile", description="Path to Dockerfile")
    context_path: str = Field(default=".", description="Build context path")
    build_args: Dict[str, str] = Field(default_factory=dict, description="Build arguments")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels to add to image")
    target: Optional[str] = Field(None, description="Multi-stage build target")
    no_cache: bool = Field(default=False, description="Disable build cache")


class ContainerRunOptions(BaseModel):
    """Options for running a Docker container"""
    image: str = Field(..., description="Docker image to run")
    name: Optional[str] = Field(None, description="Container name")
    ports: Dict[str, str] = Field(default_factory=dict, description="Port mappings (host:container)")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    volumes: Dict[str, str] = Field(default_factory=dict, description="Volume mappings (host:container)")
    network: Optional[str] = Field(None, description="Network to connect to")
    detach: bool = Field(default=True, description="Run container in detached mode")
    remove: bool = Field(default=False, description="Remove container when it exits")
    restart_policy: Optional[str] = Field(None, description="Restart policy (no, always, unless-stopped, on-failure)")


class DockerRegistryCredentials(BaseModel):
    """Docker registry authentication credentials"""
    username: str = Field(..., description="Registry username")
    password: str = Field(..., description="Registry password or token")
    registry: str = Field(default="docker.io", description="Registry URL")


class PortDetectionResult(BaseModel):
    """Result of port detection analysis"""
    detected_ports: List[int] = Field(default_factory=list, description="Ports detected from various sources")
    dockerfile_ports: List[int] = Field(default_factory=list, description="Ports from Dockerfile EXPOSE")
    recommended_ports: List[int] = Field(default_factory=list, description="Recommended ports based on project type")
    config_ports: List[int] = Field(default_factory=list, description="Ports from configuration files")
    default_ports: List[int] = Field(default_factory=list, description="Default ports for detected frameworks")
